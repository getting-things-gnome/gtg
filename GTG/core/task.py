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

"""
task.py contains the Task class which represents (guess what) a task
"""
from datetime import datetime
import cgi
import re
import uuid
import xml.dom.minidom
import xml.sax.saxutils as saxutils

from GTG import _
from GTG.tools.dates import Date
from GTG.tools.logger import Log
from liblarch import TreeNode
from GTG.tools.tags import extract_tags_from_text


class Task(TreeNode):
    """ This class represent a task in GTG.
    You should never create a Task directly. Use the datastore.new_task()
    function."""

    STA_ACTIVE = "Active"
    STA_DISMISSED = "Dismiss"
    STA_DONE = "Done"

    def __init__(self, ze_id, requester, newtask=False):
        TreeNode.__init__(self, ze_id)
        # the id of this task in the project should be set
        # tid is a string ! (we have to choose a type and stick to it)
        assert(isinstance(ze_id, str) or isinstance(ze_id, unicode))
        self.tid = str(ze_id)
        self.set_uuid(uuid.uuid4())
        self.remote_ids = {}
        self.content = ""
        self.title = _("My new task")
        # available status are: Active - Done - Dismiss - Note
        self.status = self.STA_ACTIVE
        self.closed_date = Date.no_date()
        self.due_date = Date.no_date()
        self.start_date = Date.no_date()
        self.can_be_deleted = newtask
        # tags
        self.tags = []
        self.req = requester
        self.__main_treeview = requester.get_main_view()
        # If we don't have a newtask, we will have to load it.
        self.loaded = newtask
        # Should not be necessary with the new backends
#        if self.loaded:
#            self.req._task_loaded(self.tid)
        self.attributes = {}
        self._modified_update()

    def is_loaded(self):
        return self.loaded

    def set_loaded(self, signal=True):
        # avoid doing it multiple times
        if not self.loaded:
            self.loaded = True

    def set_to_keep(self):
        self.can_be_deleted = False

    def is_new(self):
        return self.can_be_deleted

    def get_id(self):
        return str(self.tid)

    def set_uuid(self, value):
        self.uuid = str(value)

    def get_uuid(self):
        # NOTE: Transitional if switch, needed to add
        #      the uuid field to tasks created before
        #      adding this field to the task description.
        if self.uuid == "":
            self.set_uuid(uuid.uuid4())
            self.sync()
        return str(self.uuid)

    def get_remote_ids(self):
        '''
        A task usually has a different id in all the different backends.
        This function returns a dictionary backend_id->the id the task has
        in that backend
        @returns dict: dictionary backend_id->task remote id
        '''
        return self.remote_ids

    def add_remote_id(self, backend_id, task_remote_id):
        '''
        A task usually has a different id in all the different backends.
        This function adds a relationship backend_id-> remote_id that can be
        retrieved using get_remote_ids
        @param backend_id: string representing the backend id
        @param task_remote_id: the id for this task in the backend backend_id
        '''
        self.remote_ids[str(backend_id)] = str(task_remote_id)

    def get_title(self):
        return self.title

    # Return True if the title was changed.
    # False if the title was already the same.
    def set_title(self, title):
        # We should check for other task with the same title
        # In that case, we should add a number (like Tomboy does)
        old_title = self.title
        if isinstance(title, str):
            title = title.decode('utf8')
        if title:
            self.title = title.strip('\t\n')
        else:
            self.title = "(no title task)"
        # Avoid unnecessary sync
        if self.title != old_title:
            self.sync()
            return True
        else:
            return False

    # TODO : should we merge this function with set_title ?
    def set_complex_title(self, text, tags=[]):
        if tags:
            assert(isinstance(tags[0], str))
        due_date = Date.no_date()
        defer_date = Date.no_date()
        if text:
            # Get tags in the title
            for match in extract_tags_from_text(text):
                tags.append(match)
            # Get attributes
            regexp = r'([\s]*)([\w-]+):\s*([^\s]+)'
            matches = re.findall(regexp, text, re.UNICODE)
            for spaces, attribute, args in matches:
                valid_attribute = True
                if attribute.lower() in ["tags", _("tags"), "tag", _("tag")]:
                    for tag in args.split(","):
                        if not tag.strip() == "@" and not tag.strip() == "":
                            if not tag.startswith("@"):
                                tag = "@" + tag
                            tags.append(tag)
                elif attribute.lower() in ["defer", _("defer"), "start",
                                           _("start")]:
                    try:
                        defer_date = Date.parse(args)
                    except ValueError:
                        valid_attribute = False
                elif attribute.lower() == "due" or \
                        attribute.lower() == _("due"):
                    try:
                        due_date = Date.parse(args)
                    except:
                        valid_attribute = False
                else:
                    # attribute is unknown
                    valid_attribute = False

                if valid_attribute:
                    # remove valid attribute from the task title
                    text = \
                        text.replace("%s%s:%s" % (spaces, attribute, args), "")

            for t in tags:
                self.add_tag(t)

            if text != "":
                self.set_title(text.strip())
                self.set_to_keep()

            self.set_due_date(due_date)
            self.set_start_date(defer_date)

    def set_status(self, status, donedate=None):
        old_status = self.status
        self.can_be_deleted = False
        # No need to update children or whatever if the task is not loaded
        if status and self.is_loaded():
            # we first modify the status of the children
            # If Done, we set the done date
            if status in [self.STA_DONE, self.STA_DISMISSED]:
                for c in self.get_subtasks():
                    if c.get_status() in [self.STA_ACTIVE]:
                        c.set_status(status, donedate=donedate)
            # If we mark a task as Active and that some parent are not
            # Active, we break the parent/child relation
            # It has no sense to have an active subtask of a done parent.
            # (old_status check is necessary to avoid false positive a start)
            elif status in [self.STA_ACTIVE] and\
                    old_status in [self.STA_DONE, self.STA_DISMISSED]:
                if self.has_parent():
                    for p_tid in self.get_parents():
                        par = self.req.get_task(p_tid)
                        if par.is_loaded() and par.get_status() in\
                                [self.STA_DONE, self.STA_DISMISSED]:
                            # we can either break the parent/child relationship
                            # self.remove_parent(p_tid)
                            # or restore the parent too
                            par.set_status(self.STA_ACTIVE)
                # We dont mark the children as Active because
                # They might be already completed after all

        # then the task itself
        if status:
            self.status = status

        # Set closing date
        if status and status in [self.STA_DONE, self.STA_DISMISSED]:
            # to the specified date (if any)
            if donedate:
                self.closed_date = donedate
            # or to today
            else:
                self.closed_date = Date.today()
        self.sync()

    def get_status(self):
        return self.status

    def get_modified(self):
        return self.last_modified

    def get_modified_string(self):
        return self.last_modified.strftime("%Y-%m-%dT%H:%M:%S")

    def set_modified(self, modified):
        self.last_modified = modified

    def recursive_sync(self):
        """Recursively sync the task and all task children. Defined"""
        self.sync()
        for sub_id in self.children:
            sub = self.req.get_task(sub_id)
            sub.recursive_sync()

    # ABOUT DUE DATES
    #
    # PLEASE READ THIS: although simple in appearance, handling task dates can
    # actually be subtle. Take the time to understand this if you plan to work
    # on the methods below.
    #
    # Due date is the date at which a task must be accomplished. Constraints
    # exist between a task's due date and its ancestor/children's due dates.
    #
    # Date constraints
    #
    # Those are the following:
    #   - children of a task cannot have a task due date that happens later
    #     than the task's due date
    #   - ancestors of a task cannot have a due that happens before the
    #     task's due date (this is the reverse constraint from the first one)
    #   - a task's start date cannot happen later than this task's due date
    #
    # Tasks with undefined or fuzzy due dates
    #
    # Task with no due date (="undefined" tasks) or tasks with fuzzy start/due
    # dates are not subject to constraints. Furthermore, they are
    # "transparent". Meaning that they let the constraints coming from their
    # children/parents pass through them. So, for instance, a children of
    # a task with an undefined or fuzzy task would be constrained by this
    # latter task's ancestors. Equally, the an ancestor from the same
    # undefined/fuzzy task would be constrained by the children due dates.
    #
    # Updating a task due date
    #
    # Whenever a task due date is changed, all ancestor/chldren of this task
    # *must* be updated according to the constraining rules. As said above,
    # constraints must go through tasks with undefined/fuzzy due dates too!
    #
    # Undefined/fuzzy task dates are NEVER to be updated. They are not
    # sensitive to constraint. If you want to now what constraint there is
    # on this task's due date though, you can obtain it by using
    # get_due_date_constraint method.
    def set_due_date(self, new_duedate):
        """Defines the task's due date."""

        def __get_defined_parent_list(task):
            """Recursively fetch a list of parents that have a defined due date
               which is not fuzzy"""
            parent_list = []
            for par_id in task.parents:
                par = self.req.get_task(par_id)
                if par.get_due_date().is_fuzzy():
                    parent_list += __get_defined_parent_list(par)
                else:
                    parent_list.append(par)
            return parent_list

        def __get_defined_child_list(task):
            """Recursively fetch a list of children that have a defined
               due date which is not fuzzy"""
            child_list = []
            for child_id in task.children:
                child = self.req.get_task(child_id)
                if child.get_due_date().is_fuzzy():
                    child_list += __get_defined_child_list(child)
                else:
                    child_list.append(child)
            return child_list

        old_due_date = self.due_date
        new_duedate_obj = Date(new_duedate)  # caching the conversion
        self.due_date = new_duedate_obj
        # If the new date is fuzzy or undefined, we don't update related tasks
        if not new_duedate_obj.is_fuzzy():
            # if the task's start date happens later than the
            # new due date, we update it (except for fuzzy dates)
            if not self.get_start_date().is_fuzzy() and \
                    self.get_start_date() > new_duedate_obj:
                self.set_start_date(new_duedate)
            # if some ancestors' due dates happen before the task's new
            # due date, we update them (except for fuzzy dates)
            for par in __get_defined_parent_list(self):
                if par.get_due_date() < new_duedate_obj:
                    par.set_due_date(new_duedate)
            # we must apply the constraints to the defined & non-fuzzy children
            # as well
            for sub in __get_defined_child_list(self):
                sub_duedate = sub.get_due_date()
                # if the child's due date happens later than the task's: we
                # update it to the task's new due date
                if sub_duedate > new_duedate_obj:
                    sub.set_due_date(new_duedate)
                # if the child's start date happens later than
                # the task's new due date, we update it
                # (except for fuzzy start dates)
                sub_startdate = sub.get_start_date()
                if not sub_startdate.is_fuzzy() and \
                        sub_startdate > new_duedate_obj:
                    sub.set_start_date(new_duedate)
        # If the date changed, we notify the change for the children since the
        # constraints might have changed
        if old_due_date != new_duedate_obj:
            self.recursive_sync()

    def get_due_date(self):
        """ Returns the due date, which always respects all constraints """
        return self.due_date

    def get_urgent_date(self):
        """Returns the most urgent due date among the task and it's subtasks"""
        urg_date = self.due_date
        for sub in self.get_subtasks():
            sub_urg_date = sub.get_urgent_date()
            if urg_date >= sub_urg_date:
                urg_date = sub_urg_date
        return urg_date

    def get_due_date_constraint(self):
        """ Returns the most urgent due date constraint, following
            parents' due dates. Return Date.no_date() if no constraint
            is applied. """
        # Check out for constraints depending on date definition/fuzziness.
        strongest_const_date = self.due_date
        if strongest_const_date.is_fuzzy():
            for par_id in self.parents:
                par = self.req.get_task(par_id)
                par_duedate = par.get_due_date()
                # if parent date is undefined or fuzzy, look further up
                if par_duedate.is_fuzzy():
                    par_duedate = par.get_due_date_constraint()
                # if par_duedate is still undefined/fuzzy, all parents' due
                # dates are undefined or fuzzy: strongest_const_date is then
                # the best choice so far, we don't update it.
                if par_duedate.is_fuzzy():
                    continue
                # par_duedate is not undefined/fuzzy. If strongest_const_date
                # is still undefined or fuzzy, parent_duedate is the best
                # choice.
                if strongest_const_date.is_fuzzy():
                    strongest_const_date = par_duedate
                    continue
                # strongest_const_date and par_date are defined and not fuzzy:
                # we compare the dates
                if par_duedate < strongest_const_date:
                    strongest_const_date = par_duedate
        return strongest_const_date

    # ABOUT START DATE
    #
    # Start date is the date at which the user has decided to work or consider
    # working on this task.
    #
    # The only constraint applied to start dates is that start dates cannot
    # happen later than the task due date.
    #
    # The task due date (and any constrained relatives) is updated if a new
    # task start date is chosen that does not respect this rule.
    #
    # Undefined/fizzy start dates don't constraint the task due date.
    def set_start_date(self, fulldate):
        self.start_date = Date(fulldate)
        if not Date(fulldate).is_fuzzy() and \
            not self.due_date.is_fuzzy() and \
                Date(fulldate) > self.due_date:
            self.set_due_date(fulldate)
        self.sync()

    def get_start_date(self):
        return self.start_date

    # ABOUT CLOSED DATE
    #
    # Closed date is the date at which the task has been closed (done or
    # dismissed). Closed date is not constrained and doesn't constrain other
    # dates.
    def set_closed_date(self, fulldate):
        self.closed_date = Date(fulldate)
        self.sync()

    def get_closed_date(self):
        return self.closed_date

    def get_days_left(self):
        return self.get_due_date().days_left()

    def get_days_late(self):
        due_date = self.get_due_date()
        if due_date == Date.no_date():
            return None
        closed_date = self.get_closed_date()
        return (closed_date - due_date).days

    def get_text(self):
        """ Return the content or empty string in case of None """
        if self.content:
            return str(self.content)
        else:
            return ""

    def get_excerpt(self, lines=0, char=0, strip_tags=False,
                    strip_subtasks=True):
        """
        get_excerpt return the beginning of the content of the task.
        If "lines" is provided and different than 0, it return the number X
        of line (or the whole content if it contains less lines)
        If "char" is provided, it returns the X first chars of content (or the
        whole contents if it contains less char)
        If both char and lines are provided, the shorter one is returned.
        If none of them are provided (or if they are 0), this function is
        equivalent to get_text with with all XML stripped down.
        Warning: all markup informations are stripped down. Empty lines are
        also removed
        """
        # defensive programmation to avoid returning None
        if self.content:
            txt = self.content
            if strip_tags:
                for tag in self.get_tags_name():
                    txt = self._strip_tag(txt, tag)
            element = xml.dom.minidom.parseString(txt)
            txt = self.__strip_content(element, strip_subtasks=strip_subtasks)
            txt = txt.strip()
            # We keep the desired number of lines
            if lines > 0:
                liste = txt.splitlines()
                for i in liste:
                    if i.strip() == "":
                        liste.remove(i)
                to_keep = liste[:lines]
                txt = '\n'.join(to_keep)
            # We keep the desired number of char
            if char > 0:
                txt = txt[:char]
            return txt
        else:
            return ""

    def __strip_content(self, element, strip_subtasks=False):
        txt = ""
        if element:
            for n in element.childNodes:
                if n.nodeType == n.ELEMENT_NODE:
                    if strip_subtasks and n.tagName == 'subtask':
                        if txt[-2:] == '→ ':
                            txt = txt[:-2]
                    else:
                        txt += self.__strip_content(n, strip_subtasks)
                elif n.nodeType == n.TEXT_NODE:
                    txt += n.nodeValue
        return txt

    def set_text(self, texte):
        self.can_be_deleted = False
        if texte != "<content/>":
            # defensive programmation to filter bad formatted tasks
            if not texte.startswith("<content>"):
                texte = cgi.escape(texte, quote=True)
                texte = "<content>%s" % texte
            if not texte.endswith("</content>"):
                texte = "%s</content>" % texte
            self.content = str(texte)
        else:
            self.content = ''

    ### SUBTASKS #############################################################
    #
    def new_subtask(self):
        """Add a newly created subtask to this task. Return the task added as
        a subtask
        """
        subt = self.req.new_task(newtask=True)
        # we use the inherited childrens
        self.add_child(subt.get_id())
        return subt

    def add_child(self, tid):
        """Add a subtask to this task

        @param child: the added task
        """
        Log.debug("adding child %s to task %s" % (tid, self.get_id()))
        self.can_be_deleted = False
        # the core of the method is in the TreeNode object
        TreeNode.add_child(self, tid)
        # now we set inherited attributes only if it's a new task
        child = self.req.get_task(tid)
        if self.is_loaded() and child and child.can_be_deleted:
            child.set_start_date(self.get_start_date())
            child.set_due_date(self.get_due_date())
            for t in self.get_tags():
                child.add_tag(t.get_name())
        self.sync()
        return True

    def remove_child(self, tid):
        """Removed a subtask from the task.

        @param tid: the ID of the task to remove
        """
        c = self.req.get_task(tid)
        c.remove_parent(self.get_id())
        if c.can_be_deleted:
            self.req.delete_task(tid)
            self.sync()
            return True
        else:
            return False

    # FIXME: remove this function and use liblarch instead.
    def get_subtasks(self):
        tree = self.get_tree()
        return [tree.get_node(node_id) for node_id in self.get_children()]

    # FIXME : why is this function used ? It's higly specific. Remove it?
    #        (Lionel)
    # Agreed. it's only used by the "add tag to all subtasks" widget.
    def get_self_and_all_subtasks(self, active_only=False, tasks=[]):
        print "DEPRECATED FUNCTION: get_self_and_all_subtasks"
        tasks.append(self)
        for tid in self.get_children():
            i = self.req.get_task(tid)
            if i:
                if not active_only or i.status == self.STA_ACTIVE:
                    i.get_self_and_all_subtasks(active_only, tasks)
        return tasks

    def get_subtask(self, tid):
        # FIXME : remove this function. This is not useful
        print "DEPRECATED: get_subtask"
        """Return the task corresponding to a given ID.

        @param tid: the ID of the task to return.
        """
        return self.req.get_task(tid)

    def set_parent(self, parent_id):
        """Update the task's parent. Refresh due date constraints."""
        TreeNode.set_parent(self, parent_id)
        if parent_id is not None:
            par = self.req.get_task(parent_id)
            par_duedate = par.get_due_date_constraint()
            if not par_duedate.is_fuzzy() and \
                not self.due_date.is_fuzzy() and \
                    par_duedate < self.due_date:
                self.set_due_date(par_duedate)
        self.recursive_sync()

    def set_attribute(self, att_name, att_value, namespace=""):
        """Set an arbitrary attribute.

        @param att_name: The name of the attribute.
        @param att_value: The value of the attribute. Will be converted to a
            string.
        """
        val = unicode(str(att_value), "UTF-8")
        self.attributes[(namespace, att_name)] = val
        self.sync()

    def get_attribute(self, att_name, namespace=""):
        """Get the attribute C{att_name}.

        Returns C{None} if there is no attribute matching C{att_name}.
        """
        return self.attributes.get((namespace, att_name), None)

    def sync(self):
        self._modified_update()
        if self.is_loaded():
            # This is a liblarch call to the TreeNode ancestor
            self.modified()
            return True
        else:
            return False

    def _modified_update(self):
        '''
        Updates the modified timestamp
        '''
        self.last_modified = datetime.now()

### TAG FUNCTIONS ############################################################
#
    def get_tags_name(self):
        # Return a copy of the list of tags. Not the original object.
        return list(self.tags)

    # return a copy of the list of tag objects
    def get_tags(self):
        l = []
        for tname in self.tags:
            tag = self.req.get_tag(tname)
            if not tag:
                tag = self.req.new_tag(tname)
            l.append(tag)
        return l

    def rename_tag(self, old, new):
        eold = saxutils.escape(saxutils.unescape(old))
        enew = saxutils.escape(saxutils.unescape(new))
        self.content = self.content.replace(eold, enew)
        oldt = self.req.get_tag(old)
        self.remove_tag(old)
        oldt.modified()
        self.tag_added(new)
        self.req.get_tag(new).modified()
        self.sync()

    def tag_added(self, tagname):
        """
        Adds a tag. Does not add '@tag' to the contents. See add_tag
        """
        t = tagname.encode("UTF-8")
        # Do not add the same tag twice
        if not t in self.tags:
            self.tags.append(t)
            if self.is_loaded():
                for child in self.get_subtasks():
                    if child.can_be_deleted:
                        child.add_tag(t)

                tag = self.req.get_tag(t)
                if not tag:
                    tag = self.req.new_tag(t)
                tag.modified()
            return True

    def add_tag(self, tagname):
        "Add a tag to the task and insert '@tag' into the task's content"
        if self.tag_added(tagname):
            c = self.content

            # strip <content>...</content> tags
            if c.startswith('<content>'):
                c = c[len('<content>'):]
            if c.endswith('</content>'):
                c = c[:-len('</content>')]

            if not c:
                # don't need a separator if it's the only text
                sep = ''
            elif c.startswith('<tag>'):
                # if content starts with a tag, make a comma-separated list
                sep = ', '
            else:
                # other text at the beginning, so put the tag on its own line
                sep = '\n\n'

            self.content = "<content><tag>%s</tag>%s%s</content>" % (
                tagname, sep, c)
            # we modify the task internal state, thus we have to call for a
            # sync
            self.sync()

    # remove by tagname
    def remove_tag(self, tagname):
        modified = False
        if tagname in self.tags:
            self.tags.remove(tagname)
            modified = True
            for child in self.get_subtasks():
                if child.can_be_deleted:
                    child.remove_tag(tagname)
        self.content = self._strip_tag(self.content, tagname)
        if modified:
            tag = self.req.get_tag(tagname)
            # The ViewCount of the tag still doesn't know that
            # the task was removed. We need to update manually
            tag.update_task(self.get_id())
            if tag:
                tag.modified()

    def set_only_these_tags(self, tags_list):
        '''
        Given a list of strings representing tags, it makes sure that
        this task has those and only those tags.
        '''
        for tag in self.get_tags_name():
            try:
                tags_list.remove(tag)
            except:
                self.remove_tag(tag)
        for tag in tags_list:
            self.add_tag(tag)

    def _strip_tag(self, text, tagname, newtag=''):
        return (text
                .replace('<tag>%s</tag>\n\n' % (tagname), newtag)  # trail \n
                # trail comma
                .replace('<tag>%s</tag>, ' % (tagname), newtag)
                .replace('<tag>%s</tag>,' % (tagname), newtag)
                .replace('<tag>%s</tag>' % (tagname), newtag)
                # in case XML is missing (bug #504899)
                .replace('%s\n\n' % (tagname), newtag)
                .replace('%s, ' % (tagname), newtag)
                .replace('%s,' % (tagname), newtag)
                # don't forget a space a the end
                .replace('%s ' % (tagname), newtag))

    # tag_list is a list of tags names
    # return true if at least one of the list is in the task
    def has_tags(self, tag_list=None, notag_only=False):
        # recursive function to explore the tags and its children
        def children_tag(tagname):
            toreturn = False
            if tagname in self.tags:
                toreturn = True
            else:
                tag = self.req.get_tag(tagname)
                for tagc_name in tag.get_children():
                    if not toreturn:
                        toreturn = children_tag(tagc_name)
            return toreturn

        # We want to see if the task has no tags
        toreturn = False
        if notag_only:
            toreturn = self.tags == []
        # Here, the user ask for the "empty" tag
        # And virtually every task has it.
        elif tag_list == [] or tag_list is None:
            toreturn = True
        elif tag_list:
            for tagname in tag_list:
                if not toreturn:
                    toreturn = children_tag(tagname)
        else:
            # Well, if we don't filter on tags or notag, it's true, of course
            toreturn = True
        return toreturn

    def __str__(self):
        s = ""
        s = s + "Task Object\n"
        s = s + "Title:  " + self.title + "\n"
        s = s + "Id:     " + self.tid + "\n"
        s = s + "Status: " + self.status + "\n"
        s = s + "Tags:   " + str(self.tags)
        return s
