# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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
'''
This module reads a bakcn configuration and generates a series of widgets to
let the user see the configuration and modify it.
In this manner, backends do not need to know anything about their UI since it's
built for them: it should play along the lines of the separation between GTG
server and client
'''

import gtk
import functools

from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG.gtk.backends_dialog.parameters_ui.importtagsui import ImportTagsUI
from GTG.gtk.backends_dialog.parameters_ui.textui import TextUI
from GTG.gtk.backends_dialog.parameters_ui.passwordui import PasswordUI
from GTG.gtk.backends_dialog.parameters_ui.periodui import PeriodUI
from GTG.gtk.backends_dialog.parameters_ui.checkboxui import CheckBoxUI
from GTG.gtk.backends_dialog.parameters_ui.pathui import PathUI


class ParametersUI(gtk.VBox):
    '''
    Given a bakcend, this gtk.VBox populates itself with all the necessary
    widgets to view and edit a backend configuration
    '''

    COMMON_WIDTH = 170

    def __init__(self, requester):
        '''Constructs the list of the possible widgets.

        @param requester: a GTG.core.requester.Requester object
        '''
        super(ParametersUI, self).__init__(False)
        self.req = requester
        self.set_spacing(10)

        # builds a list of widget generators. More precisely, it's a
        # list of tuples: (backend_parameter_name, widget_generator)
        self.parameter_widgets = (
            ("import-tags", self.UI_generator(ImportTagsUI, {
                "title": _("Import tags"),
                "anybox_text": _("All tags"),
                "somebox_text": _("Just these tags:"),
                "parameter_name": "import-tags",
            })),
            ("attached-tags", self.UI_generator(ImportTagsUI, {
                "title": _("Tags to sync"),
                "anybox_text": _("All tasks"),
                "somebox_text": _("Tasks with these tags:"),
                "parameter_name": "attached-tags",
            })),
            ("path", self.UI_generator(PathUI)),
            ("username", self.UI_generator(TextUI, {
                "description": _("Username"),
                "parameter_name": "username",
            })),
            ("password", self.UI_generator(PasswordUI)),
            ("period", self.UI_generator(PeriodUI)),
            ("service-url", self.UI_generator(TextUI, {
                "description": _("Service URL"),
                "parameter_name": "service-url",
            })),
            ("import-from-replies", self.UI_generator(CheckBoxUI, {
                "text": _("Import tasks from @ replies directed to you"),
                "parameter": "import-from-replies",
            })),
            ("import-from-direct-messages", self.UI_generator(CheckBoxUI, {
                "text": _("Import tasks from direct messages"),
                "parameter": "import-from-direct-messages",
            })),
            ("import-from-my-tweets", self.UI_generator(CheckBoxUI, {
                "text": _("Import tasks from your tweets"),
                "parameter": "import-from-my-tweets",
            })),
            ("import-bug-tags", self.UI_generator(CheckBoxUI, {
                "text": _("Tag your GTG tasks with the bug tags"),
                "parameter": "import-bug-tags",
            })),
            ("tag-with-project-name", self.UI_generator(CheckBoxUI, {
                "text": _("Tag your GTG tasks with the project "
                     "targeted by the bug"),
                "parameter": "tag-with-project-name",
            })),
        )

    def UI_generator(self, param_type, special_arguments={}):
        '''A helper function to build a widget type from a template.
        It passes to the created widget generator a series of common
         parameters, plus the ones needed to specialize the given template

        @param param_type: the template to specialize
        @param special_arguments: the arguments used for this particular widget
                                  generator.

        @return function: return a widget generator, not a widget. the widget
                           can be obtained by calling widget_generator(backend)
        '''
        return lambda backend: param_type(req=self.req,
                                          backend=backend,
                                          width=self.COMMON_WIDTH,
                                          **special_arguments)

    def refresh(self, backend):
        '''Builds the widgets necessary to configure the backend. If it doesn't
        know how to render a widget, it simply skips it.

        @param backend: the backend that is being configured
        '''
        # remove the old parameters UIs
        def _remove_child(self, child):
            self.remove(child)
        self.foreach(functools.partial(_remove_child, self))
        # add new widgets
        backend_parameters = backend.get_parameters()
        if backend_parameters[GenericBackend.KEY_DEFAULT_BACKEND]:
            # if it's the default backend, the user should not mess with it
            return
        for parameter_name, widget in self.parameter_widgets:
            if parameter_name in backend_parameters:
                self.pack_start(widget(backend), True)
        self.show_all()

    def commit_changes(self):
        '''
        Saves all the parameters at their current state (the user may have
        modified them)
        '''

        def _commit_changes(child):
            child.commit_changes()
        self.foreach(_commit_changes)
