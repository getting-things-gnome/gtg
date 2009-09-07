import pickle
import os
import xml.utils.iso8601
from datetime import date

__all__ = ["smartSaveToFile",
           "smartLoadFromFile",
           "filterAttr",
           "iso8601toTime",
           "timeToIso8601"]

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

def iso8601toTime (string):
    return date.fromtimestamp(xml.utils.iso8601.parse(string))

def timeToIso8601 (timeobject):
    print type(timeobject)
    print timeobject
    try:
        return timeobject.strftime("%Y-%m-%dT%H:%M:%S")
    except:
        return ""

