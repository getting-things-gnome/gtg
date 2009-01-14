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

        txt    = ""
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
                        it.forward_line()
                    elif ta.get_data('is_tag') :
                        #Recursive call !!!!! (we handle tag in tags)
                        child = self.parse_buffer(buf,startit,endit,"tag",doc,tag_stack)
                        parent.appendChild(child)
                    else :
                        #The link tag has noname but has "is_anchor" properties
                        if ta.get_data('is_anchor'): tagname = "link"
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
                
        #This function concatenate all the adjacent text node of the XML
        parent.normalize()
        return parent

