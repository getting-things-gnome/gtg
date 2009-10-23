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

from bugz import Bugz

class Bug:
    def __init__(self, base, nb):
        self.bug = Bugz(base).get(nb)

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

if __name__ == '__main__':
     for bug in [Bug('http://bugzilla.gnome.org', '598354'),
         Bug('http://bugs.freedesktop.org', '24120')]:
        print "title:", bug.get_title()
        print "product:", bug.get_product()
        print "component:", bug.get_component()
