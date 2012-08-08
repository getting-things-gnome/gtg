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

#this handles old versions of pybugz as well as new ones
try:
    from bugz import bugzilla
except:
    import bugz as bugzilla

#changed the default action to skip auth

class Bug:

    def __init__(self, base, nb):
        #this also handles old versions of pybugz
        try:
            self.bug = bugzilla.Bugz(base, skip_auth=True).get(nb)
        except:
            self.bug = bugzilla.Bugz(base).get(nb)
        if self.bug is None:
            raise Exception('Failed to create bug')

    def _get_detail(self, detail):
        tmp = self.bug.find('//%s' % detail)
        if tmp is None:
            return None

        return tmp.text

    def get_title(self):
        return self._get_detail('short_desc')

    def get_product(self):
        return self._get_detail('product')

    def get_component(self):
        return self._get_detail('component')

    def get_description(self):
        comment = self.bug.findall('//long_desc')[0]
        return comment.find('.//thetext').text

if __name__ == '__main__':
    for bug in [Bug('http://bugzilla.gnome.org', '598354'),
            Bug('http://bugs.freedesktop.org', '24120')]:
        print "title:", bug.get_title()
        print "product:", bug.get_product()
        print "component:", bug.get_component()
        print "description:", bug.get_description()
        print ""
