# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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

from __future__ import with_statement

import pickle
import os
import datetime
import time
import re
from GTG import _

__all__ = ["smartSaveToFile",
           "smartLoadFromFile",
           "filterAttr",
           "iso8601toTime",
           "timeToIso8601",
           "dateToIso8601",
           "unziplist",
           "timezone"]


def smartLoadFromFile(dirname, filename):
    path=dirname+'/'+filename
    if os.path.isdir(dirname):
        if os.path.isfile(path):
            try:
                with open(path, 'r') as file:
                    item = pickle.load(file)
            except:
                return None
            return item
    else:
        os.makedirs(dirname)


def smartSaveToFile(dirname, filename, item, **kwargs):
    path=dirname+'/'+filename
    try:
        with open(path, 'wb') as file:
            pickle.dump(item, file)
    except:
        if kwargs.get('critical', False):
            raise Exception(_("saving critical object failed"))


def unziplist(a):
    if len(a) == 0:
        return [], []
    return tuple(map(list, zip(*a)))


def filterAttr(list, attr, value):
    return filter(lambda elem: getattr(elem, attr) == value, list)


def iso8601toTime(string):
    #FIXME: need to handle time with TIMEZONES!
    string = string.split('.')[0].split('Z')[0]
    if string.find('T') == -1:
        return datetime.datetime.strptime(string.split(".")[0], "%Y-%m-%d")
    return datetime.datetime.strptime(string.split(".")[0], \
                                      "%Y-%m-%dT%H:%M:%S")


def timeToIso8601(timeobject):
    if not hasattr(timeobject, 'strftime'):
        return ""
    return timeobject.strftime("%Y-%m-%dT%H:%M:%S")


def dateToIso8601(timeobject):
    if not hasattr(timeobject, 'strftime'):
        return ""
    return timeobject.strftime("%Y-%m-%d")


def timezone():
    if time.daylight:
        return datetime.timedelta(seconds = time.altzone)
    else:
        return datetime.timedelta(seconds = time.timezone)

def text_strip_tags(text):
    r = re.compile(r'<content>(.*)</content>',re.DOTALL)
    result = re.findall(r, text)
    if len(result) == 0:
        #something is wrong
        return text
    text = result[0]
    r = re.compile(r'(?:^|\s)@[\w]+,*')
    last_match_end = 0
    purged_text = ""
    for match in r.finditer(text):
        purged_text += text[last_match_end : match.start()]
        last_match_end = match.end()
    return purged_text 

