import pickle
import os

__all__ = [ "smartSaveToFile",
            "smartLoadFromFile",
            "filterAttr"]

def smartLoadFromFile(dirname,filename):
    path=dirname+'/'+filename
    if os.path.isdir(dirname):
        if os.path.isfile(path):
            try:
                with open(path,'r') as file:
                    item = pickle.load(file)
            except:
                return None
            return item
    else:
        os.makedirs(dirname)

def smartSaveToFile(dirname,filename, item,**kwargs):
    path=dirname+'/'+filename
    try:
        with open(path,'wb') as file:
            pickle.dump(item, file)
    except:
        if kwargs.get('critical',False):
            raise Exception ('saving critical object failed')

def unziplist(a):
    return tuple(map(list,zip(*a)))

def filterAttr (list, attr, value):
    return filter (lambda elem: getattr(elem,attr) == value, list)
