# Installation

    pip3 install coverage

# Configuration

By default coverage will measure all code, unless it is part of the Python standard library. So we'd better create a confguration file named `.coveragerc` under root directory of GTG codebase mostly for specifying source files for measurement.

For only gtk part measurement, the configuration file could be something like below:

```
[run]
source =
    gtg
    GTG/gtk
    ../liblarch/liblarch_gtk
omit =
    run-tests
    GTG/tests/*
    ../liblarch/test*
```

For full measurement, it will be something like:

```
[run]
source =
    gtg
    GTG
    ../liblarch
omit =
    run-tests
    GTG/tests/*
    ../liblarch/test*
```

# Coverage

    coverage run gtg -d

You can add more arguments for gtg at the end of command above. For example, if you would like to use local `liblarch` for both testing, you can use:

    coverage run gtg -d -l

# Report

After running `coverage` command, it will create a file named `.coverage` to store related information. To generate the report, we need run '''coverage report''' and the report will be shown on the screen. To generate a annotated HTML listings detailing missed lines, we need to run '''coverage html''' and then we can visit `htmlcov/index.html` in the browser for a nicer presentation.

# Combine

One big problem for testing with coverage is that, coverage report will reset each time after experiments on running tests. To keep the information before, we can use another powerful feature, `combine`. Each time after generating one `.coverage` file, we can move it to another extra directory, for example, named `combine` with different file names.
When we have enough `.coverage` files, we can copy all previous `.coverage` files back to the root directory of GTG codebase. Then we need to run '''coverage combine''' to combine all `.coverage` files, after which all `.coverage` files will be converted to one sigle `.coverage` file, then you can go on with '''Report''' part work.

# List of steps to do coverage testing

This is not a full list, any suggestions or contribution are welcome!

    GTG/gtk/backends_dialog:
          Open the `backends` window
          Click the `Add` button
          Click the `Cancel` button
          Add `Tomboy` Backend
          Enable Sync of `Tomboy` Backend
          Disable Sync of `Tomboy` Backend
          Rename `Tomboy` Backend to `test`
          Remove `Tomboy` Backend
          Close the `backends` window
     GTG/﻿gtk/browser:
          Main Window:
               Maximize the window
               Minimize the window
               Resize the window
               Change to `workflow` view
               Hide and show `Tags Sidebar`
               Hide and show `Closed Tasks Pane`
               Hide and show `Toolbar`
               Hide and show `Quick Add Entry`
               Drag and drop task on tag (NOT WORK)
          Tag Sidebar:
               Randomly choose a tag
               Move a tag as sub tag of another one
               Edit a tag via right click context menu
               keyboard event
               Change Sidebar Width
               Collapsed the tag
               Delete a search
          Closed Tasks Pane:
               Randomly choose a closed task
               keyboard event
          Task View:
               Randomly choose a task
               Move a task as sub task of another one
               Open task edit dialog
               Add subtask
               Mark a task as done
               Mark a task as not to be done anymore
               Remove a task
               Modify tags
               Set/clear start/due date
               no active tasks
               open with collapsed_tasks
               modify tags
               keyboard event
               Sort title/start date/due date
          Quick Add Entry:
               Add a task
               Click the clear button
          Toolbar:
               Mark a task as done
               Mark a task as not to be done anymore
               Add a new task
          Menu:
               Open `About` Dialog
               Click `License`
               Click `Credit`
               Close `About` Dialog
               Click all items in menu
          Plugins:
               Toggle plugin
               Click configurable plugin
          Modify tag dialog:
               Add tag
               Remove tag
               Apply to subtasks
          Tag Editor:
               Focus out
               Set/Remove tag color
     GTG/gtk/editor/editor:
          Create new task
          Close task with subtasks
     GTG/gtk/editor/taskview:
          Randomly open a dialog
          Change the text and close task dialog
          Change start/due date
          Cut/Copy/Paste (Partial Work)
          Insert a subtask with toolbar
          Insert a tag with toolbar
          Mark a task as done/Undone/Deleted with toolbar
          Use `-` to insert subtask


# Example of a full report

This was the report on 2013-09-25, with Xuan Hu's port of GTG to GTK3+Python3, by using previous configuration file and list of steps for coverage testing:

```
Name                                                           Stmts   Miss  Cover
----------------------------------------------------------------------------------
../liblarch/liblarch_gtk/__init__      281     34    88%
../liblarch/liblarch_gtk/treemodel      94     20    79%
GTG/gtk/__init__                                                   8      0   100%
GTG/gtk/backends_dialog/__init__                                 118      6    95%
GTG/gtk/backends_dialog/addpanel                                  93      0   100%
GTG/gtk/backends_dialog/backendscombo                             40      0   100%
GTG/gtk/backends_dialog/backendstree                             121      0   100%
GTG/gtk/backends_dialog/configurepanel                           103      7    93%
GTG/gtk/browser/CellRendererTags                                  98     16    84%
GTG/gtk/browser/__init__                                          27      0   100%
GTG/gtk/browser/browser                                          914     92    90%
GTG/gtk/browser/modifytags_dialog                                 48      1    98%
GTG/gtk/browser/tag_context_menu                                  33      0   100%
GTG/gtk/browser/tag_editor                                       270     29    89%
GTG/gtk/browser/treeview_factory                                 310      9    97%
GTG/gtk/colors                                                    47     23    51%
GTG/gtk/delete_dialog                                             68      1    99%
GTG/gtk/editor/__init__                                           18      0   100%
GTG/gtk/editor/calendar                                           95      6    94%
GTG/gtk/editor/editor                                            377     45    88%
GTG/gtk/editor/taskview                                          836     99    88%
GTG/gtk/editor/taskviewserial                                    136     13    90%
GTG/gtk/manager                                                  158     19    88%
GTG/gtk/plugins                                                  174     42    76%
GTG/gtk/preferences                                              155     12    92%
GTG/gtk/tag_completion                                            60      2    97%
----------------------------------------------------------------------------------
TOTAL                                                           4682    476    90%
```
