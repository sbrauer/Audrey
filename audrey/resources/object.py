import datetime
import hashlib
from pprint import pformat
import colander
from bson.dbref import DBRef
from bson.objectid import ObjectId
from pyramid.traversal import find_root
import pyes
from audrey import dateutil
from audrey.htmlutil import html_to_text
from audrey.resources.file import File
from audrey.resources.reference import Reference
from audrey.resources.generic import make_traversable
import audrey.types

GRIDFS_COLLECTION = "fs"

class Object(object):
    """ Base class for objects that can be stored in MongoDB and
    indexed in ElasticSearch.

    Developers extending Audrey should create their own subclass(es) of 
    Object that:

    * override class attribute :attr:`_object_type`; this string should uniquely identify the Object type within the context of an Audrey application
    * override class method :meth:`get_class_schema` to return a colander schema for the type.
    * override :meth:`get_title` to return a suitable title string for an
      instance of the type.

    If the type has some non-schema attributes that you store in Mongo,
    override :meth:`get_nonschema_values` and :meth:`set_nonschema_values`.
    When overriding, be sure to call the superclass methods since the base
    ``Object`` type uses these methods for metadata (``_id``, ``_created``, etc).
    """

    _object_type = "object"
    @classmethod
    def get_class_schema(cls, request=None):
        """
        Return a colander schema describing the user-editable
        attributes for this Object type.

        :param request: the current request, possibly None
        :type request: :class:`pyramid.request.Request`
        :rtype: :class:`colander.SchemaNode`

        If a ``request`` is passed, you may opt to use it to get access
        to various interesting bits of data like the current user, a context
        object, etc.  You could use that to set default values, vocabulary
        lists, etc.  If you do so, just make sure that you still return
        a reasonable schema even when ``request`` is ``None``.

        Audrey makes use of the following custom :class:`SchemaNode` kwargs
        for :class:`colander.String` nodes:

        * ``include_in_text``: boolean, defaults to True; if True, the value will be included in Elastic's full text index.
        * ``is_html``: boolean, defaults to False; if True, the value will be stripped of html markup before being indexed in Elastic.
        """
        return colander.SchemaNode(colander.Mapping())

    # Should this Object use Elastic?
    # Note that this setting only matters if the Collection's _use_elastic=True.
    _use_elastic = True

    # kwargs should be a dictionary of attribute names and values
    # The values should be "demongified".
    def __init__(self, request, **kwargs):
        """
        Construct an Object instance.

        :param request: :class:`pyramid.request.Request` instance for the
        current request
        :param kwargs: If present, ``kawrgs`` should be a dictionary of
        attribute names and values to set on the new instance.
        """
        self.request = request
        self.set_schema_values(**kwargs)
        self.set_nonschema_values(**kwargs)

    def use_elastic(self):
        """
        Should this object use ElasticSearch for indexing?

        Returns ``True`` if both the ``Object`` class and the 
        ``Collection`` class have the class attribute ``_use_elastic``
        set to ``True``.

        :rtype: boolean
        """
        assert getattr(self, '__parent__', None), "parentless child!"
        return self._use_elastic and self.__parent__._use_elastic

    def get_schema(self):
        """ Return the colander schema for this ``Object`` type.

        :rtype: :class:`colander.SchemaNode`
        """
        # As an optimization, only generate the schema once per request.
        if not hasattr(self, '__schema__'):
            self.__schema__ = self.get_class_schema(self.request)
        return self.__schema__

    def get_schema_names(self):
        """ Return the names of the top-level schema nodes.

        :rtype: list of strings
        """
        return [node.name for node in self.get_schema().children]

    def get_nonschema_values(self):
        """ Get the names and values of "non-schema" attributes.

        :rtype: dictionary with the keys:

                * "_id": ObjectId or None
                * "_created": datetime.datetime (UTC) or None
                * "_modified": datetime.datetime (UTC) or None
                * "_etag": string or None
        """
        values = {}
        values['_id'] =  getattr(self, '_id', None)
        values['_created'] = getattr(self, '_created', None)
        values['_modified'] = getattr(self, '_modified', None)
        values['_etag'] = getattr(self, '_etag', None)
        return values

    def set_nonschema_values(self, **kwargs):
        """ Set this instance's non-schema values from ``kwargs``.
        """
        self._id = kwargs.get('_id') # mongodb id
        self._created = kwargs.get('_created')
        self._modified = kwargs.get('_modified')
        self._etag = kwargs.get('_etag')

    def set_schema_values(self, **kwargs):
        """ Set attribute values for the top-level schema nodes
        present in ``kawrgs``.
        """
        for name in self.get_schema_names():
            if kwargs.has_key(name):
                setattr(self, name, kwargs[name])

    def set_all_schema_values(self, **kwargs):
        """ Set attribute values from ``kwargs`` for **all**
        top-level schema nodes.  Schema nodes that are missing
        in ``kwargs`` will be set to ``None``.
        """
        for name in self.get_schema_names():
            setattr(self, name, kwargs.get(name, None))

    def get_schema_values(self):
        """ Return a dictionary of this object's schema names and values.

        :rtype: dictionary
        """
        values = {}
        for name in self.get_schema_names():
            values[name] = getattr(self, name, None)
        return values

    def get_all_values(self):
        """ Returns a dictionary of both schema and nonschema values.

        :rtype: dictionary
        """
        vals = self.get_nonschema_values()
        vals.update(self.get_schema_values())
        return vals

    def get_mongo_collection(self):
        """ Return the MongoDB Collection that contains this object's document.

        :rtype: :class:`pymongo.collection.Collection`
        """
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_mongo_collection()

    def get_elastic_connection(self):
        """ Return a connection to the ElasticSearch server.

        :rtype: :class:`pyes.es.ES`
        """
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_connection()

    def get_elastic_index_name(self):
        """ Return the name of the ElasticSearch index for this object.

        Note that all objects in an Audrey app will use the same Elastic
        index (the index name is analogous to a database name).
        This is just a convenience method that returns the name from the root.

        :rtype: string
        """
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_index_name()

    def get_elastic_doctype(self):
        """ Return the ElasticSearch document type for this object.

        Note that Audrey uses Collection names as the Elastic doctype.
        This is just a convenience method that returns the type
        from the collection.

        :rtype: string
        """
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_doctype()

    def get_mongo_save_doc(self):
        """ Returns a dictionary representing this object suitable
        for saving in MongoDB.

        :rtype: dictionary
        """
        doc = _mongify_values(self.get_all_values())
        if doc['_id'] is None:
            del doc['_id']
        return doc

    def __str__(self):
        """ Returns a pretty-printed string of this object's values.

        :rtype: string
        """
        return pformat(self.get_all_values())

    def get_title(self):
        """ Return a "title" for this object.
        This should ideally be a human-friendly string such as might
        be displayed as the text of a link to the object.

        The default implementation boringly returns the object's
        ``__name__`` or "Untitled".

        :rtype: string
        """
        return self.__name__ or 'Untitled'

    def get_all_files(self):
        """ Returns a list of all the File objects that this object
        refers to (via schema or non-schema attributes).

        :rtype: list of :class:`audrey.resources.file.File` instances
        """
        return _find_files(self.get_all_values()).values()

    def get_all_references(self):
        """ Returns a list of all the Reference objects that this object
        refers to (via schema or non-schema attributes).

        :rtype: list of :class:`audrey.resources.reference.Reference` objects
        """
        return _find_references(self.get_all_values()).values()

    def get_all_referenced_objects(self):
        """ Returns a list of all the Objects that this object refers
        to (via schema or non-schema attributes).

        :rtype: list of :class:`Object` instances
        """
        ret = []
        root = find_root(self)
        for ref in self.get_all_references():
            obj = root.get_object_for_reference(ref)
            if obj is not None:
                ret.append(obj)
        return ret

    def save(self, validate_schema=True, index=True, set_modified=True, set_etag=True):
        """
        Save this object in MongoDB (and optionally ElasticSearch).

        :param validate_schema: Should the colander schema be validated first?  If ``True``, may raise :class:`colander.Invalid`.
        :type validate_schema: boolean
        :param index: Should the object be (re-)indexed in ElasticSearch?
        :type index: boolean
        :param set_modified: Should the object's last modified timestamp (``_modified``) be updated?
        :type set_modified: boolean
        :param set_etag: Should the object's Etag be updated?
        :type set_etag: boolean
        """
        if validate_schema:
            self.validate_schema() # May raise a colander.Invalid exception
        if set_modified:
            self._modified = dateutil.utcnow()
            if not getattr(self, '_created', None): self._created = self._modified
        if set_etag:
            self._etag = self.generate_etag()

        # Determine all the GridFS file ids that this object
        # now refers to and used to refer to.
        root = find_root(self)
        fs_files_coll = root.get_gridfs()._GridFS__files
        new_file_ids = set([x._id for x in self.get_all_files()])
        old_file_ids = set()
        if self._id:
            dbref = self.get_dbref()
            for item in fs_files_coll.find({'parents':dbref}, fields=[]):
                old_file_ids.add(item['_id'])

        # Persist the object in Mongo.
        doc = self.get_mongo_save_doc()
        id = self.get_mongo_collection().save(doc, safe=True)
        if not self._id:
            self._id = id
            dbref = self.get_dbref()

        # Update GridFS file "parents".
        ids_to_remove = old_file_ids - new_file_ids
        ids_to_add = new_file_ids - old_file_ids
        if ids_to_remove:
            fs_files_coll.update({'_id':{'$in':list(ids_to_remove)}}, {"$pull":{"parents":dbref}, "$set":{"lastmodDate": dateutil.utcnow()}}, multi=True)
        if ids_to_add:
            fs_files_coll.update({'_id':{'$in':list(ids_to_add)}}, {"$addToSet":{"parents":dbref}, "$set":{"lastmodDate": dateutil.utcnow()}}, multi=True)

        if index: self.index()

    def generate_etag(self):
        """ Compute an Etag based on the object's schema values.

        :rtype: string
        """
        h = hashlib.new('md5')
        h.update(str(self.get_schema_values()))
        return h.hexdigest()

    def validate_schema(self):
        """ Runs the instance's schema attribute values
        thru a serialize-deserialize roundtrip.
        This will raise a :class:`colander.Invalid` exception if the
        schema fails to validate.
        Otherwise it will have the effect of applying ``default`` and
        ``missing`` values.
        """
        schema = self.get_schema()
        data = schema.deserialize(schema.serialize(self.get_schema_values()))
        self.set_schema_values(**data)

    def load_mongo_doc(self, doc):
        """ Update the object's attribute values using values from ``doc``.

        Note that as appropriate, ObjectIds and DBRefs will be converted
        to :class:`audrey.resources.reference.Reference` or :class:`audrey.resources.file.File` instances.

        :param doc: a MongoDB document (such as returned by :meth:`pymongo.collection.Collection.find_one`)
        :type doc: dictionary
        """
        clean = _demongify_values(doc)
        self.set_nonschema_values(**clean)
        clean = _apply_schema_to_values(self.get_schema(), clean)
        self.set_schema_values(**clean)

    def get_dbref(self, include_database=False):
        """ Return a DBRef for this object.

        :param include_database: Should the database name be included in the DBRef?
        :type include_database: boolean
        :rtype: :class:`bson.dbref.DBRef`
        """
        coll = self.get_mongo_collection()
        dbname = None
        if include_database:
            dbname = coll.database.name 
        return DBRef(coll.name, self._id, dbname)

    def _pre_delete(self):
        # Remove from ElasticSearch
        self.unindex()
        # Update parents attribute of related GridFS files
        dbref = self.get_dbref()
        root = find_root(self)
        fs_files_coll = root.get_gridfs()._GridFS__files
        fs_files_coll.update({'parents':dbref}, {"$pull":{"parents":dbref}, "$set":{"lastmodDate": dateutil.utcnow()}}, multi=True)

    def index(self):
        """ Index (or reindex) this object in ElasticSearch.

        Note that this is a no-op when :meth:`use_elastic` is ``False``.
        """
        if not self.use_elastic(): return
        doc = self.get_elastic_index_doc()
        self.get_elastic_connection().index(doc, self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))
        self.get_elastic_connection().refresh(self.get_elastic_index_name())

    def unindex(self):
        """ Unindex this object in ElasticSearch.

        :rtype: integer

        Returns the number of items affected (normally this will
        be 1, but it may be 0 if :meth:`use_elastic` is ``False`` or
        if the object wasn't indexed to begin with).
        """
        if not self.use_elastic(): return 0
        try:
            self.get_elastic_connection().delete(self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))
            self.get_elastic_connection().refresh(self.get_elastic_index_name())
            return 1
        except pyes.exceptions.NotFoundException, e:
            return 0

    def get_elastic_index_doc(self):
        """ Returns a dictionary representing this object suitable
        for indexing in ElasticSearch.

        :rtype: dictionary
        """
        return dict(
            _created = self._created,
            _modified = self._modified,
            text = self.get_fulltext_to_index(),
        )

    def get_fulltext_to_index(self):
        """ Returns a string containing the "full text" for this object.

        Text is found by walking over the schema values looking for 
        :class:`colander.String` nodes that don't have the attribute
        ``include_in_text`` set to ``False``. (If the attribute is missing,
        it defaults to ``True``.)

        If the schema node has the attribute ``is_html`` set to ``True``,
        the text value will be stripped of HTML markup.  (If the attribute
        is missing, it defaults to ``False``.)

        :rtype: string
        """
        return '\n'.join(self._get_text_values_for_schema_node(self.get_schema(), self.get_schema_values()))

    def _get_text_values_for_schema_node(self, node, value):
        result = []
        if not value: return result
        if type(node.typ) == colander.Mapping:
            for cnode in node.children:
                name = cnode.name
                val = value.get(name, None)
                if val:
                    result += self._get_text_values_for_schema_node(cnode, val)
        elif type(node.typ) == colander.Sequence:
            if node.children:
                cnode = node.children[0]
                for val in value:
                    result += self._get_text_values_for_schema_node(cnode, val)
        elif type(node.typ) == colander.Tuple:
            for (idx, cnode) in enumerate(node.children):
                result += self._get_text_values_for_schema_node(cnode, value[idx])
        elif type(node.typ) == colander.String:
            if getattr(node, 'include_in_text', True):
                if getattr(node, 'is_html', False):
                    value = html_to_text(value, 0)
                if value: result.append(value)
        #elif type(node.typ) == deform.FileData:
        #    pass # FIXME: handle PDF, Word, etc?
        return result

    # Allow traversal to File attributes
    def __getitem__(self, name):
        if hasattr(self, name):
            val = getattr(self, name)
            if val is not None:
                return make_traversable(val, name, self)
        raise KeyError

    def dereference(self, reference):
        """ Return the object referred to by ``reference``.

        :param reference: a reference
        :type reference: :class:`audrey.resources.reference.Reference` or ``None``
        :rtype: :class:`Object` or ``None``
        """
        # Try to get the object referred to by reference (a Reference).
        if reference is None:
            return None
        return reference.dereference(self)

class NamedObject(Object):
    """ A subclass of :class:`Object` that has an editable ``__name__`` 
    attribute.
    """

    def __init__(self, request, **kwargs):
        self.__name__ = None
        Object.__init__(self, request, **kwargs)

    def get_nonschema_values(self):
        """ Get the names and values of "non-schema" attributes.

        :rtype: dictionary with the same keys as returned by :meth:`Object.get_nonschema_values` plus:

        * "__name__": string or None
        """
        values = Object.get_nonschema_values(self)
        values['__name__'] = self.__name__
        return values

    def set_nonschema_values(self, **kwargs):
        Object.set_nonschema_values(self, **kwargs)
        self.__name__ = kwargs.get('__name__')

    def get_elastic_index_doc(self):
        result = Object.get_elastic_index_doc(self)
        result['__name__'] = self.__name__
        return result

# Crawl over node and make sure all types are compatible with pymongo.
def _mongify_values(node):

    # Pymongo can't handle date objects (without time), so coerce all dates to datetimes.
    if type(node) is datetime.date:
        return datetime.datetime.combine(node, datetime.time())

    # Store a pseudo-DBRef for instances of our File class.
    # I say "pseudo" because it won't dereference properly
    # due to the collection name (while "fs.files" would dereference).
    # However our intent is not to use it as a normal DBRef but 
    # instead as a way to recognize ObjectIds referring to GridFS files.
    if type(node) is File:
        return DBRef(GRIDFS_COLLECTION, node._id)

    # Serialize DBRef or bare ObjectId.
    if type(node) is Reference:
        return node.to_mongo()

    # Pymongo can't handle sets, so coerce to lists.
    if type(node) is set:
        node = list(node)

    if type(node) == dict:
        results = {}
        for (key, value) in node.items():
            results[key] = _mongify_values(value)
        return results
    elif type(node) == list:
        return [_mongify_values(item) for item in node]
    else:
        return node

def _demongify_values(node):
    # datetimes from PyMongo have tzinfo=<bson.tz_util.FixedOffset>
    # but we'd prefer <UTC>.
    if type(node) is datetime.datetime:
        return dateutil.make_aware(node)

    if type(node) is DBRef:
        if node.collection == GRIDFS_COLLECTION:
            return File(node.id)

    if type(node) == dict:
        results = {}
        for (key, value) in node.items():
            results[key] = _demongify_values(value)
        return results
    elif type(node) == list:
        return [_demongify_values(item) for item in node]
    else:
        return node

# Crawl over node looking for File instances.
# Return a dict of all File instances keyed by ObjectId.
def _find_files(node):
    ret = {}
    if type(node) is File:
        ret[node._id] = node
    elif type(node) == dict:
        for value in node.values():
            ret.update(_find_files(value))
    elif type(node) in (set, list):
        for value in node:
            ret.update(_find_files(value))
    return ret

# Crawl over node looking for Reference instances.
# Return a dict of all Reference instances keyed by ObjectId.
def _find_references(node):
    ret = {}
    if type(node) is Reference:
        ret[node.id] = node
    elif type(node) == dict:
        for value in node.values():
            ret.update(_find_references(value))
    elif type(node) in (set, list):
        for value in node:
            ret.update(_find_references(value))
    return ret

def _apply_schema_to_values(node, value):
    if value is None: return None
    if type(node.typ) == colander.Mapping:
        ret = {}
        for cnode in node.children:
            name = cnode.name
            val = value.get(name, None)
            ret[name] = _apply_schema_to_values(cnode, val)
        return ret
    elif type(node.typ) == colander.Sequence:
        ret = []
        if node.children:
            cnode = node.children[0]
            for val in value:
                ret.append(_apply_schema_to_values(cnode, val))
        return ret
    elif type(node.typ) == colander.Tuple:
        ret = []
        for (idx, cnode) in enumerate(node.children):
            ret.append(_apply_schema_to_values(cnode, value[idx]))
        return tuple(ret)
    # Convert DBRefs and base ObjectIds to Audrey's Reference type.
    elif type(node.typ) == audrey.types.Reference:
        if node.typ.collection:
            id = None
            if type(value) is ObjectId:
                id = value
            elif type(value) is DBRef:
                if value.collection != note.type.collection:
                    raise ValueError("Expected a reference to the \"%s\" collection but found %r instead." % (node.typ.collection, value))
                id = value.id
            else:
                raise ValueError("Expected a reference to the \"%s\" collection but found %r instead." % (node.typ.collection, value))

            return Reference(node.typ.collection, id, serialize_id_only=True)
        else:
            if type(value) is DBRef:
                return Reference(value.collection, value.id)
            else:
                raise ValueError("Expected a reference but found %r instead." % value)
    return value
