import gtk

#Take list of Tags and give the background color that should be applied
#The returned color might be None (in which case, the default is used)
def background_color(tags) :
    # Compute color
    my_color    = None
    color_count = 0.0
    color_dict  = {"red":0,"green":0,"blue":0}
    for my_tag in tags:
        my_color_str = my_tag.get_attribute("color")
        if my_color_str :
            my_color    = gtk.gdk.color_parse(my_color_str)
            color_count = color_count + 1
            color_dict["red"]   = color_dict["red"]   + my_color.red
            color_dict["green"] = color_dict["green"] + my_color.green
            color_dict["blue"]  = color_dict["blue"]  + my_color.blue
    if color_count != 0:
        red        = int(color_dict["red"]   / color_count)
        green      = int(color_dict["green"] / color_count)
        blue       = int(color_dict["blue"]  / color_count)
        brightness = (red+green+blue) / 3.0
        while brightness < 60000:
            red        = int( (red   + 65535) / 2)
            green      = int( (green + 65535) / 2)
            blue       = int( (blue  + 65535) / 2)
            brightness = (red+green+blue) / 3.0
        my_color = gtk.gdk.Color(red, green, blue).to_string()
    return my_color
