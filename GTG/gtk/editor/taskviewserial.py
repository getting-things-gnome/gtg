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

import xml.dom.minidom


# The following functions are used by the gtk.TextBuffer to serialize
# the content of the task

########### Serializing functions ##############
### Serialize the task : transform it's content in something
# we can store. This function signature is defined in PyGTK

class Serializer:
    def serialize(self, register_buf, content_buf, start, end, udata):
        # Currently we serialize in XML
        its = start.copy()
        ite = end.copy()
        # Warning : the serialization process cannot be allowed to modify
        # the content of the buffer.
        doc = xml.dom.minidom.Document()
        parent = doc.createElement("content")
        doc.appendChild(self.parse_buffer(content_buf, its, ite, parent, doc))
        # We don't want the whole doc with the XML declaration
        # we only take the first node (the "content" one)
        node = doc.firstChild
        # print "********************"
        # print node.toxml().encode("utf-8")
        return node.toxml().encode("utf-8")

    def parse_buffer(self, buff, start, end, parent, doc, done=[]):
        """
        Parse the buffer and output an XML representation.

            @var buff, start, end  : the buffer to parse from start to end
            @var parent, doc: the XML element to add data and doc is
                                the XML dom
            @var done : the list of parsed tags
        """

        def is_know_tag(tag):
            """
            Return True if "tag" is a know tag. "tag" must be a gtk.TextTag.
            """
            know_tags = ["is_subtask", "is_indent", "is_tag"]
            for know in know_tags:
                if tag.get_data(know):
                    return True
            return False
        it = start.copy()
        tag = None
        start_it = start.copy()
        end_it = start.copy()

        buffer_end = False
        while not buffer_end:
            if tag is None:
                # We are not in a tag context
                # Get list of know tags which begin here
                # and are not already process
                tags = []
                for ta in it.get_tags():
                    if it.begins_tag(ta) and ta not in done and \
                            is_know_tag(ta):
                        tags.append(ta)
                        # print ta.get_data("tagname")
                if it.begins_tag() and len(tags) > 0:
                    # We enter in a tag context
                    tag = tags.pop()
                    done.append(tag)
                    start_it = it.copy()
                else:
                    # We stay out of a tag context
                    # We write the char in the xml node
                    if it.get_char() != "\0":
                        parent.appendChild(doc.createTextNode(it.get_char()))
            else:
                # We are in a tag context
                if it.ends_tag(tag) or it.equal(end):
                    # There is the end of the gtkTextTag
                    # We process the tag
                    end_it = it.copy()
                    end_it.backward_char()
                    if tag.get_data("is_tag"):
                        # The current gtkTextTag is a tag
                        # Recursive call
                        nparent = doc.createElement("tag")
                        child = self.parse_buffer(buff, start_it, end_it,
                                                  nparent, doc, done=done)
                        parent.appendChild(child)
                    elif ta.get_data('is_subtask'):
                        # The current gtkTextTag is a subtask
                        tagname = "subtask"
                        subt = doc.createElement(tagname)
                        target = ta.get_data('child')
                        subt.appendChild(doc.createTextNode(target))
                        parent.appendChild(subt)
                        parent.appendChild(doc.createTextNode("\n"))
                        it.forward_line()
                    elif ta.get_data('is_indent'):
                        # The current gtkTextTag is a indent
                        indent = buff.get_text(start_it, end_it)
                        if '\n' in indent:
                            parent.appendChild(doc.createTextNode('\n'))
                        it = end_it
                    # We go out the tag context
                    tag = None
                    if not it.equal(end):
                        it.backward_char()
            if it.equal(end):
                buffer_end = True
            else:
                it.forward_char()

        # Finishing with an \n before closing </content>
        if parent.localName == "content":
            last_val = parent.lastChild
            # We add a \n only if needed (= we don't have a "\n" at the end)
            if last_val and last_val.nodeType == 3 and \
                    last_val.nodeValue[-1] != '\n':
                parent.appendChild(doc.createTextNode('\n'))
        # This function concatenates all the adjacent text node of the XML
        parent.normalize()
        return parent


######################## Deserializing ##################################
### Deserialize : put all in the TextBuffer
# This function signature is defined in PyGTK

class Unserializer:

    def __init__(self, taskview):
        # We keep a reference to the original taskview
        # Not very pretty but convenient
        self.tv = taskview

    def unserialize(self, register_buf, content_buf, ite, data,
                    cr_tags, udata):
        if data:
            element = xml.dom.minidom.parseString(data)
            success = self.parsexml(content_buf, ite, element.firstChild)
        else:
            success = self.parsexml(content_buf, ite, None)
        return success

    # Insert a list of subtasks at the end of the buffer
    def insert_subtasks(self, buff, st_list):
        # If the lastline of the buffer is not empty, we add an extra \n
        end_end = buff.get_end_iter()
        end_line = end_end.get_line()
        start_end = buff.get_iter_at_line(end_line)
        if buff.get_text(start_end, end_end).strip():
            end_line += 1
        for tid in st_list:
            self.tv.write_subtask(buff, end_line, tid)
            end_line += 1

    # insert a GTG tag with its TextView tag.
    # Yes, we know : the word tag is used for two different concepts here.
    def insert_tag(self, buff, tag, itera=None):
        if not itera:
            itera = buff.get_end_iter()
        if tag:
            sm = buff.create_mark(None, itera, True)
            em = buff.create_mark(None, itera, False)
            buff.insert(itera, tag)
            self.tv.apply_tag_tag(buff, tag, sm, em)

    # parse the XML and put the content in the buffer
    def parsexml(self, buf, ite, element):
        start = buf.create_mark(None, ite, True)
        end = buf.create_mark(None, ite, False)
        subtasks = self.tv.get_subtasks()
        taglist2 = []
        if element:
            for n in element.childNodes:
                itera = buf.get_iter_at_mark(end)
                if n.nodeType == n.ELEMENT_NODE:
                    # print "<%s>" %n.nodeName
                    if n.nodeName == "subtask":
                        tid = n.firstChild.nodeValue
                        # We remove the added subtask from the list
                        # Of known subtasks
                        # If the subtask is not in the list, we don't write it
                        if tid in subtasks:
                            subtasks.remove(tid)
                            line_nbr = itera.get_line()
                            self.tv.write_subtask(buf, line_nbr, tid)
                    elif n.nodeName == "tag":
                        text = n.firstChild.nodeValue
                        if text:
                            self.insert_tag(buf, text, itera)
                            # We remove the added tag from the tag list
                            # of known tag for this task
                            taglist2.append(text)
                    else:
                        self.parsexml(buf, itera, n)
                        s = buf.get_iter_at_mark(start)
                        e = buf.get_iter_at_mark(end)
                        if n.nodeName == "link":
                            anchor = n.getAttribute("target")
                            tag = self.tv.create_anchor_tag(buf, anchor, None)
                            buf.apply_tag(tag, s, e)
                        else:
                            buf.apply_tag_by_name(n.nodeName, s, e)
                elif n.nodeType == n.TEXT_NODE:
                    buf.insert(itera, n.nodeValue)
        # Now, we insert the remaining subtasks
        self.insert_subtasks(buf, subtasks)
        # We also insert the remaining tags (a a new line)
        taglist = self.tv.get_tagslist()
        for t in taglist2:
            if t in taglist:
                taglist.remove(t)
        # We remove duplicates
        for t in taglist:
            while t in taglist:
                taglist.remove(t)
            taglist.append(t)
        if len(taglist) > 0:
            self.tv.insert_tags(taglist)
        buf.delete_mark(start)
        buf.delete_mark(end)
        return True
