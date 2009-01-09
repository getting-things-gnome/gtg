import sys, os, xml.dom.minidom

#This is for the awful pretty xml things
tab = "\t"
enter = "\n"

#Those two functions are there only to be able to read prettyXML
#Source : http://yumenokaze.free.fr/?/Informatique/Snipplet/Python/cleandom       
def cleanDoc(document,indent="",newl=""):
    node=document.documentElement
    cleanNode(node,indent,newl)

def cleanNode(currentNode,indent,newl):
    filter=indent+newl
    if currentNode.hasChildNodes:
        for node in currentNode.childNodes:
            if node.nodeType == 3 :
                node.nodeValue = node.nodeValue.lstrip(filter).strip(filter)
                if node.nodeValue == "":
                    currentNode.removeChild(node)
        for node in currentNode.childNodes:
            cleanNode(node,indent,newl)
            
#This function open an XML file if it exists and return the XML object
#If the file doesn't exist, it is created with an empty XML tree    
def openxmlfile(zefile,root ):
    if os.path.exists(zefile) :
        f = open(zefile,mode='r')
        doc=xml.dom.minidom.parse(zefile)
        cleanDoc(doc,tab,enter)
        xmlproject = doc.getElementsByTagName(root)
    
    #the file didn't exist, create it now
    else :
        doc = xml.dom.minidom.Document()
        rootproject = doc.createElement(root)
        doc.appendChild(rootproject)
        xmlproject = doc.getElementsByTagName(root)
        #then we create the file
        f = open(zefile, mode='a+')
        f.write(doc.toxml().encode("utf-8"))
        f.close()
        
    return doc,xmlproject
    
def savexml(zefile,doc) :
    f = open(zefile, mode='w+')
    f.write(doc.toprettyxml(tab,enter).encode("utf-8"))
    f.close()
