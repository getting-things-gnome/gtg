import xml.dom.minidom


#The following functions are used by the gtk.TextBuffer to serialize
# the content of the task

########### Serializing functions ###############

### Serialize the task : transform it's content in something
#we can store. This function signature is defined in PyGTK
class Serializer :

    #Disabling pylint argument usage since we know we are not using all args
    def serialize(self,register_buf, content_buf, start, end, udata) : #pylint: disable-msg=W0613
        #Currently we serialize in XML
        its = start.copy()
        ite = end.copy()
        #Warning : the serialization process cannot be allowed to modify 
        #the content of the buffer.
        doc = xml.dom.minidom.Document()
        tag_stack = {}
        doc.appendChild(self.parse_buffer(content_buf,its, ite,"content",doc,tag_stack))
        #We don't want the whole doc with the XML declaration
        #we only take the first node (the "content" one)
        node = doc.firstChild #pylint: disable-msg=E1101
        return node.toxml().encode("utf-8")

    def parse_buffer(self,buf, start, end, name, doc,tag_stack) :
        """
        Parse the buffer and output an XML representation.

            @var buf  : the buffer to parse from start to end
            @var name : the name of the XML element and doc is the XML dom
            @tag_stack : the list of parsed tags
            
        """
        
        it     = start.copy()
        parent = doc.createElement(name)

        while (it.get_offset() < end.get_offset()) and (it.get_char() != '\0'):
            
            # If a tag begin, we will parse until the end
            if it.begins_tag() :
                
                # We take the tag with the highest priority
                # The last of the list is the highest priority
                ta_list = it.get_tags()
                ta      = ta_list.pop()
                
                #remove the tag (to avoid infinite loop)
                #buf.remove_tag(ta,startit,endit)
                #But we are modifying the buffer. So instead,
                #We put the tag in the stack so we remember it was
                #already processed.
                startit = it.copy()
                offset  = startit.get_offset()
                
                #a boolean to know if we have processed all tags here
                all_processed = False
                
                #Have we already processed a tag a this point ?
                if tag_stack.has_key(offset) :
                    #Have we already processed this particular tag ?
                    while (not all_processed) and ta.props.name in tag_stack[offset]:
                        #Yes, so we take another tag (if there's one)
                        if len(ta_list) <= 0 :
                            all_processed = True
                        else :
                            ta = ta_list.pop()
                else :
                    #if we process the first tag of this offset, we add an entry
                    tag_stack[offset] = []
                    
                #No tag to process, we are in the text mode
                if all_processed :
                    #same code below. Should we make a separate function ?
                    parent.appendChild(doc.createTextNode(it.get_char()))
                    it.forward_char()
                else :
                    #So now, we are in tag "ta"
                    #Let's get the end of the tag
                    it.forward_to_tag_toggle(ta)
                    endit   = it.copy()
                    tagname = ta.props.name
                    #Let's add this tag to the stack so we remember
                    #it's already processed
                    tag_stack[offset].append(tagname)
                    if ta.get_data('is_subtask') :
                        tagname = "subtask"
                        subt    = doc.createElement(tagname)
                        target  = ta.get_data('child')
                        subt.appendChild(doc.createTextNode(target))
                        parent.appendChild(subt)
                        parent.appendChild(doc.createTextNode("\n"))
                        it.forward_line()
                    elif ta.get_data('is_tag') :
                        #Recursive call !!!!! (we handle tag in tags)
                        child = self.parse_buffer(buf,startit,endit,"tag",doc,tag_stack)
                        parent.appendChild(child)
                    elif ta.get_data('is_indent') :
                        indent = buf.get_text(startit,endit)
                        if '\n' in indent :
                            parent.appendChild(doc.createTextNode('\n'))
                        it = endit
                    else :
                        #The link tag has noname but has "is_anchor" properties
                        if ta.get_data('is_anchor'): 
                            tagname = "link"
                        #Recursive call !!!!! (we handle tag in tags)
                        child = self.parse_buffer(buf,startit,endit,tagname,doc,tag_stack)
                        #handling special tags
                        if ta.get_data('is_anchor') :
                            child.setAttribute("target",ta.get_data('link'))
                        parent.appendChild(child)
            #else, we just add the text
            else :
                parent.appendChild(doc.createTextNode(it.get_char()))
                it.forward_char()
                
        #Finishing with an \n before closing </content>
        if name == "content" :
            last_val = parent.lastChild
            if last_val and last_val.nodeValue != '\n' :
                parent.appendChild(doc.createTextNode('\n'))
        #This function concatenate all the adjacent text node of the XML
        parent.normalize()
        return parent
        

######################## Deserializing ##################################

### Deserialize : put all in the TextBuffer
# This function signature is defined in PyGTK
class Unserializer :
    def __init__(self,taskview) :
        #We keep a reference to the original taskview
        #Not very pretty but convenient
        self.tv = taskview
    
    #Disabling pylint argument usage since we know we are not using all args
    def unserialize(self,register_buf, content_buf, ite, data, cr_tags, udata) : #pylint: disable-msg=W0613
        if data :
            element = xml.dom.minidom.parseString(data)
            success = self.parsexml(content_buf,ite,element.firstChild) #pylint: disable-msg=E1103
        else :
            success = self.parsexml(content_buf,ite,None)
        return success
        
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
            self.tv.apply_tag_tag(buff,tag,sm,em)
        
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
                            taglist2.append(text)
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
            self.insert_tag(buf,t,it)
            self.tv.insert_at_mark(buf,end,", ")
        buf.delete_mark(start)
        buf.delete_mark(end)
        return True

