# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

from gettext import gettext as _
from GTG.core.tag import extract_tags_from_text
from GTG.core import xml
from GTG.core.dates import Date

from uuid import uuid4
from lxml import etree


# Tags for the initial tasks
tags = {
    'to_pay': str(uuid4()),
    'money': str(uuid4()),
    'errands': str(uuid4()),
    'waitingfor': str(uuid4()),
}


# TIDs for each initial task
task_ids = [str(uuid4()) for _ in range(9)]

# Date for modified and added tags
today = Date.today().xml_str()

# Initial tasks
# flake8: noqa: E501
tasks = [
    {
        'title': _("Getting Started with GTG (read me first)"),
        'id': task_ids[0],
        'subtasks': task_ids[1:],
        'added': today,
        'modified': today,
        'tags': [],
        'content': _(
            "Welcome to Getting Things GNOME (GTG), your new task manager! In GTG, "
            "everything is a task. From building a bridge over the Pacific Ocean "
            "to changing a light bulb or organizing a party!\n\n"
            "If you are new to GTG, please take the time to read this, as it will "
            "provide you useful information about how to use GTG to organize "
            "your everyday life.\n"
            "\n"
            "Creating and editing tasks:\n"
            "\n"
            "Using GTG is easy: you organize what you have to do by creating new "
            "tasks. To do this, simply press the &quot;New Task&quot; (+) button, "
            "edit the task by describing it, set some parameters, and that's it! "
            "Once a task is done, you can close it by pressing the &quot;Mark As "
            "Done&quot; button.\n"
            "\n"
            "In GTG, a task is automatically saved while you are editing it. No "
            "need to press any &quot;Save&quot; button! Try it: add some text to "
            "this task, close the window, and reopen it: your changes are still "
            "there!\n"
            "\n"
            "About subtasks:\n"
            "\n"
            "In life, you often get more things done by refining them in "
            "smaller, more operational tasks. GTG helps to do just this by "
            "defining  &quot;subtasks&quot;. In GTG, those subtasks are "
            "considered as prerequisites that must be completed before being able "
            "to close their parent task.\n"
            "\n"
            "Therefore, in GTG, a task might host one or several subtasks. Those "
            "appear as links in the task description, just like the link below. "
            "To open and edit a subtask, simply click on its link! "
            "You can always come back using the &quot;Open Parent&quot; button. "
            "Try opening the following subtask for example:\n"
            "{! " + task_ids[1] + " !}\n"
            "\n"
            "Closing a task:\n"
            "\n"
            "In GTG, once you are done with a task, you can close it by pushing "
            "either the &quot;Mark as Done&quot; or the &quot;Dismiss&quot; "
            "button. Use the first one if the task is done, and the latter if you "
            "want to close it because it is not relevant anymore.\n"
            "\n"
            "When you close a task, you will notice that all its subtasks will be "
            "automatically closed too. Indeed, GTG considers that if you have "
            "completed a given task, then you don't need to do its subtasks "
            "anymore (they were prerequisites, after all).\n"
            "\n"
            "Note that the tasks that you have marked as done or dismissed are "
            "listed in the &quot;Closed&quot; tasks view mode.\n"
            "\n"
            "Learn more about GTG:\n"
            "\n"
            "If you are interested in knowing more about "
            "GTG's other features, you will find more information here:\n"
            "{! " + task_ids[1] + " !}\n"
            "{! " + task_ids[2] + " !}\n"
            "{! " + task_ids[3] + " !}\n"
            "{! " + task_ids[4] + " !}\n"
            "{! " + task_ids[5] + " !}\n"
            "{! " + task_ids[6] + " !}\n"
            "{! " + task_ids[7] + " !}\n"
            "{! " + task_ids[8] + " !}\n"
            "\n"
            "We also recommend you read our user manual, by pressing F1 "
            "or using the &quot;Help&quot; entry in the main window's menu button.\n"
            "\n"
            "We hope you will enjoy using GTG, and thank you for trying it out! "
            "To learn more about the GTG project and how you can contribute, "
            "visit our web page: https://wiki.gnome.org/Apps/GTG/ \n"
            "\n"
            "— The GTG team")
    },
    {
        'title': _("Learn How to Use Subtasks"),
        'id': task_ids[1],
        'subtasks': [],
        'tags': [],
        'added': today,
        'modified': today,
        'content': _(
            "A &quot;Subtask&quot; is something that you need to do first before "
            "being able to accomplish your task. In GTG, the purpose of subtasks "
            "is to cut down a task (or project) in smaller, action-oriented subtasks "
            "that are easier to achieve and to track down.\n\n"
            "To insert a subtask in the task description (this window, for "
            "instance), begin a line with &quot;-&quot;, then write the subtask "
            "title and press Enter.\n"
            "\n"
            "Try inserting one subtask below. Type &quot;- This is my first "
            "subtask!&quot;, for instance, and press Enter:\n"
            "\n"
            "\n"
            "\n"
            "Alternatively, you can also use the subtask insertion button in "
            "the task editor toolbar.\n\n"
            "Note that subtasks obey some rules: first, a subtask's due date "
            "can never happen after its parent's due date and, second, when you "
            "mark a parent task as done, its subtasks will also be marked as "
            "done.\n\n"
            "And if you are not happy with your current tasks/subtasks organization, "
            "you can always change the relationships by drag-and-dropping tasks on "
            "(or between) each other in the tasks list.")
    },

    {
        'title': _("Learn How to Use Tags and Enable the Sidebar"),
        'id': task_ids[2],
        'subtasks': [],
        'tags': [tags['money'], tags['to_pay'],],
        'added': today,
        'modified': today,
        'content': _(
            "In GTG, you use tags to sort your tasks. A tag is a simple word that "
            "begins with &quot;@&quot;.\n"
            "\n"
            "Try to type a word beginning with &quot;@&quot; here:\n"
            "\n"
            "Once it becomes highlighted, it means it is recognized as a tag, "
            "and this tag is immediately linked to the task.\n"
            "\n"
            "In the main window, using the menu button or by pressing the F9 key, "
            "you can enable a sidebar which displays all the tags you are using. "
            " This allows you to easily see all tasks associated to a given tag.\n"
            "\n"
            "If you right-click on a tag in the sidebar, you can also edit it. It "
            "allows you to assign a color to it, or an icon. This lets you quickly "
            "identify the tasks associated to a given tag in the task list!\n\n"
            "New tags are always added exclusively to the currently edited task, "
            "and never to its subtasks. However, when you create a new subtask, "
            "it will inherit its parent's tags.\n"
            "\n"
            "If you need a more advanced task organization, you can also create a"
            " hierarchy of tags by drag-and-dropping a tag onto another. This "
            "is useful when you want to regroup several tags together and see all"
            " related tasks easily. For instance, if you have two tags @money and"
            " @to_pay, and you drag @to_pay on @money, every task tagged with "
            "@to_pay will also appear when you select @money.")
    },

    {
        'title': _("Learn How to Use the Actionable View Mode"),
        'id': task_ids[3],
        'subtasks': [],
        'tags': [tags['waitingfor']],
        'added': today,
        'modified': today,
        'content': _(
            "If you press the &quot;Actionable&quot; tab, only actionable tasks "
            "will be displayed in your list.\n"
            "\n"
            "What is an actionable task? It's a task you can do directly, right "
            "now.\n"
            "\n"
            "It's a task that is already &quot;start-able&quot;, i.e. the start "
            "date is already over.\n"
            "\n"
            "It's a task that doesn't have open subtasks, i.e. you can do the "
            "task itself directly, it does not depend on something else.\n"
            "\n"
            "It's a task that has a due date different than &quot;Someday&quot;, "
            "since this kind of date is reserved for things that needs more "
            "thoughts before being actionable.\n"
            "\n"
            "As the Actionable view only shows tasks that you can act on presently, "
            "it is very useful when you want to focus on the next actions to take "
            "to get things done!\n"
            "\n"
            "If you use tags, you can right-click on a tag in the sidebar and  "
            "choose to hide tasks assigned to this particular tag from the Actionable "
            "view. It is very useful if you have a tag like &quot;@waitingfor&quot; "
            "that you use for tasks blocked by some external event (i.e. such as "
            "a phone callback you're waiting for).\n"
            "\n"
            "And finally, an important note: since the Actionable view is "
            "updated instantaneously, if you edit your task while inside the "
            "Actionable view, it might disappear from the view due to the change "
            "you just made (e.g. adding a tag hidden in the Actionable view, etc.). "
            "To avoid this, you may prefer to edit your task while "
            "in the &quot;Open&quot; tasks view instead.")
    },

    {
        'title': _("Learn About Plugins"),
        'id': task_ids[4],
        'subtasks': [],
        'tags': [],
        'added': today,
        'modified': today,
        'content': _(
            "GTG has the ability to add plugins to extend its core functionality."
            "\n\n"
            "You can find the Plugins Manager by clicking on &quot;Plugins&quot; "
            "in the main window's menu button. We would like to encourage you "
            "to write your own plugins and contribute them to the GTG project "
            "so that we can consider them for wider inclusion.")
    },

    {
        'title': _("Reporting Bugs"),
        'id': task_ids[5],
        'subtasks': [],
        'tags': [],
        'added': today,
        'modified': today,
        'content': _(
            "It is a well-known fact that GTG has no bugs! 🐛\n"
            "But sometimes, in the dark, unexpected things happen...\n"
            "\n"
            "If you encounter crashes/tracebacks or unexpected behavior in general, "
            "please provide a detailed bug report in our issues tracker at "
            "https://github.com/getting-things-gnome/gtg/issues/new\n"
            "\n"
            "Your help and involvement is what makes this software better. "
            "Feedback, bug reports and ideas are welcome... and patches even more so!")
    },

    {
        'title': _("Learn How to Use the Quick Add Entry"),
        'id': task_ids[6],
        'subtasks': [],
        'tags': [],
        'added': today,
        'modified': today,
        'content': _(
            "The Quick Add entry is the fastest way to create a new task "
            "without disrupting your focus from the main window. "
            "It has a special syntax with additional keywords you can use; "
            "refer to the user manual to learn more about its features and syntax.")
    },

    {
        'title': _("Learn About Synchronization Services"),
        'id': task_ids[7],
        'subtasks': [],
        'tags': [],
        'added': today,
        'modified': today,
        'content': _(
            "❗ Take note that as of GTG 0.4, synchronization backends/services have "
            "been disabled until someone (you?) steps forward to fix and maintain "
            "them, as they have not been fully updated to work with the new codebase."
            "or to interface with the latest APIs of those online services.\n"
            "\n"
            "Synchronization services allow GTG to synchronize (or import/export) "
            "tasks, notes or bugs from some websites or applications such as "
            "Remember the Milk, Tomboy, LaunchPad, etc.\n"
            "\n"
            "This can useful if, for instance, you want to access your "
            "tasks on several instances of GTG running on separate computers, or "
            "if you want to edit your tasks using an online service.\n"
            "\n"
            "To use synchronization services, click the menu button in the main window, "
            "and select &quot;Synchronization&quot;. You will then have the "
            "possibility to select among several online or local services "
            "from/to where you can import or export your tasks.")
    },

    {
        'title': _("Learn How to Search for Tasks"),
        'id': task_ids[8],
        'subtasks': [],
        'tags': [tags['errands']],
        'added': today,
        'modified': today,
        'content': _(
            "To help you to find specific tasks more easily, GTG allows you to "
            "search for tasks based on their content.\n"
            "\n"
            "Searching for tasks is really easy: in the main window, hit Ctrl+F and "
            "just type the words you are looking for in the search bar.\n"
            "\n"
            "GTG can store your searches in the sidebar, in the &quot;Saved Searches"
            "&quot; section. You can thus always go back to a previous search if you "
            "need it. Search results are updated automatically, so you always get "
            "all the tasks matching your search request.\n"
            "\n"
            "GTG's search feature is really powerful and accepts many parameters "
            "that allow you to search for very specific tasks. For instance, "
            "using the search query &quot;@errands !today&quot;, you can search "
            "for tasks with the @errands tag that must be done today. To learn "
            "more about the various search parameters you can use, refer to the "
            "Search Syntax documentation in GTG's user manual, found through the "
            "&quot;Help&quot; menu item in the main window's menu button.")
    },
]


def generate() -> etree.Element:
    """Generate the XML tree with first run tasks."""

    # Create an empty XML tree first
    root = xml.skeleton()
    taskslist = root.find('tasklist')
    taglist = root.find('taglist')

    # Fill tags
    for tag, tid in tags.items():
        tag_tag = etree.SubElement(taglist, 'tag')
        tag_tag.set('id', tid)
        tag_tag.set('name', tag)


    # Fill tasks
    for task in tasks:
        task_tag = etree.SubElement(taskslist, 'task')
        task_tag.set('id', task['id'])
        task_tag.set('status', 'Active')

        title = etree.SubElement(task_tag, 'title')
        title.text = task['title']

        # Add tags for this task
        task_tags = etree.SubElement(task_tag, 'tags')

        for tag in task['tags']:
            tag_tag = etree.SubElement(task_tags, 'tag')
            tag_tag.text = tag

        dates = etree.SubElement(task_tag, 'dates')
        added = etree.SubElement(dates, 'added')
        added.text = task['added']

        recurring_enabled = etree.SubElement(dates, 'recurring_enabled')
        recurring_enabled.text = 'false'

        recurring = etree.SubElement(task_tag, 'recurring')
        recurring.set('enabled', 'false')

        recurring_term = etree.SubElement(recurring, 'term')
        recurring_term.text = 'None'

        modify = etree.SubElement(dates, 'modified')
        modify.text = task['modified']

        # Add subtasks in this tasks
        subtask = etree.SubElement(task_tag, 'subtasks')

        for sub in task['subtasks']:
            sub_tag = etree.SubElement(subtask, 'sub')
            sub_tag.text = sub

        content = etree.SubElement(task_tag, 'content')
        content.text = etree.CDATA(task['content'])

    return etree.ElementTree(root)
