import sys, os, xml.dom.minidom

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
