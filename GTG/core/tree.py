class Tree():

    def __init__(self, root=None):
        self.nodes = {}
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

    def get_path_for_node(self, node):
        return self._path_for_node(node)

    def get_root(self):
        return self.root

    def set_root(self, root):
        self.root = root

    def add_node(self, id, node, parent):
        if parent:
            node.set_parent(parent)
            parent.add_child(id, node)
        else:
            node.set_parent(self.root)
            self.root.add_child(id, node)
        node_list = self.nodes.get(id)
        if node_list:
            node_list.append(node)
        else:
            self.nodes[id] = [node]

    def remove_node(self, id, node):
        if node.has_child():
            for c_id in node.get_children():
                self.remove_node(c_id, node.get_child(c_id))
        if node.has_parent():
            par = node.get_parent()
            par.remove_child(node.get_id())
        node_list = self.nodes.get(id)
        node_list.remove(node)

    def get_nodes(self, id):
        if id in self.nodes:
            return list(self.nodes[id])
        else:
            return []

    def has_node(self, id):
        return id in self.nodes.keys()

    def print_tree(self):
        self._print_from_node(self.root)

    def visit_tree(self, pre_func=None, post_func=None):
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

### HELPER FUNCTION FOR TREE #################################################
#
    def _rowref_for_path(self, node, path):
        if path[0] < node.get_n_children():
            if len(path) == 1:
                return "/" + str(node.get_nth_child(path[0]).get_id())
            else:
                node = node.get_nth_child(path[0])
                path = path[1:]
                c_path = self._rowref_for_path(node, path)
                if c_path:
                    return "/" + str(node.get_id()) + str(c_path)
                else:
                    return None
        else:
            return None

    def _path_for_rowref(self, node, rowref):
        if rowref.rfind('/') == 0:
            return (node.get_child_index(rowref[1:]), )
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            cur_node = node.get_child(cur_id)
            cur_path = (node.get_child_index(cur_id), )
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return cur_path + self._path_for_rowref(cur_node, rowref)

    def _node_for_rowref(self, node, rowref):
        #print "_node_for_rowref: %s" % rowref
        if rowref == '':
            return self.root
        elif rowref.rfind('/') == 0:
            return node.get_child(rowref[1:])
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            cur_node = node.get_child(cur_id)
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return self._node_for_rowref(cur_node, rowref)

    def _rowref_for_node(self, node):
        if not node.has_parent():
            return ""
        else:
            parent = node.get_parent()
            return self._rowref_for_node(parent) + "/" + str(node.get_id())

    def _path_for_node(self, node):
        if not node.has_parent():
            return ()
        else:
            parent = node.get_parent()
            index  = parent.get_child_index(node.get_id())
            return self._path_for_node(parent) + (index, )

    def _print_from_node(self, node, prefix=""):
        print prefix + node.id
        prefix = prefix + " "
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._print_from_node(cur_node, prefix)

    def _visit_node(self, node, pre_func=None, post_func=None):
        if pre_func:
            pre_func(node)
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._visit_node(cur_node, pre_func, post_func)
        if post_func:
            post_func(node)


class TreeNode():

    def __init__(self, id, obj=None, parent=None):
        self.parent   = parent
        self.id       = id
        self.ids      = []
        self.children = []
        self.obj      = obj

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.id)

    def get_obj(self):
        return self.obj

    def set_obj(self, obj):
        self.obj = obj

    def get_id(self):
        return self.id

    def has_parent(self):
        return self.parent is not None

    def get_parent(self):
        return self.parent

    def set_parent(self, par):
        self.parent = par

    def has_child(self):
        return len(self.ids) != 0

    def get_children(self):
        return list(self.ids)

    def get_n_children(self):
        return len(self.ids)

    def get_nth_child(self, index):
        return self.children[index]

    def get_child(self, id):
        idx = self.ids.index(id)
        return self.children[idx]

    def get_child_index(self, id):
        return self.ids.index(id)

    def add_child(self, id, child):
        self.ids.append(id)
        self.children.append(child)

    def remove_child(self, id):
        idx   = self.ids.index(id)
        child = self.children[idx]
        self.ids.remove(id)
        self.children.remove(child)
        
    def reparent(self, parent):
        if self.has_parent():
            self.get_parent().remove_child(self.id)
        self.set_parent(parent)
        parent.add_child(self.id, self)
        
