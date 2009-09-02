class BijectiveFunction:
    """A simple class that implements the concept \
            of bijection between two lists"""
    __left = None
    __right = None

    def __init__(self, left =[], right = []):
        self.__checkEqualLen(right, left)
        self.__left = left
        self.__right = right

    def rightFind(self, f):
        id = self.__findId(f, self.__right)
        if id != None:
            return self.__left[id]

    def leftFind(self, f):
        id = self.__findId(f, self.__left)
        if id != None:
            return self.__right[id]

    def rightFindElem(self, elem):
        return self.rightFind(lambda x: x == elem)

    def leftFindElem(self, elem):
        return self.leftFind(lambda x: x == elem)

    def append(self, right, left):
        self.__checkEqualLen(right, left)
        self.__right.append(right)
        self.__left.append(left)

    def __findId(self, f, seq):
        """Return first sequence number in sequence where f(item) == True."""
        for id in xrange(len(seq)):
            if f(seq[id]):
                return id
        return None

    def __checkEqualLen(self, left, right):
        #TODO: write this
        pass

    def __str__(self):
        return zip(self.__left, self.__right).__str__()
