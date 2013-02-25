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

""" Create tasks for the first run

Tasks should serve as a quick tutorial how GTG works """

from GTG import _
from GTG.tools import cleanxml
from GTG.tools.tags import extract_tags_from_text


def populate():
    """On the first run of GTG, populate the task list with tasks meant to
    act as a GTG tutorial."""
    doc, root = cleanxml.emptydoc("project")

    # Task 0@1: Getting started with GTG
    title1 = _("Getting Started With GTG")
    text1 = _(
        "Welcome to Getting Things GNOME!, your new task manager! In Getting "
        "Things GNOME! (GTG), everything is a task. From building a bridge"
        " over the Pacific Ocean to changing a light bulb or organizing a"
        " party!\n\n"
        "If you are new to GTG, please take the time to read this, as it will"
        " provide you useful information about how to use GTG to organize"
        " your everyday life.\n"
        "\n"
        "Creating and editing tasks:\n"
        "\n"
        "Using GTG is easy: you organize what you have to do by creating new"
        " tasks. To do this, simply press the &quot;New Task&quot; button, "
        "edit the task by describing it, set some parameters, and that's "
        "it! Once a task done, you can close it by pressing the &quot;Mark As"
        " Done&quot; button.\n"
        "\n"
        "In GTG, a task is automatically saved while you are editing it. No"
        " need to press any &quot;Save&quot; button! Try it: add some text to"
        " this task, close the window, and reopen it: your changes are still"
        " there!\n\n"
        "About subtasks:\n"
        "\n"
        "In life, you often get more things done by refining them in "
        "smaller, more operational tasks. GTG helps to do just this by "
        "defining  &quot;subtasks&quot;. In GTG, those subtasks are "
        "considered as prerequisites that must be completed before being able"
        " to close their parent task.\n\n"
        "Therefore, in GTG, a task might host one or several subtasks. Those "
        "appear as links in the task description, just like the link below. "
        "To open and edit a subtask, simply click on its link! Try it"
        " yourself: open the following subtask:\n"
        "<subtask>1@1</subtask>\n"
        "\n"
        "Closing a task:\n"
        "\n"
        "In GTG, once you are done with a task, you can close it by pushing "
        "either the &quot;Mark as Done&quot; or the &quot;Dismiss&quot; "
        "button. Use the first one if the task is done, and the latter if you"
        " want to close it because it is not relevant anymore. Want to try it"
        "? Try to close the subtask above for instance!\n"
        "\n"
        "When you close a task, you will notice that all its subtasks will be"
        " automatically closed too! Indeed, GTG considers that if you have"
        " completed a given task, then you don't need to do its subtasks"
        " anymore (they were prerequisites, after all).\n"
        "\n"
        "Note that the tasks that you have marked as done or dismissed are "
        "listed in the &quot;Closed Tasks Pane&quot; which is hidden by"
        " default, but you can easily show it using the View menu.\n"
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
        "<subtask>7@1</subtask>\n"
        "<subtask>8@1</subtask>\n"
        "\n"
        "You can also browse GTG documentation by pressing F1 or opening it"
        " using the Help menu.\n"
        "\n"
        "We sincerely hope you will enjoy using GTG, and thank you for trying"
        " it out! Please send us bug reports and ideas for improvement using"
        " this web page: https://bugs.launchpad.net/gtg/+filebug If you want "
        "to get tips for using GTG or be informed about the newest features, "
        "also visit our blog at http://gtg.fritalk.com\n"
        "\n"
        "The GTG team.")
    task1 = addtask(doc, "0@1", title1, text1,
                    ["1@1", "2@1", "3@1", "4@1", "5@1", "6@1", "7@1", "8@1"])
    root.appendChild(task1)

    # Task 1@1: Learn to use subtasks
    title2 = _("Learn How To Use Subtasks")
    text2 = _(
        "A &quot;Subtask&quot; is something that you need to do first before "
        "being able to accomplish your task. In GTG, the purpose of subtasks "
        "is to cut down a task in smaller subtasks that are easier to achieve"
        " and to track down.\n\n"
        "To insert a subtask in the task description (this window, for "
        "instance), begin a line with &quot;-&quot;, then write the subtask "
        "title and press Enter.\n"
        "\n"
        "Try inserting one subtask below. Type &quot;- This is my first "
        "subtask!&quot;, for instance, and press Enter:\n"
        "\n"
        "\n"
        "\n"
        "Alternatively, you can also use the &quot;Insert Subtask&quot; "
        "button.\n\n"
        "Note that subtasks obey to some rules: first, a subtask's due date "
        "can never happen after its parent's due date and, second, when you "
        "mark a parent task as done, its subtasks will also be marked as "
        "done.\n\n"
        "And if you are not happy with your current tasks/subtasks "
        "organization, you can always change it by drag-and-dropping tasks on"
        " each other in the tasks list.")
    task2 = addtask(doc, "1@1", title2, text2, [])
    root.appendChild(task2)

    # Task 2@1: Learn to use tags
    title3 = _("Learn How To Use Tags")
    text3 = _(
        "In GTG, you use tags to sort your tasks. A tag is a simple word that"
        " begins with &quot;@&quot;.\n"
        "\n"
        "Try to type a word beginning with &quot;@&quot; here:\n"
        "\n"
        "Once it becomes yellow, it is a tag! And this tag is now linked to "
        "the task!\n"
        "\n"
        "Using the View menu, you can enable a sidebar which displays all the"
        " tags you are using. This allows you to easily see all tasks "
        "associated to a given tag.\n"
        "\n"
        "If you right-click on a tag in the sidebar, you can also edit it. It"
        " allows you to assign it a color or an icon for instance. This is "
        "handy if you want to quickly identify the tasks associated to a "
        "given tag in the task list!\n\n"
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
    task3 = addtask(doc, "2@1", title3, text3, [])
    root.appendChild(task3)

    # Task 3@1: Using the Workview
    title4 = _("Learn How To Use The Work View")
    text4 = _(
        "If you press the &quot;Work View&quot; button, only actionable tasks"
        " will be displayed in your list.\n"
        "\n"
        "What is an actionable task? It's a task you can do directly, right "
        "now.\n\n"
        "It's a task that is already &quot;start-able&quot;, i.e. the start "
        "date is already over.\n"
        "\n"
        "It's a task that doesn't have open subtasks, i.e. you can do the "
        "task itself directly.\n"
        "\n"
        "It's a task that has a due date different than &quot;Someday&quot;, "
        "since this kind of date is reserved for things that needs more "
        "thoughts before being actionable.\n"
        "\n"
        "Thus, in short, the Work View shows you tasks that you can do right "
        "now. It's very useful when you want to get things done and to focus "
        "on the relevant tasks!\n"
        "\n"
        "If you use tags, you can right click on a tag in the sidebar and "
        "choose to hide tasks assigned to this particular tag in the Work "
        "View. It is very useful if you have a tag like &quot;@wait&quot; "
        "that you use for tasks blocked by some external event (i.e. a phone "
        "call you wait to receive).\n\n"
        "And finally, an important note regarding the Work View: since the "
        "Work View is updated instantaneously, if you edit your task while "
        "using the Work View, this task might disappear due to the change you"
        " just made (e.g. adding a subtask, adding a tag hidden in the Work "
        "View, etc.). To avoid this, it's better not to edit your task while "
        "using the Work View. ")
    task4 = addtask(doc, "3@1", title4, text4, [])
    root.appendChild(task4)

    # Task 5@1: Plugins
    title5 = _("Learn How To Use Plugins")
    text5 = _(
        "GTG has the ability to add plugins to extend its core functionality."
        "\n\n"
        "Some examples of the currently available plugins are the "
        "notification icon which displays a handy shortcut to GTG in your "
        "notification space, or the closed tasks remover which automatically "
        "deletes old tasks from your closed tasks list.\n"
        "\n"
        "You can find the Plugin Manager by selecting Edit in the Menu Bar, "
        "then clicking Plugins.")
    task5 = addtask(doc, "4@1", title5, text5, [])
    root.appendChild(task5)

    # Task 5@1: Reporting bugs
    title6 = _("Reporting Bugs")
    text6 = _(
        "GTG is still beta software. We like it and use it everyday but you "
        "will probably encounter some bugs will you do.\n"
        "\n"
        "Please, help us improving GTG by reporting them on our Launchpad "
        "page:https://bugs.launchpad.net/gtg/+filebug\n"
        "\n"
        "We need you to make this software better. Any contribution, any "
        "idea is welcome!\n"
        "\n"
        "If you have some trouble with GTG, we might be able to help you or "
        "to solve your problem really quickly.")
    task6 = addtask(doc, "5@1", title6, text6, [])
    root.appendChild(task6)

    # Task 6@1: Learn how to use the QuickAdd Entry
    title7 = _("Learn How To Use The Quick Add Entry")
    text7 = _(
        "The Quick Add Entry is the fastest way to create a new task. Use "
        "the check box in the View menu to enable and disable the entry field"
        ".\n\n"
        "To add a task simply type its title in the entry and press Enter. "
        "The task will be created and selected in the task browser. If a tag "
        "is selected in the Tags Sidebar, it will be applied to the task you "
        "created.\n\n"
        "You can also create a task in the Quick Add Entry and at the same "
        "time specify its tags, due and defer date. Follow these format rules"
        ":\n\n"
        "tags:tag1,tag2,tag3\n"
        "\n"
        "Using this you can apply as many tags as you wish using comma as "
        "separator. Note that any word in the title that begins with &quot;"
        "@&quot; will also be interpreted as a tag!\n"
        "\n"
        "due:date\n"
        "defer:date\n"
        "\n"
        "Using this you can apply a due date or a defer date. Dates can be "
        "formated as per your locale or yyyy-mm-dd (for example 2012-04-01) "
        "or yyyymmdd (20120401) "
        "or mmdd (0401 - the year being implicitly the current one) or today,"
        " tomorrow or a weekday name (due:monday means due next Monday). "
        "Dates which are added in this way will not appear in the task title."
        "\n\n"
        "Examples:\n"
        "\n"
        "buy stationary tags:purchases,office due:20120330 defer:tuesday\n"
        "\n"
        "The above example tells GTG to create a new task with the title "
        "&quot;buy stationary&quot;, under the tags &quot;purchases&quot; "
        "and &quot;office&quot;, with the due date March 30, 2012 and the "
        "start date next Tuesday.\n"
        "\n"
        "call mum tags:family,calls due:sunday defer:tomorrow\n"
        "\n"
        "The above example tells GTG to create a new task with the title "
        "&quot;call mum&quot;, under the tags &quot;family&quot; and "
        "&quot;calls&quot;, with the due date next Sunday and the start "
        "date tomorrow.")
    task7 = addtask(doc, "6@1", title7, text7, [])
    root.appendChild(task7)

    # Task 7@1: Learn How To Use Synchonization Services
    title8 = _("Learn How To Use Synchronization Services")
    text8 = _(
        "Synchronization Services allow GTG to synchronize (meaning to have "
        "access or to import) tasks, notes or bugs from other sites or "
        "services like Launchpad, Remember the Milk, Tomboy, etc.\n"
        "\n"
        "This can incredibly useful if, for instance, you want to access your"
        " tasks on several instances of GTG running on separate computers, or"
        " if you want to edit your tasks using an online service. GTG can "
        "also import tasks from specific sites like launchpad for instance, "
        "which allows you to manage the bug reports you're working on in GTG!"
        "\n\n"
        "To use Synchronization Services, use the Edit menu, and select "
        "&quot;Synchronization Services&quot;. You will then have the "
        "possibility to select among several online or local services "
        "from/to where you can import or export your tasks.\n"
        "\n"
        "If you want to know more about Synchronization Services, you can "
        "read more about them by in the dedicated documentation in GTG's help"
        " (use the Help menu or press F1 to get access to it).")
    task8 = addtask(doc, "7@1", title8, text8, [])
    root.appendChild(task8)

    # Task 8@1: Learn How To Search For Tasks
    title9 = _("Learn How To Search For Tasks")
    text9 = _(
        "To help you to find specific tasks more easily, GTG allows you to "
        "search for tasks based on their content.\n"
        "\n"
        "Searching for tasks is really easy: just type the words you are "
        "looking for in the Quick Add Entry, and select &quot;Search&quot; in"
        " the menu that will appear automatically.\n"
        "\n"
        "GTG stores your searches in the sidebar, under the &quot;Search"
        "&quot; section. You can thus always go back to a previous search "
        "need it. Search results are updated automatically, so you always get"
        " all the tasks matching your search request.\n"
        "\n"
        "GTG also saves all the search requests you have made until you "
        "explicitely delete them (which you can do by right-clicking on them "
        "and selecting &quot;Delete&quot;). That allows you to safely quit "
        "GTG without loosing your search requests. This can be very useful "
        "when you use the search features to identify specific tasks "
        "regularly!\n\n"
        "GTG search feature is really powerful and accept many parameters "
        "that allows you to search for very specific tasks. For instance, "
        "using the search query &quot;@errands !today&quot;, you can search "
        "for tasks with the @errands tag that must be done today. To learn "
        "more about those search query parameters, you can read the "
        "documentation available in GTG's help (press F1 or use the Help menu"
        " to get access to it).")
    task9 = addtask(doc, "8@1", title9, text9, [])
    root.appendChild(task9)

    return doc


def addtask(doc, ze_id, title, text, children):
    """Initialize GTG tasks in order to display them at first run."""
    t_xml = doc.createElement("task")
    t_xml.setAttribute("id", ze_id)
    t_xml.setAttribute("status", "Active")

    tags = extract_tags_from_text(text)
    t_xml.setAttribute("tags", ",".join(tags))

    cleanxml.addTextNode(doc, t_xml, "title", title)
    for child in children:
        cleanxml.addTextNode(doc, t_xml, "subtask", child)
    cleanxml.addTextNode(doc, t_xml, "content", text)
    return t_xml
