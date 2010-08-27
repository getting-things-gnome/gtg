class TreeTester:
    '''A class that will check if a tree implementation is consistent
    by connecting to emitted signals and crashing on any problem'''
    def __init__(self,viewtree):
        self.tree = viewtree
        #both dict should always be synchronized
        self.nodes = {}
        self.paths = {}
        self.tree.register_cllbck('node-added-inview',self.add)
        self.tree.register_cllbck('node-deleted-inview',self.delete)
        self.tree.register_cllbck('node-modified-inview',self.update)
        self.tree.register_cllbck('node-children-reordered',self.update)
        self.trace = "* * * * * * * *\n"
        
        
    def add(self,nid,path):
        self.trace += "adding %s to path %s\n" %(nid,str(path))
        currentnode = self.paths.get(path,None)
        if currentnode and currentnode != nid:
            raise Exception('path %s is already occupied by %s' %(str(path),nid))
        if self.nodes.has_key(nid):
            node = self.nodes[nid]
        else:
            node = []
            self.nodes[nid] = node
        if path not in node:
            node.append(path)
        self.paths[path] = nid
    
    def delete(self,nid,path):
        self.trace += "removing %s from path %s\n" %(nid,str(path))
        if nid != self.paths.get(path,None):
            raise Exception('%s is not assigned to path %s'%(nid,str(path)))
        if path not in self.nodes.get(nid,[]):
            raise Exception('%s is not a path of node %s'%(str(path),nid))
        self.nodes[nid].remove(path)
        self.paths.pop(path)
    
    def update(self,nid,path):
        self.trace += "updating %s in path %s\n" %(nid,str(path))
        error = "updating node %s for path %s\n" %(nid,str(path))
        #Nothing to do, we just update.
        for p in self.nodes[nid]:
            if self.paths[p] != nid:
                raise Exception('Mismatching path for %s'%nid)
        if not self.paths.has_key(path):
            error += '%s is not in stored paths (node %s)\n'%(str(path),nid)
            error += self.print_tree()
            raise Exception(error)
        n = self.paths[path]
        if path not in self.nodes[n] or n != nid:
            raise Exception('Mismatching node for path %s'%str(p))
            
    def reordered(self,nid,path,neworder):
    
    
    def test_validity(self):
        for n in self.nodes.keys():
            for p in self.nodes[n]:
                if self.paths[p] != n:
                    raise Exception('Mismatching path for %s'%n)
        for p in self.paths.keys():
            n = self.paths[p]
            if p not in self.nodes[n]:
                raise Exception('Mismatching node for path %s'%str(p))
        return True
        
    def print_tree(self):
        st = self.trace
        st += "nodes are %s\n" %self.nodes
        st += "paths are %s\n" %self.paths
        return st
