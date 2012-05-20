# -*- coding: utf-8 -*-
# Copyright (c) 2010 - Luca Invernizzi <invernizzi.l@gmail.com>
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

import sys
import glob
import os.path
from xdg.BaseDirectory import xdg_config_home

from GTG.tools.borg import Borg


class TemplateFactory(Borg):
    '''
    A Factory which provides an easy access to the templates. It caches
    templates for the sake of speed.
    '''

    TEMPLATE_PATHS = [\
            os.path.join(xdg_config_home,
                         "gtg/plugins/export/export_templates"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "export_templates/")]

    def __init__(self):
        super(TemplateFactory, self).__init__()
        if hasattr(self, "_cache"):
            #The borg has already been initialized
            return
        self._cache = {}

    @classmethod
    def get_templates_paths(cls):
        '''
        Returns a list containing the full path for all the
        available templates
        '''
        template_list = []
        for a_dir in TemplateFactory.TEMPLATE_PATHS:
            template_list += glob.glob(os.path.join(a_dir, "template_*"))
        return template_list

    def create_template(self, path):
        if not path:
            return None
        if not path in self._cache:
            self._cache[path] = Template(path)
        return self._cache[path]



class Template(object):


    def __init__(self, path):
        self.__template_path = path
        self.__image_path = self.__find_template_file(path, "thumbnail_")
        self.__script_path = self.__find_template_file(path, "script_")
        self.__description = ""
        self.__title = ""
        description_path = \
                self.__find_template_file(path, "description_", ".py")
        if description_path:
            #template description are stored in python module for easier l10n.
            #thus, we need to import the module given its path
            directory_path= os.path.dirname(description_path)
            if directory_path not in sys.path:
                sys.path.append(directory_path)
            module_name = os.path.basename(\
                            description_path).replace(".py", "")
            try:
                module = __import__(module_name,
                                    globals(),
                                    locals(),
                                    ['description'],
                                    0)
                self.__description =  module.description
                self.__title =  module.title
            except (ImportError, AttributeError):
                pass

    @classmethod
    def __find_template_file(cls, path, prefix, suffix = ""):
        basename = os.path.basename(path).replace("template_", prefix)
        path = os.path.join(os.path.dirname(path), basename)
                            
        path = "%s*" % path[: path.rindex(".") - 1]
        try:
            possible_paths = glob.glob(path)
            return filter(lambda p: p.endswith(suffix), possible_paths)[0]
        except:
            return None

    def get_path(self):
        return self.__template_path

    def get_image_path(self):
        return self.__image_path

    def get_script_path(self):
        return self.__script_path

    def get_suffix(self):
        return self.__template_path[self.__template_path.rindex(".") +1 :]

    def get_description(self):
        return self.__description

    def get_title(self):
        return self.__title
