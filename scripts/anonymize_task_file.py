#!/usr/bin/env python3

# Copyright © 2010 Marko Kevac <marko@kevac.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import sys
import re

from xml.dom.minidom import parse

from gi.repository import GLib

def anonymize(filename, outputfile):
    try:
        dom = parse(filename)
    except Exception as err:
        print("error while parsing %s: %s" % (filename, err))
        return

    tasks = dom.getElementsByTagName("task")

    for task in tasks:
        textnode = task.getElementsByTagName("title")[0].childNodes[0]
        nodevalue = textnode.nodeValue
        replaced_title = re.sub('[^ \n\t]', 'm', textnode.nodeValue)
        textnode.nodeValue = "%s %s" % (task.getAttribute('id'),
                                        replaced_title)

        contentnode = task.getElementsByTagName("content")
        if len(contentnode) == 0:
            continue

        if contentnode[0].childNodes != []:
            contentnode = contentnode[0].childNodes[0]
            contentnode.nodeValue = re.sub('[^ \n\t]', 'm',
                                           contentnode.nodeValue)

    taglist = dom.getElementsByTagName("taglist")
    tags = taglist[0].getElementsByTagName("tag")
    tag_dict = {}

    for tag in tags:
        tag_dict[tag.getAttribute("name")] = tag.getAttribute("id")

    for tag in tags:
        tag.setAttribute("name", tag.getAttribute("id"))
        if tag.getAttribute('parent') != '':
            tag.setAttribute("parent",
                             tag_dict.get(tag.getAttribute("parent"), 'unk'))

    searchlist = dom.getElementsByTagName("searchlist")
    searches = searchlist[0].getElementsByTagName("savedSearch")
    search_dict = {}

    for search in searches:
        search_dict[search.getAttribute("name")] = search.getAttribute("id")

    for search in searches:
        search.setAttribute("query", "anon")
        search.setAttribute("name", search.getAttribute("id"))
        if search.getAttribute('parent') != 'search' \
                and search.getAttribute('parent') != '':
            search.setAttribute("parent",
                                search_dict.get(search.getAttribute("parent"),
                                                'search'))

    try:
        fp = open(outputfile, "w")
        fp.write(dom.toxml())
    except Exception as err:
        print("error while saving output file: %s" % err)


def usage():
    print("Usage: %s [taskfile] [outputfile]" % sys.argv[0])
    print()
    print("Removes private data from specified taskfile, or your")
    print("default gtg tasks file if unspecified.  Writes output")
    print("to /tmp/gtg_data.xml by default, or to specified")
    print("outputfile if provided.")
    sys.exit(1)


def main():
    if len(sys.argv) > 1:
        xmlfile = sys.argv[1]
    else:
        try:
            local_dir = os.path.join(GLib.get_user_data_dir(), "gtg")
            flatpak_dir = os.path.join(GLib.get_home_dir(),
                                       '.var', 'app',
                                       'org.gnome.GTG',
                                       'data', 'gtg')

            local_xml = os.path.join(local_dir, "gtg_data.xml")
            flatpak_xml = os.path.join(flatpak_dir, "gtg_data.xml")

            try:
                local_xml_time = os.path.getmtime(local_xml)
            except OSError:
                local_xml_time = 0

            try:
                flatpak_xml_time = os.path.getmtime(flatpak_xml)
            except OSError:
                flatpak_xml_time = 0

            if local_xml_time == flatpak_xml_time:
                if os.path.exists(flatpak_xml):
                    xmlfile = flatpak_xml
                elif os.path.exists(local_xml):
                    xmlfile = local_xml
                else:
                    print("Could not find the data file in default locations")
                    raise Exception("Could not find data file in default "
                                    "locations")
            elif local_xml_time < flatpak_xml_time:
                xmlfile = flatpak_xml
            elif local_xml_time > flatpak_xml_time:
                xmlfile = local_xml
            else:
                print("This should not happen")

            print("Reading tasks from %s" % (xmlfile))
        except Exception:
            print()
            usage()

    if len(sys.argv) > 2:
        outputfile = sys.argv[2]
    else:
        # Use a reasonable default, and write out where it's sent
        outputfile = "/tmp/gtg_data.xml"
        print("Saving anonymized tasks to %s" % (outputfile))

    anonymize(xmlfile, outputfile)


if __name__ == "__main__":
    main()
