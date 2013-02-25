# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Guillaume Desmottes <gdesmott@gnome.org>
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

# this handles old versions of pybugz as well as new ones
try:
    from bugz import bugzilla
    assert bugzilla
except:
    import bugz as bugzilla

# changed the default action to skip auth


class Bug:

    def __init__(self, base, nb):
        # this also handles old versions of pybugz
        try:
            bugs = bugzilla.BugzillaProxy(
                base, skip_auth=True).Bug.get({'ids': [nb, ], })
        except:
            bugs = bugzilla.BugzillaProxy(base).Bug.get({'ids': [nb, ], })
        self.bug = bugs['bugs'][0]

    def get_title(self):
        return self.bug['summary']

    def get_product(self):
        return self.bug['product']

    def get_component(self):
        return self.bug['component']

    def get_description(self):
        return self.bug['summary']

if __name__ == '__main__':
    for bug in [Bug('https://bugzilla.gnome.org', '598354'),
                Bug('https://bugs.freedesktop.org', '24120')]:
        print "title:", bug.get_title()
        print "product:", bug.get_product()
        print "component:", bug.get_component()
        print "description:", bug.get_description()
        print ""
