import pickle
import os
import xml.utils.iso8601
from datetime import datetime
import time

__all__ = ["smartSaveToFile",
           "smartLoadFromFile",
           "filterAttr",
           "iso8601toTime",
           "timeToIso8601",
           "unziplist"]

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
    if len(a) == 0:
        return [],[]
    return tuple(map(list,zip(*a)))

def filterAttr (list, attr, value):
    return filter (lambda elem: getattr(elem,attr) == value, list)

def iso8601toTime (string):
    #FIXME: need to handle time with TIMEZONES!
    string = string.split('.')[0].split('Z')[0]
    if string.find('T') == -1:
        return time.strptime(string.split(".")[0], "%Y-%m-%d")
    return time.strptime(string.split(".")[0], "%Y-%m-%dT%H:%M:%S")

def timeToIso8601 (timeobject):
    t = timeobject
    return str(t.tm_year)+ "-" + str(t.tm_mon)+ "-" + str(t.tm_mday) + \
            "T" + str(t.tm_hour) + ":" + str(t.tm_min)+ ":" + str(t.tm_sec)
