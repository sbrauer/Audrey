import colander
from audrey import dateutil
from audrey.htmlutil import html_to_text
from copy import deepcopy
import datetime

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
        return self._use_elastic and self.__parent__._use_elastic

    def get_schema(self):
        return self.get_class_schema(self.request)

    def get_schema_names(self):
        return [node.name for node in self.get_schema().children]

    def get_nonschema_values(self):
        values = {}
        if self._id:
            values['_id'] =  self._id
        values['_created'] = getattr(self, '_created', None)
        values['_modified'] = getattr(self, '_modified', None)
        return values

    def set_nonschema_values(self, **kwargs):
        self._id = kwargs.get('_id') # mongodb id
        self._created = kwargs.get('_created')
        self._modified = kwargs.get('_modified')

    def set_schema_values(self, **kwargs):
        for name in self.get_schema_names():
            if kwargs.has_key(name):
                setattr(self, name, kwargs[name])

    def get_schema_values(self):
        """ Return a dictionary of this object's schema names and values.
        (Note that values are deep copies, so modifying them won't affect
        the Object instance.)
        """
        values = {}
        for name in self.get_schema_names():
            if hasattr(self, name):
                values[name] = deepcopy(getattr(self, name))
        return values

    def get_mongo_collection(self):
        return self.__parent__.get_mongo_collection()

    def get_elastic_connection(self):
        return self.__parent__.get_elastic_connection()

    def get_elastic_index_name(self):
        return self.__parent__.get_elastic_index_name()

    def get_elastic_doctype(self):
        return self.__parent__.get_elastic_doctype()

    def get_mongo_save_doc(self):
        doc = self.get_nonschema_values()
        doc.update(self.get_schema_values())
        return _mongify_values(doc)

    def save(self, set_modified=True, index=True):
        if set_modified:
            self._modified = dateutil.utcnow()
            if not getattr(self, '_created', None): self._created = self._modified
        doc = self.get_mongo_save_doc()
        _id = self.get_mongo_collection().save(doc, safe=True)
        if not self._id: self._id = _id
        if index: self.index()

    def load_mongo_doc(self, doc):
        clean = _demongify_values(doc)
        self.set_schema_values(**clean)
        self.set_nonschema_values(**clean)

    def _pre_delete(self):
        self.unindex()

    def index(self):
        if not self.use_elastic(): return
        doc = self.get_elastic_index_doc()
        self.get_elastic_connection().index(doc, self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))

    def unindex(self):
        if not self.use_elastic(): return
        try:
            self.get_elastic_connection().delete(self.get_elastic_index_name(), self.get_elastic_doctype(), str(self._id))
        except pyes.exceptions.NotFoundException, e:
            pass

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
                #if type(node.widget) == deform.widget.RichTextWidget:
                if getattr(node, 'is_html', False):
                    value = html_to_text(value, 0)
                if value: result.append(value)
        #elif type(node.typ) == deform.FileData:
        #    pass # FIXME: handle PDF, Word, etc?
        return result

class NamedObject(BaseObject):

    def get_nonschema_values(self):
        values = BaseObject.get_nonschema_values(self)
        values['__name__'] = self.__name__
        return values

    def set_nonschema_values(self, **kwargs):
        self.__name__ = kwargs.get('__name__')

    def get_elastic_index_doc(self):
        result = BaseObject.get_elastic_index_doc(self)
        result['__name__'] = self.__name__
        return result


# Crawl over node and make sure all types are compatible with pymongo.
# FIXME: what about files?  Maybe we need a File class that we replace
# with the gridfs ObjectId in this method...
# Whatever we do, we'd need to do the reverse when loading data back from mongo.
def _mongify_values(node):

    # Pymongo can't handle date objects (without time), so coerce all dates to datetimes.
    if type(node) is datetime.date:
        return datetime.datetime.combine(node, datetime.time())

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

    if type(node) == dict:
        results = {}
        for (key, value) in node.items():
            results[key] = _demongify_values(value)
        return results
    elif type(node) == list:
        return [_demongify_values(item) for item in node]
    else:
        return node
