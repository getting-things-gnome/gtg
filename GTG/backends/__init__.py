# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""
Backends are a way to permanently store a project on a medium
(like on the hard disk or on the internet)
and to read projects from this medium
"""

import sys
import uuid
import os.path

from GTG.tools.logger import Log
from GTG.tools.borg import Borg
from GTG.backends.genericbackend import GenericBackend
from GTG.core import firstrun_tasks
from GTG.tools import cleanxml
from GTG.core import CoreConfig


class BackendFactory(Borg):
    '''
    This class holds the information about the backend types.
    Since it's about types, all information is static. The instantiated
    backends are handled in the Datastore.
    It is a Borg for what matters its only state (_backend_modules),
    since it makes no sense of keeping multiple instances of this.
    '''

    BACKEND_PREFIX = "backend_"

    def __init__(self):
        """
         Creates a dictionary of the currently available backend modules
        """
        Borg.__init__(self)
        if hasattr(self, "backend_modules"):
            # This object has already been constructed
            return
        self.backend_modules = {}
        backend_files = self._find_backend_files()
        # Create module names
        module_names = [f.replace(".py", "") for f in backend_files]
        Log.debug("Backends found: " + str(module_names))
        # Load backend modules
        for module_name in module_names:
            extended_module_name = "GTG.backends." + module_name
            try:
                __import__(extended_module_name)
            except ImportError as exception:
                # Something is wrong with this backend, skipping
                Log.warning("Backend %s could not be loaded: %s" %
                            (module_name, str(exception)))
                continue
            except Exception as exception:
                # Other exception log as errors
                Log.error("Malformated backend %s: %s" %
                          (module_name, str(exception)))
                continue

            self.backend_modules[module_name] = \
                sys.modules[extended_module_name]

    def _find_backend_files(self):
        # Look for backends in the GTG/backends dir
        this_dir = os.path.dirname(__file__)
        for filename in os.listdir(this_dir):
            is_python = filename.endswith(".py")
            has_prefix = filename.startswith(self.BACKEND_PREFIX)
            if is_python and has_prefix:
                yield filename

    def get_backend(self, backend_name):
        '''
        Returns the backend module for the backend matching
        backend_name. Else, returns none
        '''
        if backend_name in self.backend_modules:
            return self.backend_modules[backend_name]
        else:
            Log.debug("Trying to load backend %s, but failed!" % backend_name)
            return None

    def get_all_backends(self):
        '''
        Returns a dictionary containing all the backends types
        '''
        return self.backend_modules

    def get_new_backend_dict(self, backend_name, additional_parameters={}):
        '''
        Constructs a new backend initialization dictionary. In more
        exact terms, creates a dictionary, containing all the necessary
        entries to initialize a backend.
        '''
        if backend_name not in self.backend_modules:
            return None
        dic = {}
        module = self.get_backend(backend_name)
        # Different pids are necessary to discern between backends of the same
        # type
        parameters = module.Backend.get_static_parameters()
        # we all the parameters and their default values in dic
        for param_name, param_dic in parameters.items():
            dic[param_name] = param_dic[GenericBackend.PARAM_DEFAULT_VALUE]
        dic["pid"] = str(uuid.uuid4())
        dic["module"] = module.Backend.get_name()
        for param_name, param_value in additional_parameters.items():
            dic[param_name] = param_value
        dic["backend"] = module.Backend(dic)
        return dic

    def restore_backend_from_xml(self, dic):
        '''
        Function restoring a backend from its xml description.
        dic should be a dictionary containing at least the key
            - "module", with the module name
            - "xmlobject", with its xml description.
        Every other key is passed as-is to the backend, as parameter.

        Returns the backend instance, or None is something goes wrong
        '''
        if "module" not in dic or "xmlobject" not in dic:
            Log.debug("Malformed backend configuration found! %s" %
                      dic)
        module = self.get_backend(dic["module"])
        if module is None:
            Log.debug("could not load module for backend %s" %
                      dic["module"])
            return None
        # we pop the xml object, as it will be redundant when the parameters
        # are set directly in the dict
        xp = dic.pop("xmlobject")
        # Building the dictionary
        parameters_specs = module.Backend.get_static_parameters()
        dic["pid"] = str(xp.getAttribute("pid"))
        for param_name, param_dic in parameters_specs.items():
            if xp.hasAttribute(param_name):
                # we need to convert the parameter to the right format.
                # we fetch the format from the static_parameters
                param_type = param_dic[GenericBackend.PARAM_TYPE]
                param_value = GenericBackend.cast_param_type_from_string(
                    xp.getAttribute(param_name), param_type)
                dic[param_name] = param_value
        # We put the backend itself in the dict
        dic["backend"] = module.Backend(dic)
        return dic["backend"]

    def get_saved_backends_list(self):
        backends_dic = self._read_backend_configuration_file()

        # Retrocompatibility: default backend has changed name
        for dic in backends_dic:
            if dic["module"] == "localfile":
                dic["module"] = "backend_localfile"
                dic["pid"] = str(uuid.uuid4())
                dic["need_conversion"] = \
                    dic["xmlobject"].getAttribute("filename")

        # Now that the backend list is build, we will construct them
        for dic in backends_dic:
            self.restore_backend_from_xml(dic)
        # If no backend available, we create a new using localfile. Xmlobject
        # will be filled in by the backend
        if len(backends_dic) == 0:
            dic = BackendFactory().get_new_backend_dict(
                "backend_localfile")
            dic["backend"].this_is_the_first_run(firstrun_tasks.populate())
            backends_dic.append(dic)
        return backends_dic

    def _read_backend_configuration_file(self):
        '''
        Reads the file describing the current backend configuration
        (project.xml) and returns a list of dictionaries, each containing:
         - the xml object defining the backend characteristics under
              "xmlobject"
         - the name of the backend under "module"
        '''
        # Read configuration file, if it does not exist, create one
        datafile = os.path.join(CoreConfig().get_data_dir(),
                                CoreConfig.DATA_FILE)
        doc, configxml = cleanxml.openxmlfile(datafile, "config")
        xmlproject = doc.getElementsByTagName("backend")
        # collect configured backends
        return [{"xmlobject": xp,
                 "module": xp.getAttribute("module")} for xp in xmlproject]
