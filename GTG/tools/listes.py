#Return a copy of the list and avoid a to keep the same object
#It handles multilple dimension matrix through recursion
def returnlist(liste) :
    if liste.__class__ is list :
        to_return = []
        for i in liste :
            elem = returnlist(i)
            to_return.append(elem)
    else :
        to_return = liste
    return to_return
