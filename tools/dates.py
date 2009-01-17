from datetime import date

#function to convert a string of the form YYYY-MM-DD
#to a date
def strtodate(stri) :
    if stri :
        y,m,d = stri.split('-')
        if y and m and d :
            return date(int(y),int(m),int(d))
        else :
            y,m,d = stri.split('/')
            if y and m and d :
                return date(int(y),int(m),int(d))
    return None
