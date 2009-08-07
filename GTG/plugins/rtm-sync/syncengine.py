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

import os
import sys
import time
import subprocess
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home
import pickle

# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)+'/pyrtm'))
import rtm
from bijectivefunction import BijectiveFunction

def unziplist(a):
    return tuple(map(list,zip(*a)))
        

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


def getToken():
    #NOTE: token is valid forever, so it's basically a configuration
    #(like user/password)
    config_dir = os.path.join(xdg_config_home,'gtg/plugins/rtm-sync')
    token = smartLoadFromFile (config_dir, 'token')
    if token == None:
        rtm_obj=rtm.createRTM ("2a440fdfe9d890c343c25a91afd84c7e", \
                               "ca078fee48d0bbfa");
        subprocess.Popen(['xdg-open', rtm_obj.getAuthURL()])
        raw_input("press enter when done")
        token = rtm_obj.getToken()
        smartSaveToFile(config_dir,'token', token)
    return token

def synchronize(plugin_api):
    tasks = map (plugin_api.get_task, \
                 plugin_api.get_requester().get_active_tasks_list())
    #TODO:  handling connection failures and denial of access, proper interface 
    rtm_obj=rtm.createRTM ("2a440fdfe9d890c343c25a91afd84c7e",\
                           "ca078fee48d0bbfa", getToken() );
    time.sleep(1)
    #NOTE: a timeline is an undo list for RTM. It can be used for journaling
    #(timeline rollback is atomical)
    timeline = rtm_obj.timelines.create().timeline
    #NOTE: syncing only incomplete tasks for now
    #(it's easier to debug the things you see)
    lists_id_list = map (lambda x: x.id,rtm_obj.lists.getList().lists.list)
    def get_list_of_taskseries (x): 
        currentlist = rtm_obj.tasks.getList\
                (filter='status:incomplete',list_id=x).tasks
        if hasattr (currentlist, 'list'):
            return currentlist.list
        else:
            return []
    task_list_global= map (get_list_of_taskseries,lists_id_list)
    taskseries_list = filter(lambda x: hasattr (x[0],'taskseries')\
                             , zip(task_list_global,lists_id_list))
    tasks_list_wrapped = map (lambda x: (x[0].taskseries,x[1]), taskseries_list)

    #needs python 2.5, but it's in Jauntyz
    
    tasks_list_normalized = map(lambda x:  zip(x[0],[x[1]]*len(x[0]), \
            map(lambda x: x.id,x[0])) if type(x[0]) == list \
            else [(x[0],x[1],x[0].id)] ,tasks_list_wrapped)
    tasks_list_unwrapped = reduce(lambda x,y: x+y , tasks_list_normalized)
    task_objects_list,list_ids_list,taskseries_ids_list = \
            unziplist(tasks_list_unwrapped)

    #TODO: RTM allows multiple task with the same name, gtg does not. Solve!
    #FIXME:  from here on we assume that purging of the multiple entries has
    #  been done     (keep an eye on the "set" objects, since they do the
    #  purging silently)
    gtg_task_titles_list = map(lambda x: x.get_title(), tasks)
    gtg_task_id_list = map(lambda x: x.get_id(), tasks)
    rtm_task_titles_list = map(lambda x: x.name, task_objects_list)
    #FIXME:probably wont work with recurring events
    rtm_task_id_list = map(lambda x: x.task.id, task_objects_list)

    rtm_task_id_to_list_id=dict(zip(rtm_task_id_list, list_ids_list))
    rtm_task_id_to_taskseries_id=dict(\
                                zip (rtm_task_id_list, taskseries_ids_list))
    
    rtm_title_to_id_bijFun = BijectiveFunction (\
                                    rtm_task_titles_list, rtm_task_id_list)
    gtg_title_to_id_bijFun = BijectiveFunction (\
                                    gtg_task_titles_list, gtg_task_id_list)

    
    
    gtg_task_titles_set = set (gtg_task_titles_list)
    rtm_task_titles_set = set (rtm_task_titles_list)


    
    ## loading the mapping of the last sync
    cache_dir = os.path.join(xdg_cache_home,'gtg/plugins/rtm-sync')
    gtg_to_rtm_task_id_mapping = smartLoadFromFile (\
                                    cache_dir, 'gtg_to_rtm_task_id_mapping')
    if   gtg_to_rtm_task_id_mapping is None: 
        ###this is the first synchronization
        gtg_to_rtm_task_id_mapping = []
        #tasks in common
        for title in rtm_task_titles_set.intersection (gtg_task_titles_set):
            gtg_to_rtm_task_id_mapping.append (\
                    (gtg_title_to_id_bijFun.leftFindElem(title), \
                     rtm_title_to_id_bijFun.leftFindElem(title)))

        #tasks that must be added to GTG
        for title in rtm_task_titles_set.difference (gtg_task_titles_set):
            new_task = plugin_api.get_requester().new_task(newtask=True)
            new_task.set_title(title)
            gtg_to_rtm_task_id_mapping.append ((new_task.get_id(), \
                                rtm_title_to_id_bijFun.leftFindElem(title)))

        #tasks that must be added to RTM
        for title in gtg_task_titles_set.difference (rtm_task_titles_set):
            #TODO: this line should be a function with lots of nice parameters
            new_task= rtm_obj.tasks.add(timeline=timeline, name=title)\
                    .list.taskseries.task
            gtg_to_rtm_task_id_mapping.append (\
                    (gtg_title_to_id_bijFun.leftFindElem(title), new_task.id))

    else:
        ###this is an update

        ##updating the status of the task (present or removed)
        #if the task is still present,return the task id, else return None
        update_gtg_id = lambda x: x if \
                len(filter( lambda y: y == x,gtg_task_id_list)) != 0 else None
        update_rtm_id = lambda x: x if \
                len(filter( lambda y: y == x,rtm_task_id_list)) != 0 else None
        gtg_to_rtm_task_id_mapping_new = map ( lambda x: (update_gtg_id(x[0]),\
                            update_rtm_id(x[1])), gtg_to_rtm_task_id_mapping)
        #removing the tasks that have been removed in GTG or RTM
        to_be_removed = filter (lambda x: (x[0] == None or x[1] == None) \
                                and not (x[0] == None and x[1] == None),\
                                gtg_to_rtm_task_id_mapping_new)
        to_be_removed_from_rtm_extended = filter ( lambda x: x[0] == None , \
                                                  to_be_removed)
        to_be_removed_from_gtg_extended = filter ( lambda x: x[1] == None ,\
                                                  to_be_removed)
        to_be_removed_from_rtm = None
        to_be_removed_from_gtg = None
        print to_be_removed_from_rtm_extended
        if len (to_be_removed_from_rtm_extended) != 0:
            temp,to_be_removed_from_rtm = unziplist(\
                                            to_be_removed_from_rtm_extended)
            print to_be_removed_from_rtm
            for elem in to_be_removed_from_rtm:
                map (lambda x: rtm_obj.tasks.delete(timeline = timeline, \
                        list_id = rtm_task_id_to_list_id[x], \
                        taskseries_id = rtm_task_id_to_taskseries_id[x], \
                        task_id = x), to_be_removed_from_rtm)

        if len (to_be_removed_from_gtg_extended) != 0:
            to_be_removed_from_gtg, temp = unziplist(\
                            to_be_removed_from_gtg_extended)
            map (lambda x: plugin_api.get_requester().delete_task(x),\
                            to_be_removed_from_gtg)

        ##task that need to be updated
        to_be_updated = filter (lambda x: x[0] != None and x[1] != None,\
                                gtg_to_rtm_task_id_mapping_new)
        ##TODO:update
        for item in to_be_updated:
            if gtg_title_to_id_bijFun.rightFindElem(item[0])!=\
                    rtm_title_to_id_bijFun.rightFindElem(item[1]):
                print "detected title change. still to implement"

        ##new tasks
        gtg_task_id_current_set = set (gtg_task_id_list)
        rtm_task_id_current_set = set (rtm_task_id_list)
        gtg_task_id_old_set, rtm_task_id_old_set = \
                unziplist (gtg_to_rtm_task_id_mapping_new)
        gtg_new_tasks_set = \
                gtg_task_id_current_set.difference (gtg_task_id_old_set)
        rtm_new_tasks_set = \
                rtm_task_id_current_set.difference (rtm_task_id_old_set)

        for id in rtm_new_tasks_set:
            new_task = plugin_api.get_requester().new_task(newtask=True)
            new_task.set_title(rtm_title_to_id_bijFun.rightFindElem(id))
            gtg_to_rtm_task_id_mapping_new.append ((new_task.get_id(), id))
        #FIXME:gtg reuses id! need uuid
        for id in gtg_new_tasks_set:
            new_task= rtm_obj.tasks.add(timeline=timeline,\
                    name=gtg_title_to_id_bijFun.rightFindElem(id))\
                    .list.taskseries.task
            gtg_to_rtm_task_id_mapping.append ((id, new_task.id))

    #TODO: ask if ok or undo (easy on rtm (see timeline),
    #   but on gtg? need to keep a journal?  
    smartSaveToFile(cache_dir,'gtg_to_rtm_task_id_mapping',\
                    gtg_to_rtm_task_id_mapping)







    






