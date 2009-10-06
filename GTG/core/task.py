# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

from datetime import date
import xml.dom.minidom
import uuid

from GTG import _
from GTG.tools.dates import strtodate
from datetime import datetime


class Task:
    """ This class represent a task in GTG.
    You should never create a Task directly. Use the datastore.new_task()
    function."""

    STA_ACTIVE    = "Active"
    STA_DISMISSED = "Dismiss"
    STA_DONE      = "Done"

    def __init__(self, ze_id, requester, newtask=False):
        #the id of this task in the project should be set
        #tid is a string ! (we have to choose a type and stick to it)
        self.tid = str(ze_id)
        self.set_uuid(uuid.uuid4())
        self.content = ""
        #self.content = \
        #    "<content>Press Escape or close this task to save it</content>"
        self.sync_func = None
        self.title = _("My new task")
        #available status are: Active - Done - Dismiss - Note
        self.status = self.STA_ACTIVE
        self.closed_date = None
        self.due_date = None
        self.start_date = None
        self.parents = []
        #The list of children tid
        self.children = []
        self.can_be_deleted = newtask
        # tags
        self.tags = []
        self.req = requester
        #If we don't have a newtask, we will have to load it.
        self.loaded = newtask
        if self.loaded:
            self.req._task_loaded(self.tid)
        self.attributes={}
        self._modified_update()

    def is_loaded(self):
        return self.loaded

    def set_loaded(self,signal=True):
        #avoid doing it multiple times
        if not self.loaded:
            self.loaded = True
            if signal:
                self.req._task_loaded(self.tid)
                self.call_modified()

    def set_to_keep(self):
        self.can_be_deleted = False

    def is_new(self):
        return self.can_be_deleted

    def get_id(self):
        return str(self.tid)

    def set_uuid(self, value):
        self.uuid = str(value)

    def get_uuid(self):
        #NOTE: Transitional if switch, needed to add
        #      the uuid field to tasks created before
        #      adding this field to the task description.
        if self.uuid == "":
            self.set_uuid(uuid.uuid4())
            self.sync()
        return self.uuid

    def get_title(self):
        return self.title

    #Return True if the title was changed.
    #False if the title was already the same.
    def set_title(self, title):
        #We should check for other task with the same title
        #In that case, we should add a number (like Tomboy does)
        old_title = self.title
        if title:
            self.title = title.strip('\t\n')
        else:
            self.title = "(no title task)"
        #Avoid unecessary sync
        if self.title != old_title:
            self.sync()
            return True
        else:
            return False

    def set_status(self, status, donedate=None):
        old_status = self.status
        self.can_be_deleted = False
        if status:
            self.status = status
            #If Done, we set the done date
            if status in [self.STA_DONE, self.STA_DISMISSED]:
                for c in self.get_subtasks():
                    if c.get_status() in [self.STA_ACTIVE]:
                        c.set_status(status, donedate=donedate)
                #to the specified date (if any)
                if donedate:
                    self.closed_date = donedate
                #or to today
                else:
                    self.closed_date = date.today()
            #If we mark a task as Active and that some parent are not
            #Active, we break the parent/child relation
            #It has no sense to have an active subtask of a done parent.
            # (old_status check is necessary to avoid false positive a start)
            elif status in [self.STA_ACTIVE] and\
                 old_status in [self.STA_DONE, self.STA_DISMISSED]:
                if self.has_parents():
                    for p_tid in self.get_parents():
                        par = self.req.get_task(p_tid)
                        if par.is_loaded() and par.get_status in\
                           [self.STA_DONE, self.STA_DISMISSED]:
                            self.remove_parent(p_tid)
                #We dont mark the children as Active because
                #They might be already completed after all

        self.sync()

    def get_status(self):
        return self.status

    #A task is workable if all children are done/deleted/dismiss
    def is_workable(self):
        workable = True
        for c in self.get_subtasks():
            if c.get_status() == self.STA_ACTIVE:
                workable = False
        return workable

    def get_modified(self):
        return self.modified

    def set_modified(self, string):
        self.modified = string

    def set_due_date(self, fulldate, fromparent=False):
        # if fromparent, we set only a date if duedate is not set
        #Or if duedate is after the newly set date !
        if fromparent:
            parent_date = fulldate
            fulldate = self.due_date.__str__()
        else:
            parent_date = None
        #We retrieve the most urgent due date from parent
        for par in self.get_parents():
            pardate_str = self.req.get_task(par).get_due_date()
            if pardate_str:
                pardate = strtodate(pardate_str)
                if not strtodate(parent_date) or\
                   pardate < strtodate(parent_date):
                    parent_date = pardate_str
        #We compare it to the date we want to set
        if parent_date and strtodate(parent_date):
            if not fulldate or not strtodate(fulldate) or\
               strtodate(parent_date) < strtodate(fulldate):
                fulldate = parent_date
        #Now we set the duedate
        if fulldate:
            #print "fulldate %s" %fulldate
            self.due_date = strtodate(fulldate)
            #We set the due date for children only
            #if their due date is "larger" (or none)
            for child in self.get_subtasks():
                actual_date = child.get_due_date()
                if actual_date:
                    rfulldate = strtodate(fulldate)
                    ractual = strtodate(actual_date)
                    if rfulldate and rfulldate < ractual:
                        child.set_due_date(fulldate, fromparent=True)
                else:
                    child.set_due_date(fulldate, fromparent=True)
        else:
            self.due_date = None
        self.sync()

    #Due date return the most urgent date of all parents
    def get_due_date(self):
        if self.due_date:
            zedate = self.due_date
        else:
            zedate = date.max
        for par in self.get_parents():
            #Here we compare with the parent's due date
            pardate_str = self.req.get_task(par).get_due_date()
            if pardate_str:
                pardate = strtodate(pardate_str)
                if pardate and zedate > pardate:
                    zedate = pardate
        if zedate == date.max:
            return ''
        else:
            return str(zedate)

    def set_start_date(self, fulldate):
        if fulldate:
            self.start_date = strtodate(fulldate)
        else:
            self.start_date = None

    def get_start_date(self):
        if self.start_date:
            return str(self.start_date)
        else:
            return ''

    def is_started(self):
        if self.start_date:
            difference = date.today() - self.start_date
            return difference.days >= 0
        else:
            return True

    def get_closed_date(self):
        if self.closed_date:
            return str(self.closed_date)
        else:
            return ''

    def get_days_left(self):
        due_date = self.get_due_date()
        if due_date:
            difference = strtodate(due_date) - date.today()
            return difference.days
        else:
            return None

    def get_text(self):
        #defensive programmtion to avoid returning None
        if self.content:
            return str(self.content)
        else:
            return ""

    def get_excerpt(self, lines=0, char=0):
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
        #defensive programmtion to avoid returning None
        if self.content:
            element = xml.dom.minidom.parseString(self.content)
            txt = self.__strip_content(element)
            txt = txt.strip()
            #We keep the desired number of lines
            if lines > 0:
                liste = txt.splitlines()
                for i in liste:
                    if i.strip() == "":
                        liste.remove(i)
                to_keep = liste[:lines]
                txt = '\n'.join(to_keep)
            #We keep the desired number of char
            if char > 0:
                txt = txt[:char]
            return txt
        else:
            return ""

    def __strip_content(self, element):
        txt = ""
        if element:
            for n in element.childNodes:
                if n.nodeType == n.ELEMENT_NODE:
                    txt += self.__strip_content(n)
                elif n.nodeType == n.TEXT_NODE:
                    txt += n.nodeValue
        return txt

    def set_text(self, texte):
        self.can_be_deleted = False
        if texte != "<content/>":
            #defensive programmation to filter bad formatted tasks
            if not texte.startswith("<content>"):
                texte = "<content>%s" %texte
            if not texte.endswith("</content>"):
                texte = "%s</content>" %texte
            self.content = str(texte)
        else:
            self.content = ''

    ### SUBTASKS #############################################################
    #
    def new_subtask(self):
        """Add a newly created subtask to this task. Return the task added as
        a subtask
        """
        uid, pid = self.get_id().split('@') #pylint: disable-msg=W0612
        subt     = self.req.new_task(pid=pid, newtask=True)
        self.add_subtask(subt.get_id())
        return subt

    def add_subtask(self, tid):
        """Add a subtask to this task

        @param tid: the ID of the added task
        """
        self.can_be_deleted = False
        #The if prevent an infinite loop
        if tid not in self.children and tid not in self.parents:
            self.children.append(tid)
            task = self.req.get_task(tid)
            task.add_parent(self.get_id())
            #now we set inherited attributes only if it's a new task
            #Except for due date because a child always has to be due
            #before its parent
            task.set_due_date(self.get_due_date(), fromparent=True)
            if task.can_be_deleted:
                task.set_start_date(self.get_start_date())
                for t in self.get_tags():
                    task.add_tag(t.get_name())

    def remove_subtask(self, tid):
        """Removed a subtask from the task.

        @param tid: the ID of the task to remove
        """
        if tid in self.children:
            self.children.remove(tid)
            task = self.req.get_task(tid)
            if task.can_be_deleted:
                self.req.delete_task(tid)
            else:
                task.remove_parent(self.get_id())
            self.sync()

    def has_subtasks(self):
        """Returns True if task has subtasks.
        """
        return len(self.children) != 0

    def get_n_subtasks(self):
        """Return the number of subtasks of a task.
        """
        return len(self.children)

    def get_subtasks(self):
        """Return the list of subtasks.
        """
        #XXX: is this useful?
        zelist = []
        for i in self.children:
            zelist.append(self.req.get_task(i))
        return zelist

    def get_subtask(self, tid):
        """Return the task corresponding to a given ID.

        @param tid: the ID of the task to return.
        """
        return self.req.get_task(tid)

    def get_subtask_tids(self):
        """Return the list of subtasks. Return a list of IDs.
        """
        return list(self.children)

    def get_nth_subtask(self, index):
        """Return the task ID stored at a given index.

        @param index: the index of the task to return.
        """
        try:
            return self.children[index]
        except(IndexError):
            raise ValueError("Index is not in task list")

    def get_subtask_index(self, tid):
        """Return the index of a given subtask.

        @param tid: the tid of the task whose index must be returned.
        """
        return self.children.index(tid)

    #add and remove parents are private
    #Only the task itself can play with it's parent

    ### PARENTS ##############################################################

    #Take a tid object as parameter
    def add_parent(self, tid):
        #The if prevent a loop
        if tid and tid not in self.children and tid not in self.parents:
            self.parents.append(tid)
            self.sync()
            task = self.req.get_task(tid)
            task.add_subtask(self.get_id())
            task.sync()

    #Take a tid as parameter
    def remove_parent(self, tid):
        if tid and tid in self.parents:
            self.parents.remove(tid)
            self.sync()
            parent = self.req.get_task(tid)
            if parent:
                parent.remove_subtask(self.get_id())
                parent.sync()

    def get_parents(self):
        return list(self.parents)

    #Return true is the task has parent
    #If tag is provided, return True only
    #if the parent has this particular tag
    def has_parents(self, tag=None):
        #The "all tag" argument
        if tag and len(self.parents)!=0:
            a = 0
            for tid in self.parents:
                p = self.req.get_task(tid)
                a += p.has_tags(tag)
            to_return = a
        else:
            to_return = len(self.parents)!=0
        return to_return

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

    #Method called before the task is deleted
    #This method is called by the datastore and should not be called directly
    #Use the requester
    def delete(self):
        self.set_sync_func(None, callsync=False)
        for i in self.get_parents():
            task = self.req.get_task(i)
            task.remove_subtask(self.get_id())
        for task in self.get_subtasks():
            task.remove_parent(self.get_id())
        #then we remove effectively the task
        #self.req.delete_task(self.get_id())

    #This is a callback. The "sync" function has to be set
    def set_sync_func(self, sync, callsync=True):
        self.sync_func = sync
        #We call it immediatly to save stuffs that were set before this
        if callsync and self.is_loaded():
            self.sync()

    def sync(self):
        self._modified_update()
        if self.sync_func and self.is_loaded():
            self.sync_func(self)
            self.call_modified()
    
    #This function send the modified signals for the tasks, 
    #parents and childrens       
    def call_modified(self):
        self.req._task_modified(self.tid)
        #we also modify parents and children
        for p in self.get_parents() :
            self.req._task_modified(p)
        for s in self.get_subtask_tids() :
            self.req._task_modified(s)

    def _modified_update(self):
        self.modified = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")



### TAG FUNCTIONS ############################################################
#
    def get_tags_name(self):
        #Return a copy of the list of tags. Not the original object.
        l = []
        for t in self.tags:
            name = t.get_name().encode("UTF-8")
            l.append(name)
        return l

    #return a copy of the list of tag objects
    def get_tags(self):
        return list(self.tags)

    #This function add tag by name
    def add_tag(self, tagname):
        t = self.req.new_tag(tagname.encode("UTF-8"))
        #Do not add the same tag twice
        if not t in self.tags:
            self.tags.append(t)
            for child in self.get_subtasks():
                if child.can_be_deleted:
                    child.add_tag(tagname)

    #remove by tagname
    def remove_tag(self, tagname):
        t = self.req.get_tag(tagname)
        if t in self.tags:
            self.tags.remove(t)
            for child in self.get_subtasks():
                if child.can_be_deleted:
                    child.remove_tag(tagname)

    #tag_list is a list of tags object
    #return true if at least one of the list is in the task
    def has_tags(self, tag_list=None, notag_only=False):
        #We want to see if the task has no tags
        if notag_only:
            return self.tags == []
        #Here, the user ask for the "empty" tag
        #And virtually every task has it.
        elif tag_list == [] or tag_list == None:
            return True
        elif tag_list:
            for tag in tag_list:
                if tag in self.tags:
                    return True
        else:
            #Well, if we don't filter on tags or notag, it's true, of course
            return True
        return False

    #return the color of one tag that have a color defined
    #Yes, the choosen color is a bit random in case of multiple colored tags
    def get_color(self):
        color = None
        for t in self.get_tags():
            c = t.get_attribute("color")
            if c:
                color = c
        return color

    def __str__(self):
        s = ""
        s = s + "Task Object\n"
        s = s + "Title:  " + self.title + "\n"
        s = s + "Id:     " + self.tid + "\n"
        s = s + "Status: " + self.status + "\n"
        s = s + "Tags:   "  + str(self.tags)
        return s
