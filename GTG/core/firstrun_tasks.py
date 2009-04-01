from GTG.tools import cleanxml

def populate() :
    doc,root = cleanxml.emptydoc("project")
    #Task 0@1 : Getting started with GTG
    title1 = _("Getting started with GTG")
    text1 = _("Welcome in Getting Things Gnome!, your new task manager.")
    text1 += "\n\n"
    text1 += _("In GTG, everything is a task. From building a bridge over the Pacific Ocean to changing a light bulb or organizing a party. When you edit a task, it is automatically saved.")
    text1 += "\n\n"
    text1 += _("Once a task is done, you can push the &quot;Mark as done&quot; button. If the task is not relevant any-more, simply press &quot;Dismiss&quot;.")
    text1 += "\n\n"
    text1 += _("A task might be composed of multiple subtasks that appear as links in the description. Simply click on the following link :")
    text1 += "\n"
    text1 += "<subtask>1@1</subtask>\n"
    text1 += "\n\n"
    text1 += _("Don't forget to mark this subtask as done !")
    text1 += "\n\n"
    text1 += _("Other stuff you should read :")
    text1 += "\n"
    text1 += "<subtask>2@1</subtask>\n"
    text1 += "<subtask>3@1</subtask>\n"
    text1 += "<subtask>4@1</subtask>\n"
    text1 += "\n\n"
    text1 += _("We hope that you will appreciate GTG. Please send us bug reports and ideas for improvement using :")
    text1 += "https://bugs.launchpad.net/gtg"
    text1 += "\n\n"
    text1 += _("Thank you for trying out GTG :-)")
    t1 = addtask(doc,"0@1",title1,text1,["1@1","2@1","3@1","4@1"])
    root.appendChild(t1)
    
    #Task 1@1 : Learn to use subtasks
    title2 = _("Learn to use subtasks")
    text2 = _("In the task description (this window), if you begin a line with &quot;-&aquot;, it will be considered as a &quot;subtask&quot;, something that needs to be done in order to accomplish your task. Just try to write &quot;- test subtask&quot; on the next line and press enter.")
    text2 += "\n\n"
    text2 += _("You can also use the &quot;insert subtask&quot; button.")
    text2 += "\n\n\n"
    text2 += _("Task and subtasks can be re-organized by drag-n-drop in the tasks list.")
    text2 += "\n\n"
    text2 += _("Some concept come with subtasks : for example, a subtask due date can never be after its parent due date.")
    text2 += "\n\n"
    text2 += _("Also, marking a parent as done will mark all the subtasks as done.")
    t2 = addtask(doc,"1@1",title2,text2,[])
    root.appendChild(t2)
    
    #Task 2@1 : Learn to use tags
    title3 = _("Learn to use tags")
    text3 = _("A tag is a simple word that begin with &quot;@&quot;.")
    text3 += "\n\n"
    text3 += _("Try to type a word beginning with @ here :")
    text3 += "\n\n"
    text3 += _("It becomes yellow, it's a tag.")
    text3 += "\n\n"
    text3 += _("Tags are useful to sort your tasks. In the view menu, you can enable a sidebar which displays all the tags you are using so you can easily see tasks for a given tag. There's no limit to the number of tags a task can have.")
    text3 += "\n\n"
    text3 += _("If you right click on a tag in the sidebar you can also set its color. It will permit you to have a more colorful list of tasks, if you want it that way.")
    t3 = addtask(doc,"2@1",title3,text3,[])
    root.appendChild(t3)
    
    #Task 3@1 : Using the Workview
    title4 = _("Using the Workview")
    text4 = _("If you press the &quot;Workview&quot; button, only actionable tasks will be displayed.")
    text4 += "\n\n"
    text4 += _("What is an actionable task? It's a task you can do directly, right now.")
    text4 += "\n\n"
    text4 += _("It's a task that is already &quot;start-able&quot;, i.e. the start date is already over.")
    text4 += "\n\n"
    text4 += _("It's a task that doesn't have open subtasks, i.e. you can do the task itself directly.")
    text4 += "\n\n"
    text4 += _("Thus, the workview will only show you tasks you should do right now.")
    text4 += "\n\n"
    text4 += _("If you use tags, you can right click on a tag in the sidebar and choose to not display tasks with this particular tag in the workview. It's very useful if you have a tag like &quot;someday&quot; that you use for tasks you would like to do but are not particularly urgent.")
    
    t4 = addtask(doc,"3@1",title4,text4,[])
    root.appendChild(t4)
    
    #Task 4@1 : Reporting bugs
    title5 = _("Reporting bugs")
    text5 = _("GTG is still very alpha software. We like it and use it everyday but you will encounter some bugs.")
    text5 += "\n\n"
    text5 += _("Please, report them ! We need you to make this software better. Any contribution, any idea is welcome.")
    text5 += "\n\n"
    text5 += _("If you have some trouble with GTG, we might be able to help you or to solve your problem really quickly.")
    
    t5 = addtask(doc,"4@1",title5,text5,[])
    root.appendChild(t5)
    
    
    return doc
    

def addtask(doc,ze_id,title,text,childs) :
    t_xml = doc.createElement("task")
    t_xml.setAttribute("id",ze_id)
    t_xml.setAttribute("status" , "Active")
    t_xml.setAttribute("tags", "")
    cleanxml.addTextNode(doc,t_xml,"title",title)
    for c in childs :
        cleanxml.addTextNode(doc,t_xml,"subtask",c)
    cleanxml.addTextNode(doc,t_xml,"content",text)
    return t_xml
