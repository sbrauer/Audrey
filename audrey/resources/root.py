from pyramid.decorator import reify

class Root(object):

    # Developers extending Audrey should create their own subclass of Root
    # that overrides either the _collection_classes attribute or
    # the get_collection_classes() class method.
    # Either way, get_collection_classes() should return 
    # a sequence of Collection classes.

    _collection_classes = ()

    @classmethod
    def get_collection_classes(cls):
        return cls._collection_classes

    def __init__(self, request):
        self.request = request
        self.__name__ = ''
        self.__parent__ = None
        self._collection_classes_by_name = {}
        for coll_cls in self.get_collection_classes():
            coll_name = coll_cls._collection_name
            if coll_name in self._collection_classes_by_name:
                raise ValueError("Non-unique collection name: %s" % coll_name)
            self._collection_classes_by_name[coll_name] = coll_cls

    def get_child(self, name):
        child = None
        if name in self._collection_classes_by_name:
            child = self._collection_classes_by_name[name](self.request)
            child.__name__ = name
            child.__parent__ = self
        return child

    def __getitem__(self, name):
        child = self.get_child(name)
        if child is None:
            raise KeyError
        return child

    def get_child_names(self):
        return self._collection_classes_by_name.keys()

    def get_children(self):
        result = []
        for name in self.get_child_names():
            result.append(self[name])
        return result

    @reify
    def _mongo_db(self):
        settings = self.request.registry.settings
        return settings['mongo_conn'][settings['mongo_name']]

    def get_mongo_collection(self, coll_name):
        return self._mongo_db[coll_name]
    
    def get_elastic_connection(self):
        return self.request.registry.settings['elastic_conn']
    
    def get_elastic_index_name(self):
        return self.request.registry.settings['elastic_name']

    # FIXME: add search related stuff
