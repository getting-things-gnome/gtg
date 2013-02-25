# -*- coding: utf-8 -*-
# Copyright (c) 2010 - Luca Invernizzi <invernizzi.l@gmail.com>
#               2012 - Izidor Matušov <izidor.matusov@gmail.com>
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

""" Module for discovering templates and work with templates """

from glob import glob
import os.path
import subprocess
import sys
import tempfile
import threading

from Cheetah.Template import Template as CheetahTemplate
from xdg.BaseDirectory import xdg_config_home
import gobject

TEMPLATE_PATHS = [
    os.path.join(xdg_config_home, "gtg/plugins/export/export_templates"),
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "export_templates"),
]


def get_templates_paths():
    """ Returns a list containing the full path for all the
    available templates. """
    template_list = []
    for a_dir in TEMPLATE_PATHS:
        template_list += glob(os.path.join(a_dir, "template_*"))
    return template_list


class Template:
    """ Representation of a template """

    def __init__(self, path):
        self._template = path
        self._document_path = None

        self._image_path = self._find_file("thumbnail_")
        self._script_path = self._find_file("script_")

        self._title, self._description = self._load_description()

    def _find_file(self, prefix, suffix=""):
        """ Find a file for the template given prefix and suffix """
        basename = os.path.basename(self._template)
        basename = basename.replace("template_", prefix)
        path = os.path.join(os.path.dirname(self._template), basename)
        path = os.path.splitext(path)[0] + '*' + suffix
        possible_filles = glob(path)
        if len(possible_filles) > 0:
            return possible_filles[0]
        else:
            return None

    def _load_description(self):
        """ Returns title and description of the template
        template description are stored in python module for easier l10n.
        thus, we need to import the module given its path """
        path = self._find_file("description_", ".py")
        if not path:
            return "", ""
        dir_path = os.path.dirname(path)
        if dir_path not in sys.path:
            sys.path.append(dir_path)
        module_name = os.path.basename(path).replace(".py", "")
        try:
            module = __import__(module_name, globals(), locals(),
                                ['description'], 0)
            return module.title, module.description
        except (ImportError, AttributeError):
            return "", ""

    def _get_suffix(self):
        """ Return suffix of the template """
        return os.path.splitext(self._template)[1]

    def get_path(self):
        """ Return path to the template """
        return self._template

    def get_image_path(self):
        """ Return path to the image """
        return self._image_path

    def get_title(self):
        """ Return title of the template """
        return self._title

    def get_description(self):
        """ Return description of the template """
        return self._description

    def get_document_path(self):
        """ Return path to generated document.
        Return None until generate() was successful."""
        return self._document_path

    def generate(self, tasks, plugin_api, callback):
        """ Fill template and run callback when finished.

        Created files are saved with the same suffix as the template. Opening
        the final file determines its type based on suffix. """
        document = CheetahTemplate(file=self.get_path(),
                                   searchList=[{'tasks': tasks,
                                                'plugin_api': plugin_api}])

        suffix = ".%s" % self._get_suffix()
        output = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        output.write(str(document))
        self._document_path = output.name
        output.close()

        if self._script_path:
            self._run_script(callback)
        else:
            callback()

    def _run_script(self, callback):
        """ Run script in its own thread and in other thread wait
        for the result. """
        document_ready = threading.Event()

        def script():
            """ Run script using the shebang of the script

            The script gets path to a document as it only argument and
            this thread expects resulting file as the only output of
            the script. """

            with open(self._script_path, 'r') as script_file:
                first_line = script_file.readline().strip()
                if first_line.startswith('#!'):
                    cmd = [first_line[2:], self._script_path,
                           self._document_path]
                else:
                    cmd = None

            self._document_path = None

            if cmd is not None:
                try:
                    self._document_path = subprocess.Popen(
                        args=cmd, shell=False,
                        stdout=subprocess.PIPE).communicate()[0]
                except Exception:
                    pass

            if self._document_path and not os.path.exists(self._document_path):
                self._document_path = None
            document_ready.set()

        def wait_for_document():
            """ Wait for the completion of the script and finish generation """
            document_ready.wait()
            gobject.idle_add(callback)

        threading.Thread(target=script).start()
        threading.Thread(target=wait_for_document).start()
