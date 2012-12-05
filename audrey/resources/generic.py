class TraversableDict(object):
    def __init__(self, a_dict):
        self._data = a_dict

    def __getitem__(self, name):
        try:
            return make_traversable(self._data.__getitem__(name), name, self)
        except:
            raise KeyError

class TraversableSeq(object):
    def __init__(self, a_list):
        self._data = a_list

    def __getitem__(self, name):
        try:
            return make_traversable(self._data[int(name)], name, self)
        except:
            raise KeyError

def make_traversable(obj, name, parent):
    ret = obj
    if type(obj) is dict:
        ret = TraversableDict(obj)
    elif type(obj) in (set, list):
        ret = TraversableSeq(obj)
    ret.__name__ = name
    ret.__parent__ = parent
    return ret
