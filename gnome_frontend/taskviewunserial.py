import xml.dom.minidom


######################## Deserializing ##################################

### Deserialize : put all in the TextBuffer
# This function signature is defined in PyGTK
class Unserializer :
    def __init__(self,taskview) :
        #We keep a reference to the original taskview
        #Not very pretty but convenient
        self.tv = taskview

    def unserialize(self,register_buf, content_buf, ite, data, cr_tags, udata) :
        if data :
            element = xml.dom.minidom.parseString(data)
            success = self.parsexml(content_buf,ite,element.firstChild)
        else :
            success = self.parsexml(content_buf,ite,None)
        return True
        
    #Insert a list of subtasks at the end of the buffer
    def insert_subtasks(self,buff,st_list) :
        for tid in st_list :
            line_nbr = buff.get_end_iter().get_line()
            self.tv.write_subtask(buff,line_nbr,tid)
            
    #insert a GTG tag with its TextView tag.
    #Yes, we know : the word tag is used for two different concepts here.
    def insert_tag(self,buff,tag,itera=None) :
        if not itera :
            itera = buff.get_end_iter()
        if tag :
            sm = buff.create_mark(None,itera,True)
            em = buff.create_mark(None,itera,False)
            buff.insert(itera,tag)
            s = buff.get_iter_at_mark(sm)
            e = buff.get_iter_at_mark(em)
            self.tv.apply_tag_tag(buff,tag,s,e)
        
    #parse the XML and put the content in the buffer
    def parsexml(self,buf,ite,element) :
        start = buf.create_mark(None,ite,True)
        end   = buf.create_mark(None,ite,False)
        subtasks = self.tv.get_subtasks()
        taglist2 = []
        if element :
            for n in element.childNodes :
                itera = buf.get_iter_at_mark(end)
                if n.nodeType == n.ELEMENT_NODE :
                    #print "<%s>" %n.nodeName
                    if n.nodeName == "subtask" :
                        tid = n.firstChild.nodeValue
                        #We remove the added subtask from the list
                        #Of known subtasks
                        #If the subtask is not in the list, we don't write it
                        if tid in subtasks :
                            subtasks.remove(tid)
                            line_nbr = itera.get_line()
                            self.tv.write_subtask(buf,line_nbr,tid)
                    elif n.nodeName == "tag" :
                        text = n.firstChild.nodeValue
                        if text :
                            self.insert_tag(buf,text,itera)
                            #We remove the added tag from the tag list
                            #of known tag for this task
                            taglist2.append(text[1:])
                    else :
                        self.parsexml(buf,itera,n)
                        s = buf.get_iter_at_mark(start)
                        e = buf.get_iter_at_mark(end)
                        if n.nodeName == "link" :
                            anchor = n.getAttribute("target")
                            tag = self.tv.create_anchor_tag(buf,anchor,None)
                            buf.apply_tag(tag,s,e)
                        else :
                            buf.apply_tag_by_name(n.nodeName,s,e)
                elif n.nodeType == n.TEXT_NODE :
                    buf.insert(itera,n.nodeValue)
        #Now, we insert the remaining subtasks
        self.insert_subtasks(buf,subtasks)
        #We also insert the remaining tags (a a new line)
        taglist = self.tv.get_tagslist()
        for t in taglist2 :
            if t in taglist :
                taglist.remove(t)
        if len(taglist) > 0 :
            self.tv.insert_at_mark(buf,end,"\n")
        for t in taglist :
            it = buf.get_iter_at_mark(end)
            self.insert_tag(buf,"@%s"%t,it)
            self.tv.insert_at_mark(buf,end,", ")
        buf.delete_mark(start)
        buf.delete_mark(end)
        return True
