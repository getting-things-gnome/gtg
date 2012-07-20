# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

""" Create tasks for the first run

Tasks should serve as a quick tutorial how GTG works """

from GTG import _
from GTG.tools import cleanxml
from GTG.tools.tags import extract_tags_from_text


def populate():
    doc, root = cleanxml.emptydoc("project")

    #Task 0@1: Getting started with GTG
    title1 = _("Getting started with GTG")
    text1 = _(\
"Welcome to Getting Things GNOME!, your new task manager! In Getting "
"Things GNOME! (GTG), everything is a task. From building a bridge over "
"the Pacific Ocean to changing a light bulb or organizing a party!\n"
"\n"
"If you are new to GTG, please take the time to read this, as it will "
"provide you useful information about how to use GTG to organize your "
"everyday life.\n"
"\n"
"Creating and editing tasks:\n"
"\n"
"Using GTG is easy: you organize what you have to do by creating new "
"tasks. To do this, simply press the &quot;New Task&quot; button, "
"edit the task by describing it, set some parameters, and that's "
"it! Once a task done, you can close it by pressing the &quot;Mark As "
"Done&quot; button.\n"
"\n"
"In GTG, a task is automatically saved while you are editing it. No need to "
"press any &quot;Save&quot; button! Try it: add some text to this task, close "
"the window, and reopen it: your changes are still there!\n"
"\n"
"About subtasks:\n"
"\n"
"In life, you often get more things done by refining them in "
"smaller, more operational tasks. GTG helps to do just this by defining "
"&quot;subtasks&quot;. In GTG, those subtasks are considered as prerequisites "
"that must be completed before being able to close their parent task.\n"
"\n"
"Therefore, in GTG, a task might host one or several subtasks. Those "
"appear as links in the task description, just like the link below. To "
"open and edit a subtask, simply click on its link! Try it yourself: open "
"the following subtask:\n"
"<subtask>1@1</subtask>\n"
"\n"
"Closing a task:\n"
"\n"
"In GTG, once you are done with a task, you can close it by pushing "
"either the &quot;Mark as Done&quot; or the &quot;Dismiss&quot; button. "
"Use the first one if the task is done, and the latter if you want to "
"close it because it is not relevant anymore. Want to try it? Try to "
"close the subtask above for instance!\n"
"\n"
"When you close a task, you will notice that all its subtasks will be "
"automatically closed too! Indeed, GTG considers that if you have completed a "
"given task, then you don't need to do its subtasks anymore (they were "
"prerequisites, after all).\n"
"\n"
"Note that the tasks that you have marked as done or dismissed are listed in "
"the &quot;Closed Tasks Pane&quot; which is hidden by default, but you can "
"easily show it using the View menu.\n"
"\n"""
"Learn more about GTG:\n"
"\n"
"If you are interested in knowing more about "
"GTG's other features, you will find more information here:\n"
"<subtask>2@1</subtask>\n"
"<subtask>3@1</subtask>\n"
"<subtask>4@1</subtask>\n"
"<subtask>5@1</subtask>\n"
"<subtask>6@1</subtask>\n"
"\n"
"You can also browse GTG documentation by pressing F1 or opening it using "
"the Help menu.\n"
"\n"
"We sincerely hope you will enjoy using GTG, and thank you for trying it out! "
"Please send us bug reports and ideas for improvement using this web page: "
"https://bugs.launchpad.net/gtg If you want to get tips for using GTG or be "
"informed about the newest features, also visit our blog at "
"http://gtg.fritalk.com\n"
"\n"
"The GTG team.")
    t1 = addtask(doc, "0@1", title1, text1, \
        ["1@1", "2@1", "3@1", "4@1", "5@1", "6@1"])
    root.appendChild(t1)

    #Task 1@1: Learn to use subtasks
    title2 = _("Learn how to use subtasks")
    text2 = _("""A &quot;Subtask&quot; is something that you need to do first before being able to accomplish your task. In GTG, the purpose of subtasks is to cut down a task in smaller subtasks that are easier to achieve and to track down.
    
To insert a subtask in the task description (this window, for instance), begin a line with &quot;-&quot;, then write the subtask title and press Enter.

Try inserting one subtask below. Type &quot;- This is my first subtask!&quot;, for instance, and press Enter:


    
Alternatively, you can also use the &quot;insert subtask&quot; button.

Tasks and subtasks can be re-organized by drag-n-drop in the tasks list.

Note that subtasks obey to some rules: first, a subtask's due date can never be happen after its parent's due date and, second, when you mark a parent task as done, its subtasks will also be marked as done.""")
    t2 = addtask(doc, "1@1", title2, text2, [])
    root.appendChild(t2)

    #Task 2@1: Learn to use tags
    title3 = _("Learn how to use tags")
    text3 = _("""A tag is a simple word that begins with &quot;@&quot;.

Try to type a word beginning with @ here:

It becomes yellow, it's now a tag.

Tags are useful to sort your tasks. In the view menu, you can enable a sidebar which displays all the tags you are using so you can easily see tasks assigned to a given tag. There's no limit to the number of tags a task can have.

You can drag-n-drop a tag onto another to create \"subtags\". As an example, if you drag the tag @to_pay onto the tag @money, every task tagged with @to_pay will also appear in the view of @money (but the @money tag is not added to the task).

If you right click on a tag in the sidebar you can also set its color. It will allow you to have a more colorful list of tasks, if you want it that way.

A new tag is only added to the current task. There's no recursion and the tag is not applied to subtasks. But when you create a new subtask, this subtask will inherit the tags of its parent as a good primary default (it will also be the case if you add a tag to a parent just after creating a subtask). Of course, you can modify at any time the tags of this particular subtask. It will never be changed by the parent.""")
    t3 = addtask(doc, "2@1", title3, text3, [])
    root.appendChild(t3)

    #Task 3@1: Using the Workview
    title4 = _("Learn how to use the Work View")
    text4 = _("""If you press the &quot;Work View&quot; button, only actionable tasks will be displayed.

What is an actionable task? It's a task you can do directly, right now.

It's a task that is already &quot;start-able&quot;, i.e. the start date is already over.

It's a task that doesn't have open subtasks, i.e. you can do the task itself directly.

Thus, the workview will only show you tasks you can do right now.

If you use tags, you can right click on a tag in the sidebar and choose to hide tasks assigned to this particular tag in the workview. It's very useful if you have a tag like &quot;someday&quot; that you use for tasks you would like to do but are not particularly urgent.""")
    t4 = addtask(doc, "3@1", title4, text4, [])
    root.appendChild(t4)

    #Task 5@1: Plugins
    title5 = _("Learn how to use plugins")
    text5 = _("""GTG has the ability to add plugins to extend its core functionality.

Some examples of the current plugins are synchronization with online services like Remember the Milk and Evolution, Tomboy/Gnote integration and Geolocalized Tasks.

You can find the Plugin Manager by selecting Edit in the Menu Bar, then clicking Preferences. You will then see a tab labeled Plugins.""")

    t5 = addtask(doc, "4@1", title5, text5, [])
    root.appendChild(t5)

    #Task 5@1: Reporting bugs
    title6 = _("Reporting bugs")
    text6 = _("""GTG is still very alpha software. We like it and use it everyday but you will encounter some bugs.

Please, report them on our Launchpad page:
https://bugs.launchpad.net/gtg

We need you to make this software better. Any contribution, any idea is welcome.

If you have some trouble with GTG, we might be able to help you or to solve your problem really quickly.""")

    t6 = addtask(doc, "5@1", title6, text6, [])
    root.appendChild(t6)

    #Task 6@1: Learn how to use the QuickAdd Entry
    title7 = _("Learn how to use the Quick Add Entry")
    text7 = _("""The Quick Add Entry is the fastest way to create a new task. Use the check box in the View menu to enable and disable the entry field.

To add a task simply type its title in the entry and press Enter. The task will be created and selected in the task browser. If a tag is selected in the Tags Sidebar, it will be applied to the task you created.

You can also create a task in the Quick Add Entry and at the same time specify its tags, due and defer date. Follow these format rules:


tags:tag1,tag2,tag3
 - This way you can apply as many tags as you wish using comma as separator
 - Note: any word in the title that begins with &quot;@&quot; will also be interpreted as a tag

due:date
defer:date
 - This way you can apply a due date or a defer date. Dates can be formated as yyyy-mm-dd (for example 2012-04-01) or yyyymmdd (20120401) or mmdd (0401 - the year being implicitly the current one) or today, tomorrow or a weekday name (due:monday means due next Monday). Dates which are added in this way will not appear in the task title.

Examples:
buy stationary tags:purchases,office due:20120330 defer:tuesday

 - The above example tells GTG to create a new task with the title "buy stationary", under the tags "purchases" and "office", with the due date March 30, 2012 and the start date next Tuesday.

call mum tags:family,calls due:sunday defer:tomorrow
 - The above example tells GTG to create a new task with the title "call mum", under the tags "family" and "calls", with the due date next Sunday and the start date tomorrow.""")

    t7 = addtask(doc, "6@1", title7, text7, [])
    root.appendChild(t7)

    return doc


def addtask(doc, ze_id, title, text, childs):
    t_xml = doc.createElement("task")
    t_xml.setAttribute("id", ze_id)
    t_xml.setAttribute("status", "Active")

    tags = extract_tags_from_text(text)
    t_xml.setAttribute("tags", ",".join(tags))

    cleanxml.addTextNode(doc, t_xml, "title", title)
    for c in childs:
        cleanxml.addTextNode(doc, t_xml, "subtask", c)
    cleanxml.addTextNode(doc, t_xml, "content", text)
    return t_xml
