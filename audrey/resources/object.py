import datetime
import hashlib
from pprint import pformat
import colander
from bson.dbref import DBRef
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
    - override _object_type; this string should uniquely identify the Object
      type within the context of a given Audrey application
    - override get_class_schema() to return a colander schema for the type.
      Audrey makes use of the following custom SchemaNode kwargs
      for String nodes:
      - include_in_text: boolean, defaults to True; if True, the value will be included in Elastic's full text index.
      - is_html: boolean, defaults to False; if True, the value will be stripped of html markup before being indexed in Elastic.
    - override get_title() to return a suitable title string

    If the type has some non-schema attributes that you store in Mongo,
    override get_nonschema_values() and set_nonschema_values().
    """

    _object_type = "object"

    # If a request is passed, it gives us access to request.context, the
    # mongo db connection, and the current user (via
    # pyramid.security.authenticated_userid(request)).
    # Could be handy for default values, vocabulary lists, etc.
    @classmethod
    def get_class_schema(cls, request=None):
        return colander.SchemaNode(colander.Mapping())

    # Should this Object use Elastic?
    # Note that this setting only matters if the Collection's _use_elastic=True.
    _use_elastic = True

    # kwargs should be a dictionary of attribute names and values
    # The values should be "demongified".
    def __init__(self, request, **kwargs):
        self.request = request
        self.set_schema_values(**kwargs)
        self.set_nonschema_values(**kwargs)

    def use_elastic(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self._use_elastic and self.__parent__._use_elastic

    def get_schema(self):
        # As an optimization, only generate the schema once per request.
        if not hasattr(self, '__schema__'):
            self.__schema__ = self.get_class_schema(self.request)
        return self.__schema__

    def get_schema_names(self):
        return [node.name for node in self.get_schema().children]

    def get_nonschema_values(self):
        values = {}
        values['_id'] =  getattr(self, '_id', None)
        values['_created'] = getattr(self, '_created', None)
        values['_modified'] = getattr(self, '_modified', None)
        values['_etag'] = getattr(self, '_etag', None)
        return values

    def set_nonschema_values(self, **kwargs):
        self._id = kwargs.get('_id') # mongodb id
        self._created = kwargs.get('_created')
        self._modified = kwargs.get('_modified')
        self._etag = kwargs.get('_etag')

    def set_schema_values(self, **kwargs):
        for name in self.get_schema_names():
            if kwargs.has_key(name):
                setattr(self, name, kwargs[name])

    def get_schema_values(self):
        """ Return a dictionary of this object's schema names and values.
        """
        values = {}
        for name in self.get_schema_names():
            values[name] = getattr(self, name, None)
        return values

    def get_all_values(self):
        """ Returns a dictionary of both schema and nonschema values. """
        vals = self.get_nonschema_values()
        vals.update(self.get_schema_values())
        return vals

    def get_mongo_collection(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_mongo_collection()

    def get_elastic_connection(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_connection()

    def get_elastic_index_name(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_index_name()

    def get_elastic_doctype(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self.__parent__.get_elastic_doctype()

    def get_mongo_save_doc(self):
        doc = _mongify_values(self.get_all_values())
        if doc['_id'] is None:
            del doc['_id']
        return doc

    def __str__(self):
        return pformat(self.get_all_values())

    def get_title(self):
        # Subclasses should override this method to return
        # a reasonable title for this instance.
        return self.__name__ or 'Untitled'

    def get_all_files(self):
        return _find_files(self.get_all_values()).values()

    def get_all_references(self):
        return _find_references(self.get_all_values()).values()

    def get_all_referenced_objects(self):
        ret = []
        root = find_root(self)
        for ref in self.get_all_references():
            obj = root.get_object_for_reference(ref)
            if obj is not None:
                ret.append(obj)
        return ret

    def save(self, set_modified=True, index=True, set_etag=True):
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
            fs_files_coll.update({'_id':{'$in':list(ids_to_remove)}}, {"$pull":{"parents":dbref}}, multi=True)
        if ids_to_add:
            fs_files_coll.update({'_id':{'$in':list(ids_to_add)}}, {"$addToSet":{"parents":dbref}}, multi=True)

        if index: self.index()

    def generate_etag(self):
        h = hashlib.new('md5')
        h.update(str(self.get_schema_values()))
        return h.hexdigest()

    # FIXME... implement and test
    def roundtrip_thru_schema(self):
        """ Runs the instance's schema attribute values
        thru a serialize-deserialize roundtrip.
        This will raise a colander.Invalid exception if the
        schema fails to validate.
        Otherwise it will have the effect of applying default and
        missing values.
        """
        schema = self.get_schema()
        data = schema.deserialize(schema.serialize(self.get_schema_values()))
        self.set_schema_values(**data)

    def load_mongo_doc(self, doc):
        clean = _demongify_values(doc)
        self.set_nonschema_values(**clean)
        clean = _apply_schema_to_values(self.get_schema(), clean)
        self.set_schema_values(**clean)

    def get_dbref(self, include_database=False):
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
        fs_files_coll.update({'parents':dbref}, {"$pull":{"parents":dbref}}, multi=True)

    def index(self):
        if not self.use_elastic(): return
        doc = self.get_elastic_index_doc()
        self.get_elastic_connection().index(doc, self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))
        self.get_elastic_connection().refresh(self.get_elastic_index_name())

    def unindex(self):
        if not self.use_elastic(): return 0
        try:
            self.get_elastic_connection().delete(self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))
            self.get_elastic_connection().refresh(self.get_elastic_index_name())
            return 1
        except pyes.exceptions.NotFoundException, e:
            return 0

    def get_elastic_index_doc(self):
        return dict(
            _created = self._created,
            _modified = self._modified,
            text = self.get_fulltext_to_index(),
        )

    def get_fulltext_to_index(self):
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

class NamedObject(Object):

    def __init__(self, request, **kwargs):
        self.__name__ = None
        Object.__init__(self, request, **kwargs)

    def get_nonschema_values(self):
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
            if val:
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
            # Assume value is an ObjectId
            return Reference(node.typ.collection, value, serialize_id_only=True)
        else:
            # Assume value is a DBRef
            return Reference(value.collection, value.id)
    return value
