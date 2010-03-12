from GTG import _
from GTG.tools import cleanxml

def populate():
    doc,root = cleanxml.emptydoc("project")

    #Task 0@1: Getting started with GTG
    title1 = _("Getting started with GTG")
    text1 = _("""Welcome to Getting Things Gnome!, your new task manager.

In GTG, everything is a task. From building a bridge over the Pacific Ocean to changing a light bulb or organizing a party. When you edit a task, it is automatically saved.

Once a task is done, you can push the &quot;Mark as done&quot; button. If the task is not relevant any-more, simply press &quot;Dismiss&quot;.

A task might be composed of multiple subtasks that appear as links in the description. Simply click on the following link:""")
    text1 += "\n<subtask>1@1</subtask>\n"
    text1 += _("""Once you've read the above subtask, mark it as Done. If you don't want to do the task, mark it as dismissed. Done and Dismissed tasks are kept in the closed tasks pane, hidden by default but you can easily enable it in the View menu.

If you choose to close this current task, subtasks will be automatically closed too. We indeed consider that, if you achieve a given task, you don't need to do the subtask anymore.
Other stuff you should read:""")
    text1 += """\n<subtask>2@1</subtask>
    <subtask>3@1</subtask>
    <subtask>4@1</subtask>
    <subtask>5@1</subtask>
    <subtask>6@1</subtask>\n"""
    text1 += _("""We hope that you will appreciate GTG. Please send us bug reports and ideas for improvement using:
    https://bugs.launchpad.net/gtg

Thank you for trying out GTG :-)""")
    t1 = addtask(doc, "0@1", title1, text1, ["1@1", "2@1", "3@1", "4@1", "5@1", "6@1"])
    root.appendChild(t1)
    
    #Task 1@1: Learn to use subtasks
    title2 = _("Learn how to use subtasks")
    text2 = _("""In the task description (this window), if you begin a line with &quot;-&quot;, it will be considered as a &quot;subtask&quot;, something that needs to be done in order to accomplish your task. Just try to write &quot;- test subtask&quot; on the next line and press enter.

You can also use the &quot;insert subtask&quot; button.

Tasks and subtasks can be re-organized by drag-n-drop in the tasks list.

Some concepts come with subtasks: for example, a subtask's due date can never be after its parent's due date.

Also, marking a parent as done will mark all the subtasks as done.""")
    t2 = addtask(doc, "1@1", title2, text2, [])
    root.appendChild(t2)
    
    #Task 2@1: Learn to use tags
    title3 = _("Learn how to use tags")
    text3 = _("""A tag is a simple word that begins with &quot;@&quot;.

Try to type a word beginning with @ here:

It becomes yellow, it's a tag.

Tags are useful to sort your tasks. In the view menu, you can enable a sidebar which displays all the tags you are using so you can easily see tasks assigned to a given tag. There's no limit to the number of tags a task can have.

You can drag-n-drop a tag onto another to create \"subtags\". As an example, if you drag the tag @to_pay onto the tag @money, every task tagged with @to_pay will also appear in the view of @money (but the @money tag is not added to the task).

If you right click on a tag in the sidebar you can also set its color. It will allow you to have a more colorful list of tasks, if you want it that way.

A new tag is only added to the current task. There's no recursion and the tag is not applied to subtasks. But when you create a new subtask, this subtask will inherit the tags of its parent as a good primary default (it will also be the case if you add a tag to a parent just after creating a subtask). Of course, you can modify at any time the tags of this particular subtask. It will never be changed by the parent.""")
    t3 = addtask(doc, "2@1", title3, text3, [])
    root.appendChild(t3)
    
    #Task 3@1: Using the Workview
    title4 = _("Learn how to use the Workview")
    text4 = _("""If you press the &quot;Workview&quot; button, only actionable tasks will be displayed.

What is an actionable task? It's a task you can do directly, right now.

It's a task that is already &quot;start-able&quot;, i.e. the start date is already over.

It's a task that doesn't have open subtasks, i.e. you can do the task itself directly.

Thus, the workview will only show you tasks you should do right now.

If you use tags, you can right click on a tag in the sidebar and choose to hide tasks assigned to this particular tag in the workview. It's very useful if you have a tag like &quot;someday&quot; that you use for tasks you would like to do but are not particularly urgent.""")
    t4 = addtask(doc, "3@1", title4, text4, [])
    root.appendChild(t4)
    
    #Task 5@1: Plugins
    title5 = _("Learn how to use Plugins")
    text5 = _("""GTG has the ability to add plugins to extend it's core functionality.

Some examples of the current plugins are Syncing with Remember the Milk and Evolution, Tomboy/Gnote integration and Geolocalized Tasks.
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
    title7 = _("Learn how to use the QuickAdd Entry")
    text7 = _("""The quickadd entry is the quickest way to create a new task. You can show or hide it in the View menu.
For adding a task you just have to type its title in the entry and press return. The task will be created and selected in the task browser. If a tag is selected in the tag panel, this tag is applied to the task you create.
You can also create a task with attributes like tags, due date or defer date in the quickadd entry.
For that the syntax is :

tags:tag1,tag2,tag3 : This way you can apply as many tags as you wish using comma as separator

due:date or defer:date : This way you can apply a due date or a defer date. date can be yyyy-mm-dd (for exemple 2009-04-01) or yyyymmdd (20090401) or mmdd (0401, in this case the year is implicitly the current one) or today or tomorrow or a weekday name (due:monday means due next Monday)

Attributes which are added in this way apply but do not appear in the title.
If a word begins with @, it is interpreted as a tag.""")

    t7 = addtask(doc, "6@1", title7, text7, [])
    root.appendChild(t7)

    return doc
    

def addtask(doc, ze_id, title, text, childs):
    t_xml = doc.createElement("task")
    t_xml.setAttribute("id", ze_id)
    t_xml.setAttribute("status", "Active")
    t_xml.setAttribute("tags", "")
    cleanxml.addTextNode(doc, t_xml, "title", title)
    for c in childs:
        cleanxml.addTextNode(doc, t_xml, "subtask", c)
    cleanxml.addTextNode(doc, t_xml, "content", text)
    return t_xml
