# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

import os, xml.dom.minidom
import shutil
import sys
import time
import re
import datetime

from GTG.tools.logger import Log

#This is for the awful pretty xml things
tab = "\t"
enter = "\n"
BACKUP_NBR = 7

#Those two functions are there only to be able to read prettyXML
#Source : http://yumenokaze.free.fr/?/Informatique/Snipplet/Python/cleandom       
def cleanDoc(document,indent="",newl=""):
    node = document.documentElement
    cleanNode(node,indent,newl)

def cleanNode(currentNode,indent,newl):
    myfilter = indent+newl
    if currentNode.hasChildNodes:
        toremove = []
        for node in currentNode.childNodes:
            if node.nodeType == 3 :
                val = node.nodeValue.lstrip(myfilter).strip(myfilter)
                if val == "":
                    toremove.append(node)
                else:
                    node.nodeValue = val
        #now we remove the nodes that were empty
        for n in toremove:
            currentNode.removeChild(n)
        for node in currentNode.childNodes:
            cleanNode(node,indent,newl)

def cleanString(string,indent="",newl=""):
    #we will remove the pretty XML stuffs.
    #Firt, we remove the \n and tab in elements
    e = re.compile('>\n\t*')
    toreturn = e.sub('>',string)
    #then we remove the \n tab before closing elements
    f = re.compile('\n\t*</')
    toreturn = f.sub('</',toreturn)
    return toreturn

#This add a text node to the node parent. We don't return anything
#Because the doc object itself is modified.
def addTextNode(doc,parent,title,content) :
    if content :
        element = doc.createElement(title)
        parent.appendChild(element)
        element.appendChild(doc.createTextNode(content))
        
#This is a method to read the textnode of the XML
def readTextNode(node,title) :
    n = node.getElementsByTagName(title)
    if n and n[0].hasChildNodes() :
        content = n[0].childNodes[0].nodeValue
        if content :
            return content
    return None
            
#This function open an XML file if it exists and return the XML object
#If the file doesn't exist, it is created with an empty XML tree    
def openxmlfile(zefile,root ):
    tmpfile = zefile+'__'
#    print "opening %s file" %zefile
    try:
        if os.path.exists(zefile):
            f = open(zefile, "r")
        elif os.path.exists(tmpfile):
            Log.debug("Something happened to the tags file. Using backup")
            os.rename(tmpfile, zefile)
            f = open(zefile, "r")
        else:
            # Creating empty file
            doc,xmlproject = emptydoc(root)
            newfile = savexml(zefile, doc) # use our function to save file
            if not newfile:
                sys.exit(1)
            return openxmlfile(zefile, root) # recursive call
        stringed = f.read()
        stringed = cleanString(stringed,tab,enter)
        doc = xml.dom.minidom.parseString(stringed)
#        doc = xml.dom.minidom.parse(f)
#        print "cleaning %s" %zefile
        cleanDoc(doc,tab,enter)
        xmlproject = doc.getElementsByTagName(root)[0]
        f.close()
        return doc,xmlproject
    except IOError, msg:
        print msg
        sys.exit(1)
        
    except xml.parsers.expat.ExpatError, msg:
        f.close()
        errormsg = "Error parsing XML file %s: %s" %(zefile, msg)
        Log.debug(errormsg)
        if os.path.exists(tmpfile):
            Log.debug("Something happened to the tags file. Using backup")
            os.rename(tmpfile, zefile)
            # Ok, try one more time now
            return openxmlfile(zefile, root)
        # At least, print error message so users are not so much confused
        print errormsg
        sys.exit(1)


#Return a doc element with only one root element of the name "root"
def emptydoc(root) :
    doc = xml.dom.minidom.Document()
    rootproject = doc.createElement(root)
    doc.appendChild(rootproject)
    return doc, rootproject
    
#write a XML doc to a file
def savexml(zefile,doc,backup=False):
#    print "writing %s file" %(zefile)
    tmpfile = zefile+'__'
    try:
        if os.path.exists(zefile):
            os.rename(zefile, tmpfile)
        f = open(zefile, mode='w+')
        pretty = doc.toprettyxml(tab, enter).encode("utf-8")
        if f and pretty:
            bwritten = os.write(f.fileno(), pretty)
            if bwritten != len(pretty):
                print "error writing file %s" % zefile
                f.close()
                return False
            f.close()
            
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
                
            if backup :
                #We will now backup the file
                backup_nbr = BACKUP_NBR
                #We keep BACKUP_NBR versions of the file
                #The 0 is the youngest one
                while backup_nbr > 0 :
                    older = "%s.bak.%s" %(zefile,backup_nbr)
                    backup_nbr -= 1
                    newer = "%s.bak.%s" %(zefile,backup_nbr)
                    if os.path.exists(newer) :
                        shutil.move(newer,older)
                #The bak.0 is always a fresh copy of the closed file
                #So that it's not touched in case of bad opening next time
                current = "%s.bak.0" %(zefile)
                shutil.copy(zefile,current)

                daily_backup = "%s.%s.bak" % (zefile, datetime.date.today().strftime("%Y-%m-%d"))
                if not os.path.exists(daily_backup):
                    shutil.copy(zefile, daily_backup)
            return True
        else:
            print "no file %s or no pretty xml"%zefile
            return False
    except IOError, msg:
        print msg
        return False
