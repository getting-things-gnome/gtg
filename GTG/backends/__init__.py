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
import logging

from GTG.core.borg import Borg
from GTG.core.config import CoreConfig
from GTG.backends.generic_backend import GenericBackend

log = logging.getLogger(__name__)


class BackendFactory(Borg):
    """
    This class holds the information about the backend types.
    Since it's about types, all information is static. The instantiated
    backends are handled in the Datastore.
    It is a Borg for what matters its only state (_backend_modules),
    since it makes no sense of keeping multiple instances of this.
    """

    BACKEND_PREFIX = "backend_"

    def __init__(self):
        """
         Creates a dictionary of the currently available backend modules
        """
        super().__init__()
        if hasattr(self, "backend_modules"):
            # This object has already been constructed
            return
        self.backend_modules = {}
        backend_files = self._find_backend_files()
        # Create module names
        module_names = [f.replace(".py", "") for f in backend_files]
        log.debug("Backends found: %r", module_names)
        # Load backend modules
        for module_name in module_names:
            extended_module_name = "GTG.backends." + module_name
            try:
                __import__(extended_module_name)
            except ImportError as exception:
                # Something is wrong with this backend, skipping
                log.warning("Backend %s could not be loaded: %r",
                            module_name, exception)
                continue
            except Exception:
                # Other exception log as errors
                log.exception("Malformated backend %s:", module_name)
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
        """
        Returns the backend module for the backend matching
        backend_name. Else, returns none
        """
        if backend_name in self.backend_modules:
            return self.backend_modules[backend_name]
        else:
            log.debug("Trying to load backend %s, but failed!", backend_name)
            return None

    def get_all_backends(self):
        """
        Returns a dictionary containing all the backends types
        """
        return self.backend_modules

    def get_new_backend_dict(self, backend_name, additional_parameters={}):
        """
        Constructs a new backend initialization dictionary. In more
        exact terms, creates a dictionary, containing all the necessary
        entries to initialize a backend.
        """
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

    def get_saved_backends_list(self):
        config = CoreConfig()
        backends = []

        for backend in config.get_all_backends():
            settings = config.get_backend_config(backend)
            module = self.get_backend(settings.get('module'))

            # Skip this backend if it doesn't have a module
            if not module:
                log.debug(f"Could not load module for backend {module}")
                continue

            backend_data = {}
            specs = module.Backend.get_static_parameters()
            backend_data['pid'] = str(settings.get('pid'))
            backend_data["first_run"] = False

            for param_name, param_dic in specs.items():

                try:
                    # We need to convert the parameter to the right format.
                    # We fetch the format from the static_parameters
                    param_type = param_dic[GenericBackend.PARAM_TYPE]
                    param_value = GenericBackend.cast_param_type_from_string(
                        settings.get(param_name), param_type)

                    backend_data[param_name] = param_value

                except ValueError:
                    # Parameter not found in config
                    pass

            backend_data['backend'] = module.Backend(backend_data)
            backends.append(backend_data)

        # If no backend available, we create a new using localfile. Dic
        # will be filled in by the backend
        if not backends:
            dic = BackendFactory().get_new_backend_dict(
                "backend_localfile")

            dic["first_run"] = True
            backends.append(dic)

        return backends
