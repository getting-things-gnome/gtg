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

"""
task.py contains the Task class which represents (guess what) a task
"""

import xml.dom.minidom
import uuid
import cgi
import xml.sax.saxutils as saxutils

from GTG              import _
from GTG.tools.dates  import date_today, no_date, Date
from datetime         import datetime
from GTG.core.tree    import TreeNode
from GTG.tools.logger import Log


class Task(TreeNode):
    """ This class represent a task in GTG.
    You should never create a Task directly. Use the datastore.new_task()
    function."""

    STA_ACTIVE    = "Active"
    STA_DISMISSED = "Dismiss"
    STA_DONE      = "Done"

    def __init__(self, ze_id, requester, newtask=False):
        TreeNode.__init__(self, ze_id)
        #the id of this task in the project should be set
        #tid is a string ! (we have to choose a type and stick to it)
        self.tid = str(ze_id)
        self.set_uuid(uuid.uuid4())
        self.remote_ids = {}
        self.content = ""
        #self.content = \
        #    "<content>Press Escape or close this task to save it</content>"
        self.title = _("My new task")
        #available status are: Active - Done - Dismiss - Note
        self.status = self.STA_ACTIVE
        self.closed_date = no_date
        self.due_date = no_date
        self.start_date = no_date
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
                #self.req._task_modified(self.tid)

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
        #Avoid unnecessary sync
        if self.title != old_title:
            self.sync()
            return True
        else:
            return False

    def set_status(self, status, donedate=None):
        old_status = self.status
        self.can_be_deleted = False
        if status:
            #we first modify the status of the children
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
                    self.closed_date = date_today()
            #If we mark a task as Active and that some parent are not
            #Active, we break the parent/child relation
            #It has no sense to have an active subtask of a done parent.
            # (old_status check is necessary to avoid false positive a start)
            elif status in [self.STA_ACTIVE] and\
                 old_status in [self.STA_DONE, self.STA_DISMISSED]:
                if self.has_parents():
                    for p_tid in self.get_parents():
                        par = self.req.get_task(p_tid)
                        if par.is_loaded() and par.get_status() in\
                           [self.STA_DONE, self.STA_DISMISSED]:
                            #we can either break the parent/child relationship
                            #self.remove_parent(p_tid)
                            #or restore the parent too
                            par.set_status(self.STA_ACTIVE)
                #We dont mark the children as Active because
                #They might be already completed after all
            #then the task itself
            self.status = status
        self.sync()

    def get_status(self):
        return self.status

    def get_modified(self):
        return self.modified

    def get_modified_string(self):
        return self.modified.strftime("%Y-%m-%dT%H:%M:%S")

    def set_modified(self, modified):
        self.modified = modified

    def set_due_date(self, fulldate):
        assert(isinstance(fulldate, Date))
        self.due_date = fulldate
        self.sync()

    #Due date return the most urgent date of all parents
    def get_due_date(self):
        zedate = self.due_date

        for par in self.get_parents():
            #Here we compare with the parent's due date
            pardate = self.req.get_task(par).get_due_date()
            if pardate and zedate > pardate:
                zedate = pardate
        
        return zedate

    def set_start_date(self, fulldate):
        assert(isinstance(fulldate, Date))
        self.start_date = fulldate
        self.sync()

    def get_start_date(self):
        return self.start_date

    def set_closed_date(self, fulldate):
        assert(isinstance(fulldate, Date))
        self.closed_date = fulldate
        self.sync()
        
    def get_closed_date(self):
        return self.closed_date

    def get_days_left(self):
        due_date = self.get_due_date()
        if due_date == no_date:
            return None
        return due_date.days_left()
    
    def get_days_late(self):
        due_date = self.get_due_date()
        if due_date == no_date:
            return None
        closed_date = self.get_closed_date()
        return (closed_date - due_date).days

    def get_text(self):
        #defensive programmtion to avoid returning None
        if self.content:
            return str(self.content)
        else:
            return ""

    def get_excerpt(self, lines=0, char=0, strip_tags=False, strip_subtasks=True):
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
            txt = self.content
            if strip_tags:
                for tag in self.get_tags_name():
                    txt = self._strip_tag(txt, tag)
            element = xml.dom.minidom.parseString(txt)
            txt = self.__strip_content(element, strip_subtasks=strip_subtasks)
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

    def __strip_content(self, element, strip_subtasks=False):
        txt = ""
        if element:
            for n in element.childNodes:
                if n.nodeType == n.ELEMENT_NODE:
                    if strip_subtasks and n.tagName=='subtask':
                        if txt[-2:]=='→ ':
                            txt = txt[:-2]
                    else:
                        txt += self.__strip_content(n, strip_subtasks)
                elif n.nodeType == n.TEXT_NODE:
                    txt += n.nodeValue
        return txt

    def set_text(self, texte):
        self.can_be_deleted = False
        if texte != "<content/>":
            #defensive programmation to filter bad formatted tasks
            if not texte.startswith("<content>"):
                texte = cgi.escape(texte, quote = True)
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
        subt     = self.req.new_task(newtask=True)
        #we use the inherited childrens
        self.add_child(subt.get_id())
        return subt
        
    def add_child(self, tid):
        """Add a subtask to this task

        @param child: the added task
        """
        Log.debug("adding child %s to task %s" %(tid, self.get_id()))
        self.can_be_deleted = False
        #the core of the method is in the TreeNode object
        if TreeNode.add_child(self,tid):
            #now we set inherited attributes only if it's a new task
            child = self.req.get_task(tid)
            if child.can_be_deleted:
                child.set_start_date(self.get_start_date())
                for t in self.get_tags():
                    child.tag_added(t.get_name())
            self.sync()
            #This one should be handled by the self.call_modified()
#            child.sync()
            return True
        else:
            Log.debug("child addition failed (or still pending)")
            return False
            
    def remove_child(self,tid):
        """Removed a subtask from the task.

        @param tid: the ID of the task to remove
        """
        if TreeNode.remove_child(self,tid):
            task = self.req.get_task(tid)
            if task.can_be_deleted:
                #child is a new, unmodified task
                # It should be deleted
                self.req.delete_task(tid)
            self.sync()
            return True
        else:
            return False


    #FIXME : remove this method
    def get_subtasks(self):
#        print "Deprecation Warning : use get_children instead of get_subtasks"
        #XXX: is this useful?
        zelist = []
        for i in self.get_children():
            t = self.req.get_task(i)
            if t:
                zelist.append(t)
        return zelist
        
    def get_self_and_all_subtasks(self, active_only=False, tasks=[]):
        tasks.append(self)
        for tid in self.get_children():
            i = self.req.get_task(tid)
            if i:
                if not active_only or i.status == self.STA_ACTIVE:
                    i.get_self_and_all_subtasks(active_only, tasks)
        return tasks

    def get_subtask(self, tid):
        """Return the task corresponding to a given ID.

        @param tid: the ID of the task to return.
        """
        return self.req.get_task(tid)

    ### PARENTS ##############################################################

    #Take a tid object as parameter
    def add_parent(self, parent_tid):
        Log.debug("adding parent %s to task %s" %(parent_tid, self.get_id()))
        added = TreeNode.add_parent(self, parent_tid)
        if added:
            self.sync()
            #the parent is handled by the sync
#            self.req.get_task(parent_tid).sync()
            return True
        else:
            return False

    #Take a tid as parameter
    def remove_parent(self, tid):
        TreeNode.remove_parent(self,tid)
        self.sync()
        parent = self.req.get_task(tid)
        if parent:
            parent.sync()

    #Return true is the task has parent
    #If tag is provided, return True only
    #if the parent has this particular tag
    def has_parents(self, tag=None):
        has_par = TreeNode.has_parent(self)
        #The "all tag" argument
        if tag and has_par:
            a = 0
            for tid in self.get_parents():
                p = self.req.get_task(tid)
                a += p.has_tags(tag)
            to_return = a
        else:
            to_return = has_par
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
        #we issue a delete for all the children
        for task in self.get_subtasks():
            #I think it's superfluous (invernizzi)
            #task.remove_parent(self.get_id())
            task.delete()
        #we tell the parents we have to go
        for i in self.get_parents():
            task = self.req.get_task(i)
            task.remove_child(self.get_id())
        #we tell the tags about the deletion
        for tagname in self.tags:
            tag = self.req.get_tag(tagname)
            tag.remove_task(self.get_id())
        #then we signal the we are ready to be removed
        self.req._task_deleted(self.get_id())

    def sync(self):
        self._modified_update()
        if self.is_loaded():
            self.call_modified()
            return True
        else:
            return False
    
    #This function send the modified signals for the tasks, 
    #parents and children
    def call_modified(self):
        #we first modify children
        for s in self.get_children():
            self.req._task_modified(s)
        #then the task
        self.req._task_modified(self.tid)
        #then parents
        for p in self.get_parents():
            self.req._task_modified(p)

    def _modified_update(self):
        '''
        Updates the modified timestamp
        '''
        self.modified = datetime.now()

### TAG FUNCTIONS ############################################################
#
    def get_tags_name(self):
        #Return a copy of the list of tags. Not the original object.
        return list(self.tags)

    #return a copy of the list of tag objects
    def get_tags(self):
        l = []
        for tname in self.tags:
            l.append(self.req.get_tag(tname))
        return l
        
    def rename_tag(self, old, new):
        eold = saxutils.escape(saxutils.unescape(old))
        enew = saxutils.escape(saxutils.unescape(new))
        self.content = self.content.replace(eold, enew)
        self.remove_tag(old)
        self.req._tag_modified(old)
        self.tag_added(new)
        self.req._tag_modified(new)
        self.sync()

    def tag_added(self, tagname):
        """
        Adds a tag. Does not add '@tag' to the contents. See add_tag
        """
        #print "tag %s added to task %s" %(tagname,self.get_id())
        t = tagname.encode("UTF-8")
        tag = self.req.get_tag(t)
        if not tag:
            tag = self.req.new_tag(t)
        tag.add_task(self.get_id())
        #Do not add the same tag twice
        if not t in self.tags:
            self.tags.append(t)
            #we notify the backends
            #self.req.tag_was_added_to_task(self, tagname)
            for child in self.get_subtasks():
                if child.can_be_deleted:
                    child.add_tag(t)
            self.req._tag_modified(t)
            return True
    
    def add_tag(self, tagname):
        "Add a tag to the task and insert '@tag' into the task's content"
        if self.tag_added(tagname):
            c = self.content
            
            #strip <content>...</content> tags
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

    #remove by tagname
    def remove_tag(self, tagname):
        t = self.req.get_tag(tagname)
        modified = False
        if t:
            t.remove_task(self.get_id())
            modified = True
        if tagname in self.tags:
            self.tags.remove(tagname)
            modified = True
            for child in self.get_subtasks():
                if child.can_be_deleted:
                    child.remove_tag(tagname)
        self.content = self._strip_tag(self.content, tagname)
        if modified:
            self.req._tag_modified(tagname)
                       
    def _strip_tag(self, text, tagname,newtag=''):
        return (text
                    .replace('<tag>%s</tag>\n\n'%(tagname), newtag) #trail \n
                    .replace('<tag>%s</tag>, '%(tagname), newtag) #trail comma
                    .replace('<tag>%s</tag>'%(tagname), newtag)
                    #in case XML is missing (bug #504899)
                    .replace('%s\n\n'%(tagname), newtag) 
                    .replace('%s, '%(tagname), newtag) 
                    #don't forget a space a the end
                    .replace('%s '%(tagname), newtag)
               )
     

    #tag_list is a list of tags names
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
