from bson.objectid import ObjectId
from audrey.exceptions import Veto
import string

class BaseCollection(object):

    # Developers extending Audrey should create their own subclass(es) of 
    # BaseCollection that:
    # - override _collection_name; this string is used for traversal
    #   to a Collection from Root, as the name of the MongoDB collection,
    #   and as the name of the ElasticSearch doctype.
    # - override either the _object_classes attribute or
    #   the get_object_classes() class method.
    #   Either way, get_object_classes() should return 
    #   a sequence of Object classes stored in this collection.
    # - override _use_elastic = False, if Elastic indexing isn't desired.
    # If Mongo indexes or Elastic mappings are desired, override
    # get_mongo_indexes() and/or get_elastic_mapping().

    _collection_name = 'base_collection'

    _object_classes = ()

    # Set this to False if you don't care about using ElasticSearch
    # for this collection.
    _use_elastic = True

    _ID_FIELD = '_id'

    # In BaseCollection, users can't explicitly assign names to objects.
    # The ObjectIds automatically assigned by MongoDB are used as the __name__.
    _NAME_FIELD = _ID_FIELD

    @classmethod
    def get_object_classes(cls):
        return cls._object_classes

    # Return a list of data about the desired Mongo indexes for this collection.
    # The list should contain two-item tuples with data to be passed
    # to pymongo's Collection.ensure_index() method.
    # The first item is the ensure_index key_or_list parm.
    # The second items is a dictionary that will be passed as kwargs.
    # See http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.ensure_index
    @classmethod
    def get_mongo_indexes(cls):
        return []

    # Return a dictionary representing ElasticSearch mapping properties
    # for this collection.
    # See http://www.elasticsearch.org/guide/reference/mapping/
    @classmethod
    def get_elastic_mapping(cls):
        mapping = {}
        mapping['text'] = dict(type='string', include_in_all=True)
        mapping['_created'] = dict(type='date', format='dateOptionalTime', include_in_all=False)
        mapping['_modified'] = dict(type='date', format='dateOptionalTime', include_in_all=False)
        return mapping

    def __init__(self, request):
        self.request = request
        self._object_classes_by_type = {}
        for obj_cls in self.get_object_classes():
            obj_type = obj_cls._object_type
            if obj_type in self._object_classes_by_type:
                raise ValueError("Non-unique object type: %s" % obj_type)
            self._object_classes_by_type[obj_type] = obj_cls

    def get_mongo_collection(self):
        return self.__parent__.get_mongo_collection(self._collection_name)

    def get_elastic_connection(self):
        return self.__parent__.get_elastic_connection()

    def get_elastic_index_name(self):
        return self.__parent__.get_elastic_index_name()

    def get_elastic_doctype(self):
        return self._collection_name

    def construct_child_from_mongo_doc(self, doc):
        #obj = self._get_child_class_from_mongo_doc(doc)(self.request, **doc)
        obj = self._get_child_class_from_mongo_doc(doc)(self.request)
        obj.load_mongo_doc(doc)
        obj.__name__ = self._get_child_name_from_mongo_doc(doc)
        obj.__parent__ = self
        return obj

    # For homogenous collections (ones that store only one Object class)
    # the following implementation is fine.
    # For non-homogenous collections, a developer should make sure that 
    # the documents stored in Mongo have some data that identifies what
    # Object class should be used to construct instances, and override
    # this method to return the appropriate class for a given document.
    # return self._object_classes_by_type.get(obj_type)
    def _get_child_class_from_mongo_doc(self, doc):
        classes = self.get_object_classes()
        if classes: return classes[0]
        return None

    def _get_child_name_from_mongo_doc(self, doc):
        return str(doc[self._NAME_FIELD])

    def _get_mongo_query_spec_for_id(self, id):
        return {self._ID_FIELD: ObjectId(id)}

    def _get_mongo_query_spec_for_name(self, name):
        return self._get_mongo_query_spec_for_id(name)

    def has_child_with_id(self, id):
        doc = self.get_mongo_collection().find_one(self._get_mongo_query_spec_for_id(id), fields=[])
        return doc is not None

    def get_child_by_id(self, id):
        doc = self.get_mongo_collection().find_one(self._get_mongo_query_spec_for_id(id))
        if doc is None:
            return None
        return self.construct_child_from_mongo_doc(doc)

    def has_child_with_name(self, name):
        doc = self.get_mongo_collection().find_one(self._get_mongo_query_spec_for_name(name), fields=[])
        return doc is not None

    def get_child_by_name(self, name):
        doc = self.get_mongo_collection().find_one(self._get_mongo_query_spec_for_name(name))
        if doc is None:
            return None
        return self.construct_child_from_mongo_doc(doc)

    def __getitem__(self, name):
        child = self.get_child_by_name(name)
        if child is None:
            raise KeyError
        return child

    ###
    # In the following get_child...() methods, spec and sort parameters
    # should follow the conventions for those same parameters for 
    # pymongo's Collection.find() method.
    # http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.find
    ###

    def get_children_and_total(self, spec=None, sort=None, skip=0, limit=0):
        cursor = self.get_mongo_collection().find(spec=spec, sort=sort, skip=skip, limit=limit)
        total = cursor.count()
        items = []
        for doc in cursor:
            obj = self.construct_child_from_mongo_doc(doc)
            items.append(obj)
        return dict(total=total, items=items)

    def get_children(self, spec=None, sort=None, skip=0, limit=0):
        return self.get_children_and_total(spec, sort, skip, limit)['items']

    def get_child_names_and_total(self, spec=None, sort=None, skip=0, limit=0):
        fields = []
        if self._NAME_FIELD != self._ID_FIELD: fields.append(self._NAME_FIELD)
        cursor = self.get_mongo_collection().find(spec=spec, fields=fields, sort=sort, skip=skip, limit=limit)
        total = cursor.count()
        items = [str(r[self._NAME_FIELD]) for r in cursor]
        return dict(total=total, items=items)

    def get_child_names(self, spec=None, sort=None, skip=0, limit=0):
        return self.get_child_names_and_total(spec, sort, skip, limit)['items']

    def get_children_lazily(self, spec=None, sort=None):
        """ Return child objects using a generator.
        Great when you want to iterate over a potentially large number of children
        and don't want to load them all into memory at once.
        """
        cursor = self.get_mongo_collection().find(spec=spec, sort=sort)
        for doc in cursor:
            obj = self.construct_child_from_mongo_doc(doc)
            yield obj

    def veto_add_child(self, child):
        type_ok = False
        for cls in self.get_object_classes():
            if isinstance(child, cls):
                type_ok = True
                break
        if type_ok: return None
        if hasattr(child, '_object_type'):
            child_type = child._object_type
            collection_type = self._collection_name
        else:
            child_type = str(child.__class__)
            collection_type = str(self.__class__)
        return "Cannot add %s to %s." % (child_type, collection_type)

    # Note that the add_child() method calls the child's save() method,
    # persisting it in Mongo (and indexing in Elastic).
    def add_child(self, child):
        error = self.veto_add_child(child)
        if error: raise Veto(error)
        child.__parent__ = self
        child.save()
        if self._NAME_FIELD == self._ID_FIELD:
            # We assume BaseObject.save() set the _id attribute.
            child.__name__ = str(child._id)

    def delete_child(self, child_obj):
        child_obj._pre_delete()
        self.get_mongo_collection().remove(dict(_id=child_obj._id), safe=True)

    def delete_child_by_name(self, name):
        # Returns the number of children deleted (0 or 1).
        child = self.get_child_by_name(name)
        if child:
            self.delete_child(child)
            return 1
        else:
            return 0

    def delete_child_by_id(self, id):
        # Returns the number of children deleted (0 or 1).
        child = self.get_child_by_id(id)
        if child:
            self.delete_child(child)
            return 1
        else:
            return 0

    def _clear_elastic(self):
        """ Delete all documents from Elastic for this Collection's doctype.
        """
        self.get_elastic_connection().delete(self.get_elastic_index_name(), self.get_elastic_doctype(), None)

    # Returns the number of objects indexed.
    def _reindex_all(self, clear=False):
        if clear:
            self._clear_elastic()
        count = 0
        if self._use_elastic:
            for child in self.get_children_lazily():
                child.index()
                count += 1
        return count

class NamingCollection(BaseCollection):

    _collection_name = 'naming_collection'

    _NAME_FIELD = '__name__'

    @classmethod
    def get_mongo_indexes(cls):
        indexes = BaseCollection.get_mongo_indexes(cls)
        indexes.append(([('__name__', pymongo.ASCENDING)], dict(unique=True)))

    @classmethod
    def get_elastic_mapping(cls):
        mapping = BaseCollection.get_elastic_mapping(cls)
        mapping['__name__'] = dict(type='string', include_in_all=False, index='not_analyzed')
        return mapping

    def _get_mongo_query_spec_for_name(self, name):
        return {self._NAME_FIELD: name}

    # If you want to restrict the format of names (legal characters, etc)
    # override this method to return an error msg if the name doesn't 
    # match your conventions.  Else return None.
    # Note that this method doesn't have to (and shouldn't) test whether
    # the name is already in use.
    def validate_name_format(self, name):
        return None

    def veto_child_name(self, name, unique=True):
        if name is not None: name = name.strip()
        if not name: return "Name may not be blank."
        err = self.validate_name_format(name)
        if err: return err
        if unique and self.has_child_with_name(name): return "The name \"%s\" is already in use." % name
        return None

    def veto_add_child(self, child):
        err = BaseCollection.veto_add_child(child)
        if err: return err
        return self.veto_child_name(child.__name__)

    def rename_child(self, name, newname, _validate=True):
        # Returns the number of children renamed (0 or 1).
        if name == newname: return 0
        if _validate:
            error = self.veto_child_name(newname)
            if error: raise Veto(error)
        child = self.get_child_by_name(name)
        if child:
            child.__name__ = newname
            child.save()
            return 1
        else:
            return 0
