# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2026 - the GTG contributors
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

from unittest import TestCase
from uuid import uuid4

from gi.repository import GObject, Gtk

from GTG.core.tasks import FilteredTaskTreeManager, TaskStore, Task
from GTG.core.filters import unwrap



class LambdaFilter(Gtk.Filter):


    def __init__(self,filter_func):
        super(LambdaFilter, self).__init__()
        self.filter_func = filter_func


    def do_match(self,item) -> bool:
        task = item if isinstance(item, Task) else unwrap(item, Task)
        return self.filter_func(task)


    def set_filter_function(self,func):
        self.filter_func = func
        self.changed(Gtk.FilterChange.DIFFERENT)



def create_task_store(titles):
    "Create a task store based an a nested dict of titles."
    store = TaskStore()
    for title, children in titles.items():
        task = Task(uuid4(),title)
        store.add(task)
        _add_subtree(store,children,task.id)
    return store


def _add_subtree(store,subtree,parent_id):
    for title, children in subtree.items():
        task = Task(uuid4(),title)
        store.add(task,parent_id)
        _add_subtree(store,children,task.id)


def get_titles_as_tree(tree_model):
    """
    Return the GtkTreeListModel as a nested dict.
    - Each key is the title of the task, so make sure they all differ.
    - This function will expand the rows of the tree model.
    """
    titles = dict()
    root_model = tree_model.get_model()
    for i in range(root_model.get_n_items()):
        row = tree_model.get_child_row(i)
        task = unwrap(row,Task)
        titles[task.title] = _explore_row(row)
    return titles


def _explore_row(row):
    """
    Recursively collect the descendant titles into a nested dict.
    """
    titles = dict()
    row.set_expanded(True)
    num_of_children = row.get_children().get_n_items()
    for i in range(num_of_children):
        child_row = row.get_child_row(i)
        task = unwrap(child_row,Task)
        titles[task.title] = _explore_row(child_row)
    return titles



class TestFilteredTaskTreeManagerWithoutChanges(TestCase):


    def setUp(self):
        self.task_store = create_task_store({
            "a":{
                "aa": dict(),
                "ab": {
                    "aba": dict(),
                    "abb": dict(),
                },
            },
            "b":dict()
        })


    def test_no_match(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda _: False))
        tree_model = fttm.get_tree_model()
        self.assertEqual(get_titles_as_tree(tree_model),dict())


    def test_only_root_match(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda t: len(t.title)==1))
        tree_model = fttm.get_tree_model()
        want = {
            "a": dict(),
            "b": dict(),
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_only_third_level_match(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda t: len(t.title)==3))
        tree_model = fttm.get_tree_model()
        want = {
            "aba": dict(),
            "abb": dict(),
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_only_first_subtree_match(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda t: t.title[0]=="a"))
        tree_model = fttm.get_tree_model()
        want = {
            "a": {
                "aa": dict(),
                "ab": {
                    "aba": dict(),
                    "abb": dict(),
                }
            },
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_only_tasks_with_b_match(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda t: "b" in t.title))
        tree_model = fttm.get_tree_model()
        want = {
            "ab": {
                "aba": dict(),
                "abb": dict(),
            },
            "b": dict()
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_everything_matches(self):
        fttm = FilteredTaskTreeManager(self.task_store,LambdaFilter(lambda _: True))
        tree_model = fttm.get_tree_model()
        want = {
            "a": {
                "aa": dict(),
                "ab": {
                    "aba": dict(),
                    "abb": dict(),
                },
            },
            "b": dict()
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)



class TestFilteredTaskTreeManagerWithFilterChange(TestCase):


    def test_simple_root_task_changes(self):
        store = create_task_store({
            "[AB] this will remain": dict(),
            "[A.] this will be removed": dict(),
            "[.B] this will appear": dict(),
            "[..] this will stay hidden": dict(),
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[AB] this will remain": dict(),
            "[.B] this will appear": dict(),
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_simple_child_task_changes(self):
        store = create_task_store({
            "[AB] this parent will remain":{
                "[AB] this will remain": dict(),
                "[A.] this will be removed": dict(),
                "[.B] this will appear": dict(),
                "[..] this will stay hidden": dict(),
            },
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[AB] this parent will remain":{
                "[AB] this will remain": dict(),
                "[.B] this will appear": dict(),
            }
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_removed_parent(self):
        store = create_task_store({
            "[A.] this parent will be removed":{
                "[AB] this will remain": dict(),
                "[A.] this will be removed": dict(),
                "[.B] this will appear": dict(),
                "[..] this will stay hidden": dict(),
            },
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[AB] this will remain": dict(),
            "[.B] this will appear": dict(),
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_added_parent(self):
        store = create_task_store({
            "[.B] this parent will be added":{
                "[AB] this will remain": dict(),
                "[A.] this will be removed": dict(),
                "[.B] this will appear": dict(),
                "[..] this will stay hidden": dict(),
            },
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[.B] this parent will be added":{
                "[AB] this will remain": dict(),
                "[.B] this will appear": dict(),
            }
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_flatten_a_deep_chain(self):
        store = create_task_store({
            "[A.] 1": {
                "[AB] 2":{
                    "[A.] 3":{
                        "[AB] 4":{
                            "[A.] 5":{
                                "[AB] 6": dict()
                            }
                        }
                    }
                }
             }
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[AB] 2": dict(),
            "[AB] 4": dict(),
            "[AB] 6": dict(),
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_rebuild_a_deep_chain(self):
        store = create_task_store({
            "[.B] 1": {
                "[AB] 2":{
                    "[.B] 3":{
                        "[AB] 4":{
                            "[.B] 5":{
                                "[AB] 6": dict()
                            }
                        }
                    }
                }
             }
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[.B] 1": {
                "[AB] 2":{
                    "[.B] 3":{
                        "[AB] 4":{
                            "[.B] 5":{
                                "[AB] 6": dict()
                            }
                        }
                    }
                }
             }
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)


    def test_hide_and_show_entire_subtrees(self):
        store = create_task_store({
            "[AB] this will remain": { "[AB] 1": dict(),"[AB] 2": dict() },
            "[A.] this will be removed": { "[A.] 1": dict(),"[A.] 2": dict() },
            "[.B] this will appear": { "[.B] 1": dict(),"[.B] 2": dict() },
            "[..] this will stay hidden": { "[..] 1": dict(),"[..] 2": dict() },
        })
        task_filter = LambdaFilter(lambda t: "A" in t.title)
        fttm = FilteredTaskTreeManager(store,task_filter)
        tree_model = fttm.get_tree_model()
        task_filter.set_filter_function(lambda t: "B" in t.title)
        want = {
            "[AB] this will remain": { "[AB] 1": dict(),"[AB] 2": dict() },
            "[.B] this will appear": { "[.B] 1": dict(),"[.B] 2": dict() },
        }
        self.assertEqual(get_titles_as_tree(tree_model),want)
