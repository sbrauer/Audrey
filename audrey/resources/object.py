import colander
from audrey import dateutil
from audrey.htmlutil import html_to_text
from audrey.resources.file import File
from audrey.resources.generic import make_traversable
import datetime
import pyes
import hashlib
from bson.dbref import DBRef
from pyramid.traversal import find_root

GRIDFS_COLLECTION = "fs"

class BaseObject(object):
    """ Base class for objects that can be stored in MongoDB.
    Includes support for Deform; simply override the get_class_schema()
    class method to return a Colander schema for your class.
    """

    # Developers extending Audrey should create their own subclass(es) of 
    # BaseObject that:
    # - override _object_type; this string should uniquely identify the Object
    #   type within the context of a given Audrey application
    # - override get_class_schema() to return a colander schema for the type.
    #   Audrey makes use of the following custom SchemaNode kwargs
    #   for String nodes:
    #   - include_in_text: boolean, defaults to True; if True, the value will be included in Elastic's full text index.
    #   - is_html: boolean, defaults to False; if True, the value will be stripped of html markup before being indexed in Elastic.
    # If the type has some non-schema attributes that you store in Mongo,
    # override get_nonschema_values() and set_nonschema_values().

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
        if kwargs:
            self.set_schema_values(**kwargs)
            self.set_nonschema_values(**kwargs)

    def use_elastic(self):
        assert getattr(self, '__parent__', None), "parentless child!"
        return self._use_elastic and self.__parent__._use_elastic

    def get_schema(self):
        return self.get_class_schema(self.request)

    def get_schema_names(self):
        return [node.name for node in self.get_schema().children]

    def get_nonschema_values(self):
        values = {}
        _id = getattr(self, '_id', None)
        if _id: values['_id'] =  _id
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
            if hasattr(self, name):
                values[name] = getattr(self, name)
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
        return _mongify_values(self.get_all_values())

    def __str__(self):
        return str(self.get_all_values())

    def get_all_files(self):
        return _find_files(self.get_all_values()).values()

    def save(self, set_modified=True, index=True, set_etag=True):
        if set_modified:
            self._modified = dateutil.utcnow()
            if not getattr(self, '_created', None): self._created = self._modified
        if set_etag:
            self._etag = self.generate_etag()

        # Determine all the GridFS file ids that this object
        # now refers to and used to refer to.
        dbref = self.get_dbref()
        root = find_root(self)
        fs_files_coll = root.get_gridfs()._GridFS__files
        new_file_ids = set([x._id for x in self.get_all_files()])
        old_file_ids = set()
        if self._id:
            for item in fs_files_coll.find({'parents':dbref}, fields=[]):
                old_file_ids.add(item['_id'])

        # Persist the object in Mongo.
        doc = self.get_mongo_save_doc()
        self._id = self.get_mongo_collection().save(doc, safe=True)

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

    def load_mongo_doc(self, doc):
        clean = _demongify_values(doc)
        self.set_schema_values(**clean)
        self.set_nonschema_values(**clean)

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

class NamedObject(BaseObject):

    def get_nonschema_values(self):
        values = BaseObject.get_nonschema_values(self)
        values['__name__'] = self.__name__
        return values

    def set_nonschema_values(self, **kwargs):
        BaseObject.set_nonschema_values(self, **kwargs)
        self.__name__ = kwargs.get('__name__')

    def get_elastic_index_doc(self):
        result = BaseObject.get_elastic_index_doc(self)
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

