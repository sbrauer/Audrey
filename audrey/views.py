import colander
import webob
from pyramid.httpexceptions import HTTPNotFound
import resources
from exceptions import Veto
import sortutil
from bson.objectid import ObjectId
import audrey.resources

DEFAULT_BATCH_SIZE = 20
MAX_BATCH_SIZE = 100

# FIXME: consider returning some sort of documentation
# in the OPTIONS response body...
# Perhaps a JSON document with details of the supported POST and/or PUT
# requests?

def object_options(context, request):
    request.response.allow = "HEAD,GET,OPTIONS,PUT,DELETE"
    request.response.status_int = 204 # No Content
    return {}

def root_options(context, request):
    request.response.allow = "HEAD,GET,OPTIONS"
    request.response.status_int = 204 # No Content
    return {}

def collection_options(context, request):
    if isinstance(request.context, resources.collection.NamingCollection):
        request.response.allow = "HEAD,GET,OPTIONS"
    else:
        request.response.allow = "HEAD,GET,OPTIONS,POST"
    request.response.status_int = 204 # No Content
    return {}

def represent_object(context, request):
    ret = context.get_all_values()
    #ret = context.get_schema_values()
    #ret['_id'] = str(context._id)
    #ret['_created'] = context._created
    #ret['_modified'] = context._modified
    ret['_object_type'] = context._object_type
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context)),
        collection = dict(href=request.resource_url(context.__parent__)),
    )
    if isinstance(request.context, resources.object.NamedObject):
        ret['__name__'] = context.__name__
        # FIXME: namespace this rel and document
        ret['_links']['__name__'] = dict(href=request.resource_url(context, '__name__'))
    # FIXME: namespace and document the "file" rel
    ret['_links']['file'] = [dict(name=str(f._id), href=request.resource_url(context, '@@download', str(f._id))) for f in context.get_all_files()]
    return ret

def object_get(context, request):
    request.response.content_type = 'application/hal+json'
    request.response.etag = context._etag
    request.response.last_modified = context._modified
    request.response.conditional_response = True
    return represent_object(context, request)

def test_preconditions(context, request):
    # Returns None on success, or a dictionary with an "error" key on failure.
    # Also sets response status code on failure.
    # Possible failure statuses:
    # 403 Forbidden: Precondition headers (If-Unmodified-Since and If-Match) missing.
    # 412 Precondition Failed
    if_unmodified_since = request.headers.get('If-Unmodified-Since')
    if_match = request.headers.get('If-Match')
    if not (if_unmodified_since and if_match):
        request.response.status_int = 403 # Forbidden
        return dict(error='Requests must supply both If-Unmodified-Since and If-Match headers.')
    if if_match != ('"%s"' % context._etag):
        request.response.status_int = 412 # Precondition Failed
        return dict(error='If-Match header does not match current Etag.')
    if if_unmodified_since != webob.datetime_utils.serialize_date(context._modified):
        request.response.status_int = 412 # Precondition Failed
        return dict(error='If-Unmodified-Since header does not match current modification timestamp.')
    return None

def object_put(context, request):
    # Update an existing object.
    # On success, response is an empty body (204).
    # On failure, response is simple application/json document
    # with an "error" key containing an error message string.
    # In the event of schema validation errors, there will also be an "errors"
    # key containing a dictionary mapping field names to error messages.
    # Possible failure statuses:
    # 403 Forbidden: Precondition headers (If-Unmodified-Since and If-Match) missing.
    # 412 Precondition Failed
    # 400 Bad Request: Validation failed.
    err = test_preconditions(context, request)
    if err: return err
    schema = context.get_schema()
    try:
        deserialized = schema.deserialize(request.json_body)
    except colander.Invalid, e:
        errors = e.asdict()
        request.response.status_int = 400 # Bad Request
        return dict(error='Validation failed.', errors=errors)
    context.set_schema_values(**deserialized)
    context.save()
    request.response.status_int = 204 # No Content
    request.response.content_location = request.resource_url(context)
    return {}

def object_delete(context, request):
    # Delete an existing object.
    # On success, response is an empty body (204).
    # On failure, response is simple application/json document
    # with an "error" key containing an error message string.
    # Possible failure statuses:
    # 403 Forbidden: Precondition headers (If-Unmodified-Since and If-Match) missing.
    # 412 Precondition Failed
    err = test_preconditions(context, request)
    if err: return err
    context.__parent__.delete_child(context)
    request.response.status_int = 204 # No Content
    return {}

def object_name_options(context, request):
    request.response.allow = "HEAD,GET,OPTIONS,PUT"
    request.response.status_int = 204 # No Content
    return {}

def object_name(context, request):
    """ A resource representing the __name__ of a NamedObject.
    Supports GET and PUT (to rename an object).
    """
    if request.method == 'GET':
        ret = dict(__name__ = context.__name__)
        ret['_links'] = dict(
            self = dict(href=request.resource_url(context, '__name__')),
            up = dict(href=request.resource_url(context)),
        )
        request.response.content_type = 'application/hal+json'
        request.response.etag = context._etag
        request.response.last_modified = context._modified
        request.response.conditional_response = True
        return ret
    elif request.method == 'PUT':
        err = test_preconditions(context, request)
        if err: return err
        name = context.__name__
        json_body = request.json_body
        newname = json_body.get('__name__', '').strip()
        try:
            context.__parent__.rename_child(name, newname)
        except Veto, e:
            request.response.status_int = 400 # Bad Request
            return dict(error=str(e))
        if newname == name:
            obj = context
        else:
            obj = context.__parent__[newname]
        request.response.status_int = 204 # No Content
        request.response.content_location = request.resource_url(obj)
        request.response.location = request.resource_url(obj)
        return {}
    else:
        request.response.status_int = 405 # Method Not Allowed
        return {}

def root_get(context, request):
    ret = {}
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context)),
        item = [dict(name=c.__name__, href=request.resource_url(c)+"{?sort}", templated=True) for c in context.get_children()],
        search = dict(href=request.resource_url(context, '@@search')+"?q={q}{&sort}{&collection*}", templated=True),
        # FIXME: need a custom (and documented) rel
        upload = dict(href=request.resource_url(context, '@@upload')),
    )
    request.response.content_type = 'application/hal+json'
    return ret

# FIXME: should i just hardcode a variable name (say "file") instead
# of trying to be flexible and accept all file uploads as below?
def root_upload(context, request):
    ret = {}
    for (name, val) in request.POST.items():
        if hasattr(val, 'filename'):
            _id = context.create_gridfs_file(val)
            ret[name] = str(_id)
    return ret

def root_download(context, request):
    # Handle urls of the form: "/download/gridfs_id"
    return context.serve_gridfs_file_for_id(ObjectId(request.subpath[0]))

def object_download(context, request):
    # Handle urls of the form: "/some/object/download/gridfs_id"
    # Only allow download of files "owned" by the context object.
    f = audrey.resources.file.File(ObjectId(request.subpath[0]))
    gf = f.get_gridfs_file(request)
    if gf and (context.get_dbref() in gf.parents):
        return f.serve(request)
    return HTTPNotFound()

def file_serve(context, request):
    # Serve an audrey.resources.file.File
    return context.serve(request)

# FIXME: replace with an interface?
class ItemHandler(object):
    def get_property(self):
        pass # Should return "_links" or "_embedded"
    def handle_item(self, context, request):
        pass # Should return a dictionary representing one item.

class LinkingItemHandler(ItemHandler):
    def get_property(self):
        return "_links"
    def handle_item(self, context, request):
        return dict(name=context.__name__, href=request.resource_url(context))

class EmbeddingItemHandler(ItemHandler):
    def get_property(self):
        return "_embedded"
    def handle_item(self, context, request):
        return represent_object(context, request)

class LinkingSearchItemHandler(LinkingItemHandler):
    def handle_item(self, context, request):
        # Context may be either an object or a dict with object and highlight.
        if type(context) == dict:
            object = context['object']
            highlight = context['highlight']
        else:
            object = context
            highlight = None
        ret = dict(name="%s:%s" % (object.__parent__.__name__, object.__name__), href=request.resource_url(object))
        if highlight: ret['highlight'] = highlight
        return ret

DEFAULT_COLLECTION_ITEM_HANDLER = LinkingItemHandler()
DEFAULT_SEARCH_ITEM_HANDLER = LinkingSearchItemHandler()

def root_search(context, request, highlight_fields=None, item_handler=DEFAULT_SEARCH_ITEM_HANDLER):
    (batch, per_batch, skip) = get_batch_parms(request)
    sort = request.GET.get('sort', None)
    q = request.GET.get('q', None)
    collection_names = request.GET.getall('collection')
    result = context.basic_fulltext_search(search_string=q, collection_names=collection_names, skip=skip, limit=per_batch, sort=sort, highlight_fields=highlight_fields)
    total_items = result['total']
    total_batches = total_items / per_batch
    if total_items % per_batch: total_batches += 1

    ret = {}
    ret['_summary'] = dict(
        total_items = total_items,
        total_batches = total_batches,
        batch = batch,
        per_batch = per_batch,
        sort = sort,
        collections = collection_names,
        q = q,
    )
    query_dict = {}
    query_dict.update(request.GET)
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context, '@@search', query=query_dict)),
    )
    if batch > 1:
        query_dict['batch'] = batch-1
        ret['_links']['prev'] = dict(href=request.resource_url(context, '@@search', query=query_dict))
    if batch < total_batches:
        query_dict['batch'] = batch+1
        ret['_links']['next'] = dict(href=request.resource_url(context, '@@search', query=query_dict))

    if item_handler.get_property() == '_embedded':
        ret['_embedded'] = {}
    ret[item_handler.get_property()]['item'] = [item_handler.handle_item(obj, request) for obj in result['items']]
    request.response.content_type = 'application/hal+json'
    return ret

def collection_get(context, request, spec=None, item_handler=DEFAULT_COLLECTION_ITEM_HANDLER):
    (batch, per_batch, skip) = get_batch_parms(request)
    sort_string = request.GET.get('sort', None)
    mongo_sort = sortutil.sort_string_to_mongo(sort_string)
    result = context.get_children_and_total(spec=spec, sort=mongo_sort, skip=skip, limit=per_batch)
    total_items = result['total']
    total_batches = total_items / per_batch
    if total_items % per_batch: total_batches += 1

    ret = {}
    ret['_summary'] = dict(
        total_items = total_items,
        total_batches = total_batches,
        batch = batch,
        per_batch = per_batch,
        sort = sort_string,
    )
    query_dict = {}
    query_dict.update(request.GET)
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context, query=query_dict)),
        collection = dict(href=request.resource_url(context.__parent__)),
    )
    if batch > 1:
        query_dict['batch'] = batch-1
        ret['_links']['prev'] = dict(href=request.resource_url(context, query=query_dict))
    if batch < total_batches:
        query_dict['batch'] = batch+1
        ret['_links']['next'] = dict(href=request.resource_url(context, query=query_dict))

    if item_handler.get_property() == '_embedded':
        ret['_embedded'] = {}
    ret[item_handler.get_property()]['item'] = [item_handler.handle_item(obj, request) for obj in result['items']]

    request.response.content_type = 'application/hal+json'
    return ret

def collection_post(context, request, __name__=None):
    # Create a new object/resource.
    # Request body should be a JSON document with
    # the new object's schema values (and optional _object_type;
    # required for heterogenous collections).
    # On success, return 201 Created with an empty body and Content-Location
    # header with url of new resource.
    # On failure, response is simple application/json document
    # with an "error" key containing an error message string.
    # In the event of schema validation errors, there will also be an "errors"
    # key containing a dictionary mapping field names to error messages.
    # Possible failure statuses:
    # 400 Bad Request: _object_type missing or invalid, or validation failed.
    object_class = None
    json_body = request.json_body
    _object_type = json_body.get('_object_type', None)
    if _object_type:
        object_class = context._object_classes_by_type.get(_object_type, None)
    else:
        classes = context.get_object_classes()
        if len(classes) == 1:
            object_class = classes[0]
        else:
            request.response.status_int = 400 # Bad Request
            return dict(error='Request is missing _object_type.')
    if object_class is None:
        request.response.status_int = 400 # Bad Request
        return dict(error='Unsupported _object_type.')

    schema = object_class.get_class_schema(request=request)
    try:
        deserialized = schema.deserialize(json_body)
    except colander.Invalid, e:
        errors = e.asdict()
        request.response.status_int = 400 # Bad Request
        return dict(error='Validation failed.', errors=errors)
    obj = object_class(request, **deserialized)
    if __name__: obj.__name__ = __name__
    try:
        context.add_child(obj)
    except Veto, e:
        request.response.status_int = 400 # Bad Request
        return dict(error=str(e))

    request.response.status_int = 201 # Created
    request.response.content_location = request.resource_url(obj)
    request.response.location = request.resource_url(obj)
    return {}

def notfound_put(request):
    if isinstance(request.context, resources.collection.NamingCollection):
        name = request.view_name
        # A non-empty subpath would indicate more than one path element.
        if name and not request.subpath:
            return collection_post(request.context, request, name)
    return HTTPNotFound()

def notfound_default(request):
    return HTTPNotFound()

def get_int_query_parm(request, name, default=None):
    try:
        return int(request.GET[name])
    except:
        return default

def get_batch_parms(request):
    batch = get_int_query_parm(request, 'batch', 1)
    per_batch = get_int_query_parm(request, 'per_batch', DEFAULT_BATCH_SIZE)
    if per_batch > MAX_BATCH_SIZE: per_batch = MAX_BATCH_SIZE
    skip = (batch-1) * per_batch
    limit = per_batch
    return (batch, per_batch, skip)
