class Tree():

    def __init__(self, root=None):
        if root:
            self.root = root
        else:
            self.root = TreeNode(id="root")

    def __str__(self):
        return "<Tree: root = '%s'>" % (str(self.root))

    def get_rowref_for_path(self, path):
        return self._rowref_for_path(self.root, path)

    def get_path_for_rowref(self, rowref):
        return self._path_for_rowref(self.root, rowref)

    def get_node_for_rowref(self, rowref):
        return self._node_for_rowref(self.root, rowref)

    def get_rowref_for_node(self, node):
        return self._rowref_for_node(node)

    def get_root(self):
        return self.root

    def set_root(self, root):
        self.root = root
        
    def print_tree(self):
        self._print_from_node(self.root)

    def visit_tree(self, pre_func=None, post_func=None):
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

### HELPER FUNCTION FOR TREE #################################################

    def _rowref_for_path(self, node, path):
        if len(path) == 1:
            return "/" + str(node.get_nth_child(path[0]).get_id())
        else:
            node = node.get_nth_child(path[0])
            path = path[1:]
            return "/" + str(self._node_for_tm_path(node, path))

    def _path_for_rowref(self, node, rowref):
        if rowref.rfind('/') == 0:
            return (node.get_child_index(rowref[1:]),)
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            cur_node = node.get_child(cur_id)
            cur_path = (node.get_child_index(cur_id),)
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return cur_path + self._path_for_rowref(cur_node, rowref)

    def _node_for_rowref(self, node, rowref):
        if rowref.rfind('/') == 0:
            return node.get_child(rowref[1:])
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            print rowref
            cur_node = node.get_child(cur_id)
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return self._node_for_rowref(cur_node, rowref)

    def _rowref_for_node(self, node):
        if not node.has_parent():
            return ""
        else:
            parent = node.get_parent()
            return self._rowref_for_node(parent) + "/" + str(node.get_id())

    def _print_from_node(self, node, prefix=""):
        print prefix + node.id
        prefix = prefix + " "
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._print_from_node(cur_node, prefix)

    def _visit_node(self, node, pre_func=None, post_func=None):
        if pre_func: pre_func(node)
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._visit_node(cur_node, pre_func, post_func)
        if post_func: post_func(node)


class TreeNode():

    def __init__(self, id, parent=None):
        self.parent   = parent
        self.id       = id
        self.children = {}

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.path)

    def get_id(self):
        return self.id

    def has_parent(self):
        return self.parent is not None

    def get_parent(self):
        return self.parent

    def set_parent(self, par):
        self.parent = par

    def has_child(self):
        return len(self.children) != 0

    def get_children(self):
        return self.children.keys()

    def get_n_children(self):
        return len(self.children)

    def get_nth_child(self, index):
        k = self.children.keys()[index]
        return self.children[k]

    def get_child(self, id):
        return self.children[id]

    def get_child_index(self, id):
        return self.children.keys().index(id)

    def add_child(self, id, child):
        self.children[id] = child

    def remove_child(self, id):
        return self.children.pop(id)