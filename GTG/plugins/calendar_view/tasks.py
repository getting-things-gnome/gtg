#from datetime import datetime
import cgi
import re
import uuid
import xml.dom.minidom

from dates import Date

class Task(object): #TreeNode):
    STA_ACTIVE = "Active"
    STA_DISMISSED = "Dismiss"
    STA_DONE = "Done"

    def __init__(self, ze_id, newtask=False): #, requester, newtask=False):
        #TreeNode.__init__(self, ze_id)
        assert(isinstance(ze_id, str) or isinstance(ze_id, str))
        self.tid = str(ze_id)
        #self.set_uuid(uuid.uuid4())
        self.content = ""
        self.title = ("My new task")
        self.status = self.STA_ACTIVE
        self.closed_date = Date.no_date()
        self.due_date = Date.no_date()
        self.start_date = Date.no_date()
        #self.can_be_deleted = newtask
        self.tags = []
        #self.req = requester
        #self.attributes = {}
        #self._modified_update()
        self.color = None

    def get_id(self):
        return str(self.tid)

    #def set_uuid(self, value):
    #    self.uuid = str(value)

    #def get_uuid(self):
    #    if self.uuid == "":
    #        self.set_uuid(uuid.uuid4())
    #    return str(self.uuid)

    def get_title(self):
        return self.title

    def set_title(self, title):
        if title:
            self.title = title.strip('\t\n')
        else:
            self.title = "(no title task)"

    def set_status(self, status, donedate=None):
        if status in [self.STA_ACTIVE, self.STA_DISMISSED, self.STA_DONE]:
            self.status = status
        if status in [self.STA_DISMISSED, self.STA_DONE]:
            if donedate:
                self.set_closed_date(donedate)
            else:
                self.set_closed_date(Date.today())

    def get_status(self):
        return self.status

    def set_due_date(self, new_duedate):
        new_duedate_obj = Date(new_duedate)  # caching the conversion
        self.due_date = new_duedate_obj
        
    def get_due_date(self):
        return self.due_date

    def set_start_date(self, fulldate):
        self.start_date = Date(fulldate)
        #if Date(fulldate) > self.due_date:
            #self.set_due_date(fulldate)

    def get_start_date(self):
        return self.start_date

    def set_closed_date(self, fulldate):
        self.closed_date = Date(fulldate)

    def get_closed_date(self):
        return self.closed_date

    def get_text(self):
        if self.content:
            return str(self.content)
        else:
            return ""

    def get_excerpt(self, lines=0, char=0, strip_tags=False,
                    strip_subtasks=True):
        """
        simplified get_excerpt return the beginning of the content of the task.
        """
        if self.content:
            txt = self.content
            element = xml.dom.minidom.parseString(txt)
            txt = txt.strip()
            if char > 0:
                txt = txt[:char]
            return txt
        else:
            return ""

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

    def get_tags_name(self):
        # Return a copy of the list of tags. Not the original object.
        return list(self.tags)

    def set_color(self, color=(0.5,0.5,0.5)):
        self.color = color

    def get_color(self):
        return self.color

    def __str__(self):
        s = ""
        s = s + "Task Object\n"
        s = s + "Title:  " + self.title + "\n"
        s = s + "Id:     " + self.tid + "\n"
        s = s + "Status: " + self.status + "\n"
        s = s + "Tags:   " + str(self.tags)
        return s
