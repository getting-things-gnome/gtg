from datetime import date

#function to convert a string of the form YYYY-MM-DD
#to a date
def strtodate(stri) :
    toreturn = None
    zedate = []
    if stri :
        if '-' in stri :
            zedate = stri.split('-')
        elif '/' in stri :
            zedate = stri.split('/')
            
        if len(zedate) == 3 :
            y = zedate[0]
            m = zedate[1]
            d = zedate[2]
            if y.isdigit() and m.isdigit() and d.isdigit() :
                yy = int(y)
                mm = int(m)
                dd = int(d)
                #FIXME: we should catch exceptions here
                try :
                    toreturn = date(yy,mm,dd)
                except ValueError:
                    toreturn = None
    return toreturn
