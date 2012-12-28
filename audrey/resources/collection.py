from bson.objectid import ObjectId
from audrey.exceptions import Veto
from collections import OrderedDict
import string

class Collection(object):
    """
    A set of Objects.  Corresponds to a MongoDB Collection (and 
    an ElasticSearch "type").

    Developers extending Audrey should create their own subclass(es) of 
    Collection that:

    * override class attribute :attr:`_collection_name`; this string is used
      for traversal to a Collection from Root, as the name of the MongoDB
      collection, and as the name of the ElasticSearch doctype.
    * override either the :attr:`_object_classes` class attribute or
      the :meth:`get_object_classes` class method.
      Either way, :meth:`get_object_classes` should return 
      a sequence of the :class:`audrey.resources.object.Object` classes
      that can be stored in this collection.

    If Mongo indexes are desired for the collection, override the class method
    :meth:`get_mongo_indexes`.

    If an ElasticSearch mapping is desired, override the class method :meth:`get_elastic_mapping`.

    If ElasticSearch indexing isn't desired, override the class attribute :attr:`_use_elastic` to ``False``.
    """

    _collection_name = 'base_collection'

    _object_classes = ()

    # Set this to False if you don't care about using ElasticSearch
    # for this collection.
    _use_elastic = True

    _ID_FIELD = '_id'

    # In Collection, users can't explicitly assign names to objects.
    # The ObjectIds automatically assigned by MongoDB are used as the __name__.
    _NAME_FIELD = _ID_FIELD

    @classmethod
    def get_object_classes(cls):
        """ Returns a sequence of the Object classes that this Collection
        manages.

        :rtype: sequence of :class:`audrey.resources.object.Object` classes
        """
        return cls._object_classes

    # Return a list of data about the desired Mongo indexes for this collection.
    # The list should contain two-item tuples with data to be passed
    # to pymongo's Collection.ensure_index() method.
    # The first item is the ensure_index key_or_list parm.
    # The second items is a dictionary that will be passed as kwargs.
    # See http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.ensure_index
    @classmethod
    def get_mongo_indexes(cls):
        """
        Return a list of data about the desired MongoDB indexes for this
        collection.  The first item of each tuple is the ensure_index
        ``key_or_list`` parm.  The second item of each tuple is a dictionary
        that will be passed as kwargs.

        :rtype: sequence of two-item tuples, each with the two parameters to be passed to a call to :meth:`pymongo.collection.Collection.ensure_index`

        The default implementation returns an empty list, meaning that no indexes will be ensured.
        """
        return []

    @classmethod
    def get_elastic_mapping(cls):
        """ Return a dictionary representing ElasticSearch mapping properties
        for this collection.
        Refer to http://www.elasticsearch.org/guide/reference/mapping/

        :rtype: dictionary
        """
        mapping = {}
        mapping['text'] = dict(type='string', include_in_all=True)
        mapping['_created'] = dict(type='date', format='dateOptionalTime', include_in_all=False)
        mapping['_modified'] = dict(type='date', format='dateOptionalTime', include_in_all=False)
        return mapping

    def __init__(self, request):
        self.request = request
        self._object_classes_by_type = OrderedDict()
        for obj_cls in self.get_object_classes():
            obj_type = obj_cls._object_type
            if obj_type in self._object_classes_by_type:
                raise ValueError("Non-unique object type: %s" % obj_type)
            self._object_classes_by_type[obj_type] = obj_cls

    def get_object_types(self):
        """ Return the ``_object_types`` that this collection manages.

        :rtype: list of strings
        """
        return [cls._object_type for cls in self.get_object_classes()]

    def get_object_class(self, object_type):
        """ Return the class that corresponds to the ``object_type`` string.

        :param object_type: name of an object type
        :type object_type: string
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
        """
        return self._object_classes_by_type.get(object_type)

    def get_mongo_collection(self):
        """ Return the MongoDB Collection for this collection.

        :rtype: :class:`pymongo.collection.Collection`
        """
        return self.__parent__.get_mongo_collection(self._collection_name)

    def get_elastic_connection(self):
        """ Return a connection to the ElasticSearch server.

        :rtype: :class:`pyes.es.ES`
        """
        return self.__parent__.get_elastic_connection()

    def get_elastic_index_name(self):
        """ Return the name of the ElasticSearch index.

        Note that all objects in an Audrey app will use the same Elastic
        index (the index name is analogous to a database name).
        This is just a convenience method that returns the name from the root.

        :rtype: string
        """
        return self.__parent__.get_elastic_index_name()

    def get_elastic_doctype(self):
        """ Return the ElasticSearch document type for this collection.

        Note that Audrey uses the ``_collection_name`` as the doctype.

        :rtype: string
        """
        return self._collection_name

    def construct_child_from_mongo_doc(self, doc):
        """ Given a MongoDB document (presumably from this collection),
        construct and return an Object.

        :param doc: a MongoDB document (such as returned by :meth:`pymongo.collection.Collection.find_one`)
        :type doc: dictionary
        :rtype: :class:`audrey.resources.object.Object`
        """
        obj = self._get_child_class_from_mongo_doc(doc)(self.request)
        obj.load_mongo_doc(doc)
        if self._NAME_FIELD == self._ID_FIELD:
            obj.__name__ = str(obj._id)
        obj.__parent__ = self
        return obj

    def _get_child_class_from_mongo_doc(self, doc):
        """ Given a MongoDB document (presumably from this collection),
        return the appropriate object class (which could be used
        to construct an Object from the document).

        :param doc: a MongoDB document (such as returned by :meth:`pymongo.collection.Collection.find_one`)
        :type doc: dictionary
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
        """
        classes = self.get_object_classes()
        if len(classes) == 1:
            # A homogenous collection (only one Object class).
            return classes[0]
        # Assume doc has a key '_object_type'.
        return self.get_object_class(doc['_object_type'])

    def has_child_with_id(self, id):
        """ Does this collection have a child with the given ``id``?

        :param id: an ObjectId
        :type id: :class:`bson.objectid.ObjectId`
        :rtype: boolean
        """
        doc = self.get_mongo_collection().find_one(dict(_id=id), fields=[])
        return doc is not None

    def get_child_by_id(self, id):
        """ Return the child object for the given ``id``.

        :param id: an ObjectId
        :type id: :class:`bson.objectid.ObjectId`
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
        """
        doc = self.get_mongo_collection().find_one(dict(_id=id))
        if doc is None:
            return None
        return self.construct_child_from_mongo_doc(doc)

    def _str_to_id(self, s):
        try:
            id = ObjectId(s)
        except:
            id = None
        return id

    def has_child_with_name(self, name):
        """ Does this collection have a child with the given ``name``?

        :param name: an object name
        :type name: string
        :rtype: boolean
        """
        id = self._str_to_id(name)
        if id:
            return self.has_child_with_id(id)
        else:
            return False

    def get_child_by_name(self, name):
        """ Return the child object for the given ``name``.

        :param name: an object name
        :type name: string
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
        """
        id = self._str_to_id(name)
        if id:
            return self.get_child_by_id(id)
        else:
            return None

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
        """ Query for children and return the total number of matching children
        and a list of the children (or a batch of children if the ``limit``
        parameter is non-zero).

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :param skip: number of documents to omit from start of result set
        :type skip: integer
        :param limit: maximum number of children to return
        :type limit: integer
        :rtype: dictionary with the keys:

                * "total" - an integer indicating the total number of children matching the query ``spec``
                * "items" - a sequence of :class:`audrey.resources.object.Object` instances
        """
        cursor = self.get_mongo_collection().find(spec=spec, sort=sort, skip=skip, limit=limit)
        total = cursor.count()
        items = []
        for doc in cursor:
            obj = self.construct_child_from_mongo_doc(doc)
            items.append(obj)
        return dict(total=total, items=items)

    def get_children(self, spec=None, sort=None, skip=0, limit=0):
        """ Return the children matching the query parameters.

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :param skip: number of documents to omit from start of result set
        :type skip: integer
        :param limit: maximum number of children to return
        :type limit: integer
        :rtype: a sequence of :class:`audrey.resources.object.Object` instances
        """
        return self.get_children_and_total(spec, sort, skip, limit)['items']

    def get_child(self, spec=None, sort=None):
        """ Return the first child matching the query parms.

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :rtype: :class:`audrey.resources.object.Object` or ``None``
        """
        children = self.get_children(spec, sort, skip=0, limit=1)
        if children:
            return children[0]
        return None

    def get_child_names_and_total(self, spec=None, sort=None, skip=0, limit=0):
        """ Query for children and return the total number of matching children
        and a list of the child names (or a batch of child names if the
        ``limit`` parameter is non-zero).

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :param skip: number of documents to omit from start of result set
        :type skip: integer
        :param limit: maximum number of children to return
        :type limit: integer
        :rtype: dictionary with the keys:

                * "total" - an integer indicating the total number of children matching the query ``spec``
                * "items" - a sequence of __name__ strings
        """
        fields = []
        if self._NAME_FIELD != self._ID_FIELD: fields.append(self._NAME_FIELD)
        cursor = self.get_mongo_collection().find(spec=spec, fields=fields, sort=sort, skip=skip, limit=limit)
        total = cursor.count()
        items = [str(r[self._NAME_FIELD]) for r in cursor]
        return dict(total=total, items=items)

    def get_child_names(self, spec=None, sort=None, skip=0, limit=0):
        """ Return the child names matching the query parameters.

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :param skip: number of documents to omit from start of result set
        :type skip: integer
        :param limit: maximum number of children to return
        :type limit: integer
        :rtype: a sequence of __name__ strings
        """
        return self.get_child_names_and_total(spec, sort, skip, limit)['items']

    def get_children_lazily(self, spec=None, sort=None):
        """ Return child objects matching the query parameters using a generator.
        Great when you want to iterate over a potentially large number of children
        and don't want to load them all into memory at once.

        :param spec: a MongoDB query spec (as used by :meth:`pymongo.collection.Collection.find`)
        :type spec: dictionary or ``None``
        :param sort: a MongoDB sort parameter
        :type sort: a list of (key, direction) tuples or ``None``
        :rtype: a generator of :class:`audrey.resources.object.Object` instances
        """
        cursor = self.get_mongo_collection().find(spec=spec, sort=sort)
        for doc in cursor:
            obj = self.construct_child_from_mongo_doc(doc)
            yield obj

    def veto_add_child(self, child):
        """ Check whether the collection will allow the given ``child``
        to be added.
        If there is some objection, return a string describing the objection.
        Else return ``None`` to indicate the child is OK.

        :param child: a child to be added to this collection
        :type child: :class:`audrey.resources.object.Object`
        :rtype: string or ``None``
        """
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

    def add_child(self, child, validate_schema=True):
        """ Add a child object to this collection.
        Note that this will ultimately call the child's :meth:`audrey.resources.object.Object.save` method, persisting it in Mongo (and indexing in Elastic).
        If ``validate_schema`` is ``True``, a :class:`colander.Invalid` exception may be raised if schema validation fails.

        :param child: a child to be added to this collection
        :type child: :class:`audrey.resources.object.Object`
        :param validate_schema: Should we validate the schema before adding the child?
        :type validate_schema: boolean
        """
        error = self.veto_add_child(child)
        if error: raise Veto(error)
        child.__parent__ = self
        child.save(validate_schema=validate_schema)
        if self._NAME_FIELD == self._ID_FIELD:
            # We assume Object.save() set the _id attribute.
            child.__name__ = str(child._id)

    def delete_child(self, child_obj):
        """ Remove a child object from this collection.

        :param child: a child to be added to this collection
        :type child: :class:`audrey.resources.object.Object`
        """
        child_obj._pre_delete()
        self.get_mongo_collection().remove(dict(_id=child_obj._id), safe=True)

    def delete_child_by_name(self, name):
        """ Remove a child object (identified by the given ``name``) from this collection.

        :param name: name of the child to remove
        :type name: string
        :rtype: integer indicating number of children removed.  Should be 1 normally, but may be 0 if no child was found with the given ``name``.
        """
        child = self.get_child_by_name(name)
        if child:
            self.delete_child(child)
            return 1
        else:
            return 0

    def delete_child_by_id(self, id):
        """ Remove a child object (identified by the given ``id``) from this collection.

        :param name: ID of the child to remove
        :type name: :class:`bson.objectid.ObjectId`
        :rtype: integer indicating number of children removed.  Should be 1 normally, but may be 0 if no child was found with the given ``id``.
        """
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

class NamingCollection(Collection):
    """ A subclass of :class:`Collection` that allows control over the
    ``__name__`` attribute.
    """

    _collection_name = 'naming_collection'

    _NAME_FIELD = '__name__'

    @classmethod
    def get_mongo_indexes(cls):
        indexes = Collection.get_mongo_indexes()
        indexes.append(([(cls._NAME_FIELD, 1)], dict(unique=True)))
        return indexes

    @classmethod
    def get_elastic_mapping(cls):
        mapping = Collection.get_elastic_mapping()
        mapping[cls._NAME_FIELD] = dict(type='string', include_in_all=False, index='not_analyzed')
        return mapping

    def has_child_with_name(self, name):
        doc = self.get_mongo_collection().find_one({self._NAME_FIELD: name}, fields=[])
        return doc is not None

    def get_child_by_name(self, name):
        doc = self.get_mongo_collection().find_one({self._NAME_FIELD: name})
        if doc is None:
            return None
        return self.construct_child_from_mongo_doc(doc)

    def validate_name_format(self, name):
        """ Is the given name in an acceptable format?
        If so, return ``None``.  Otherwise return an error string
        explaining the problem.

        :param name: name of a child object
        :type name: string
        :rtype: string or ``None``

        The default implementation of this method always returns ``None``.
        If you want to restrict the format of names (legal characters, etc)
        override this method to check the name and return an error if needed.
        
        Note that this method doesn't have to test whether
        the name is empty or already in use.
        """
        return None

    def veto_child_name(self, name, unique=True):
        """ Check whether the collection will allow a child with the given
        ``name`` to be added.
        If there is some objection, return a string describing the objection.
        Else return ``None`` to indicate the child name is OK.

        :param name: name of a child object
        :type name: string
        :param unique: Should we check that the name is unique (not already in use)?
        :type unique: boolean
        :rtype: string or ``None``
        """
        if name is not None: name = name.strip()
        if not name: return "Name may not be empty."
        err = self.validate_name_format(name)
        if err: return err
        if unique and self.has_child_with_name(name): return "The name \"%s\" is already in use." % name
        return None

    def veto_add_child(self, child):
        err = Collection.veto_add_child(self, child)
        if err: return err
        return self.veto_child_name(child.__name__)

    def rename_child(self, name, newname, validate=True):
        """ Rename a child of this collection.
        May raise a :class:`audrey.exceptions.Veto` exception if
        ``validate`` is ``True`` and the ``newname`` is vetoed.

        :param name: name of the child to rename
        :type name: string
        :param newname: new name for the child
        :type newname: string
        :param validate: Should we validate the new name first?
        :type validate: boolean
        :rtype: integer indicating number of children renamed.  Should be 1 normally, but may be 0 if ``newname`` == ``name``.
        """
        if name == newname: return 0
        if validate:
            error = self.veto_child_name(newname)
            if error: raise Veto(error)
        child = self.get_child_by_name(name)
        if child is None:
            raise KeyError, "No such child %r" % name
        child.__name__ = newname
        child.save()
        return 1
