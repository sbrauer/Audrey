import colander
import webob
from pyramid.encode import urlencode
from pyramid.httpexceptions import HTTPNotFound
from pyramid.traversal import find_root, resource_path
import resources
from exceptions import Veto
import sortutil
from bson.objectid import ObjectId
import audrey.resources
from audrey.colanderutil import AudreySchemaConverter

DEFAULT_BATCH_SIZE = 20
MAX_BATCH_SIZE = 100
SCHEMA_CONVERTER = AudreySchemaConverter()

def get_href(context, *elements, **kw):
    # Return absolute url:
    #return context.request.resource_url(context, *elements, **kw)

    # Return url starting with '/':
    path = resource_path(context)
    if elements:
        if path[-1] != '/':
            path += '/'
        path += '/'.join(elements)
    if 'query' in kw:
        query = kw['query']
        if query:
            return '%s?%s' % (path, urlencode(query, doseq=True))
    return path

def get_curie(context, request):
    # Return a "curie" object to namespace our HAL+JSON links.
    root = find_root(context)
    return dict(
        name='audrey',
        href="%srelations/{rel}" % get_href(root),
        templated=True,
    )

def generic_response(request, status=200, error=None, **kwargs):
    request.response.status_int = status
    ret = dict(status=status)
    if error:
        ret['ok'] = False
        ret['error'] = error
    else:
        ret['ok'] = True
    ret.update(kwargs)
    return ret

def str_to_bool(s, default=None):
    """ Interpret the given string ``s`` as a boolean value.
    ``default`` should be one of ``None``, ``True``, or ``False``.
    """
    if s is None:
        return default
    s = s.strip().lower()
    if s == '':
        return default
    if s in ('0', 'false'):
        return False
    return True

def str_to_list(s, default=None):
    """ Interpret the given string ``s`` as a comma-delimited list
    of strings.
    """
    if s is None:
        return default
    s = s.strip()
    if s == '':
        return default
    return s.split(',')

# FIXME: consider ditching all these handler classes???

# FIXME: replace with an interface?
class ItemHandler(object):
    def get_property(self):
        pass # Should return "_links" or "_embedded"
    def handle_item(self, context, request):
        pass # Should return a dictionary representing one item.

class EmbeddingItemHandler(ItemHandler):
    def __init__(self, fields=None):
        self.fields = fields
    def get_property(self):
        return "_embedded"
    def handle_item(self, context, request):
        return represent_object(context, request, fields=self.fields)

class LinkingItemHandler(ItemHandler):
    def get_property(self):
        return "_links"
    def handle_item(self, context, request):
        return dict(name=context.__name__,
                    href=get_href(context),
                    title=context.get_title())

class LinkingSearchItemHandler(LinkingItemHandler):
    def handle_item(self, context, request):
        # Context may be either an object or a dict with object and highlight.
        if type(context) == dict:
            object = context['object']
            highlight = context['highlight']
        else:
            object = context
            highlight = None
        ret = dict(
                name="%s:%s" % (object.__parent__.__name__, object.__name__),
                href=get_href(object),
                title=object.get_title())
        if highlight: ret['highlight'] = highlight
        return ret

class EmbeddingSearchItemHandler(EmbeddingItemHandler):
    def handle_item(self, context, request):
        # Context may be either an object or a dict with object and highlight.
        if type(context) == dict:
            object = context['object']
            highlight = context['highlight']
        else:
            object = context
            highlight = None
        ret = EmbeddingItemHandler.handle_item(self, context, request)
        if highlight: ret['_highlight'] = highlight
        return ret

class LinkingReferenceHandler(ItemHandler):
    def get_property(self):
        return "_links"
    def handle_item(self, context, request):
        return dict(name=str(context._id),
                    href=get_href(context),
                    title=context.get_title())

DEFAULT_COLLECTION_ITEM_HANDLER = LinkingItemHandler()
DEFAULT_SEARCH_ITEM_HANDLER = LinkingSearchItemHandler()
DEFAULT_REFERENCE_HANDLER = LinkingReferenceHandler()

def method_not_allowed(context, request):
    return generic_response(request, 405,
        "%s not supported by this resource." % request.method)

def object_options(context, request):
    request.response.allow = "HEAD,GET,OPTIONS,PUT,DELETE"
    request.response.status_int = 204 # No Content

def root_options(context, request):
    request.response.allow = "HEAD,GET,OPTIONS"
    request.response.status_int = 204 # No Content

def collection_options(context, request):
    if isinstance(request.context, resources.collection.NamingCollection):
        request.response.allow = "HEAD,GET,OPTIONS"
    else:
        request.response.allow = "HEAD,GET,OPTIONS,POST"
    request.response.status_int = 204 # No Content

def represent_object(context, request, reference_handler=DEFAULT_REFERENCE_HANDLER, fields=None, include_meta_links=False):
    if fields is None:
        ret = context.get_all_values()
        if '_etag' in ret:
            del ret['_etag']
    else:
        ret = {}
        for name in fields:
            ret[name] = getattr(context, name, None)
    if (fields is None) or ('_object_type' in fields):
        ret['_object_type'] = context._object_type
    if (fields is None) or ('_title' in fields):
        ret['_title'] = context.get_title()

    ret['_links'] = dict(self = dict(href=get_href(context)))
    if include_meta_links:
        ret['_links']['curie'] = get_curie(context, request)
        ret['_links']['collection'] = dict(href=get_href(context.__parent__))
        ret['_links']['describedby'] = dict(href=get_href(context.__parent__, '@@schema', context._object_type))
    file_links= [
        dict(
            name=str(f._id),
            href=get_href(context, '@@download', str(f._id)),
            type=f.get_gridfs_file(request).content_type,
            length=f.get_gridfs_file(request).length,
        ) for f in context.get_all_files()]
    if file_links: ret['_links']['audrey:file'] = file_links
    references = [reference_handler.handle_item(obj, request) for obj in context.get_all_referenced_objects()]
    if references:
        if reference_handler.get_property() == '_embedded':
            ret['_embedded'] = {}
        ret[reference_handler.get_property()]['audrey:reference'] = references
    return ret

def object_get(context, request, reference_handler=DEFAULT_REFERENCE_HANDLER):
    request.response.content_type = 'application/hal+json'
    request.response.etag = context._etag
    request.response.last_modified = context._modified
    request.response.conditional_response = True
    return represent_object(context, request, reference_handler=reference_handler, include_meta_links=True)

def test_preconditions(context, request):
    # Returns None on success, or a dictionary on failure with ok, status, and error keys.
    # Also sets response status code on failure.
    # Possible failure statuses:
    # 412 Precondition Failed
    error = None
    if_unmodified_since = request.headers.get('If-Unmodified-Since')
    if_match = request.headers.get('If-Match')
    if not (if_unmodified_since and if_match):
        error='Requests must supply If-Unmodified-Since and If-Match headers.'
    elif if_match != ('"%s"' % context._etag):
        error='If-Match header does not match current Etag.'
    elif if_unmodified_since != webob.datetime_utils.serialize_date(context._modified):
        error='If-Unmodified-Since header does not match current modification timestamp.'
    if error:
        return generic_response(request, 412, error)
    return None

def object_put(context, request):
    # Update an existing object.
    # Response body is simple application/json document with keys:
    # "ok", "status", and optional "error" (when not ok).
    # On success, response status is 200.
    # In the event of schema validation errors, there will also be an "errors"
    # key containing a dictionary mapping field names to error messages.
    # Possible failure statuses:
    # 412 Precondition Failed
    # 400 Bad Request: Validation failed.
    err = test_preconditions(context, request)
    if err: return err
    # FIXME: confirm that _object_type in json_body is correct?
    schema = context.get_schema()
    try:
        deserialized = schema.deserialize(request.json_body)
    except colander.Invalid, e:
        errors = e.asdict()
        return generic_response(request, 400, 'Validation failed.', errors=errors)
    context.set_schema_values(**deserialized)
    # We just validated the schema, so no need to do it again.
    context.save(validate_schema=False)
    request.response.etag = context._etag
    request.response.last_modified = context._modified
    request.response.location = request.resource_url(context)
    return generic_response(request)

def object_delete(context, request):
    # Delete an existing object.
    # Response body is simple application/json document with keys:
    # "ok", "status", and optional "error" (when not ok).
    # On success, response status is 200.
    # Possible failure statuses:
    # 412 Precondition Failed
    err = test_preconditions(context, request)
    if err: return err
    context.__parent__.delete_child(context)
    return generic_response(request)

def collection_rename(context, request):
    json_body = request.json_body
    from_name = json_body.get('from_name', '').strip()
    to_name = json_body.get('to_name', '').strip()
    try:
        context.rename_child(from_name, to_name)
    except Veto, e:
        return generic_response(request, 400, str(e))
    except KeyError, e:
        return generic_response(request, 404, str(e))
    obj = context[to_name]
    request.response.location = request.resource_url(obj)
    return generic_response(request)

def root_get(context, request):
    ret = {}
    ret['_links'] = dict(
        self = dict(href=get_href(context)),
        curie = get_curie(context, request),
        item = [dict(name=c.__name__, href=get_href(c)+"{?embed,fields,sort}", templated=True) for c in context.get_collections()],
        search = dict(href=get_href(context, '@@search')+"?q={q}{&collections,embed,fields,sort}", templated=True),
    )
    ret['_links']['audrey:upload'] = dict(href=get_href(context, '@@upload'))
    request.response.content_type = 'application/hal+json'
    return ret

def root_upload(context, request):
    ret = generic_response(request)
    for (name, val) in request.POST.items():
        if hasattr(val, 'filename'):
            file = context.create_gridfs_file_from_fieldstorage(val)
            if name not in ret:
                ret[name] = []
            ret[name].append(file)
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

def root_search(context, request, highlight_fields=None):
    embed = str_to_bool(request.GET.get('embed'), False)
    fields = None
    if embed:
        fields = str_to_list(request.GET.get('fields'))
        item_handler = EmbeddingSearchItemHandler(fields)
    else:
        item_handler = DEFAULT_SEARCH_ITEM_HANDLER

    (batch, per_batch, skip) = get_batch_parms(request)
    sort = request.GET.get('sort', None)
    q = request.GET.get('q', None)
    collection_names = str_to_list(request.GET.get('collections'))
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
        self = dict(href=get_href(context, '@@search', query=query_dict)),
    )
    if batch > 1:
        query_dict['batch'] = batch-1
        ret['_links']['prev'] = dict(href=get_href(context, '@@search', query=query_dict))
    if batch < total_batches:
        query_dict['batch'] = batch+1
        ret['_links']['next'] = dict(href=get_href(context, '@@search', query=query_dict))

    if item_handler.get_property() == '_embedded':
        ret['_embedded'] = {}
    ret[item_handler.get_property()]['item'] = [item_handler.handle_item(obj, request) for obj in result['items']]
    request.response.content_type = 'application/hal+json'
    return ret

def collection_get(context, request, spec=None):
    embed = str_to_bool(request.GET.get('embed'), False)
    fields = None
    if embed:
        fields = str_to_list(request.GET.get('fields'))
        item_handler = EmbeddingItemHandler(fields)
    else:
        item_handler = DEFAULT_COLLECTION_ITEM_HANDLER

    (batch, per_batch, skip) = get_batch_parms(request)
    sort_string = request.GET.get('sort', None)
    mongo_sort = sortutil.sort_string_to_mongo(sort_string)
    result = context.get_children_and_total(spec=spec, sort=mongo_sort, skip=skip, limit=per_batch, fields=fields)
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
    if fields:
        ret['_summary']['fields'] = fields
    if isinstance(context, resources.collection.NamingCollection):
        create_method = 'PUT'
    else:
        create_method = 'POST'
    ret['_factory'] = dict(method=create_method, schemas=context.get_object_types())
    query_dict = {}
    query_dict.update(request.GET.dict_of_lists())
    view_name = request.view_name
    if view_name: view_name = '@@'+view_name
    ret['_links'] = dict(
        self = dict(href=get_href(context, view_name, query=query_dict)),
        curie = get_curie(context, request),
        collection = dict(href=get_href(context.__parent__)),
    )
    ret['_links']['audrey:schema'] = [dict(name=x, href=get_href(context, '@@schema', x)) for x in context.get_object_types()]
    if isinstance(context, resources.collection.NamingCollection):
        ret['_links']['audrey:rename'] = dict(href=get_href(context, '@@rename'))
    if batch > 1:
        query_dict['batch'] = batch-1
        ret['_links']['prev'] = dict(href=get_href(context, query=query_dict))
    if batch < total_batches:
        query_dict['batch'] = batch+1
        ret['_links']['next'] = dict(href=get_href(context, query=query_dict))

    if item_handler.get_property() == '_embedded':
        ret['_embedded'] = {}
    ret[item_handler.get_property()]['item'] = [item_handler.handle_item(obj, request) for obj in result['items']]

    request.response.content_type = 'application/hal+json'
    return ret

def collection_post(context, request, __name__=None):
    # Create a new object/resource.
    # Request body should be a JSON document with
    # the new object's schema values (and _object_type).
    # On success, return 201 Created with Location
    # header containing url of new resource.
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
        object_class = context.get_object_class(_object_type)
    else:
        return generic_response(request, 400, 'Request is missing _object_type.')
    if object_class is None:
        return generic_response(request, 400, 'Unsupported _object_type.')

    schema = object_class.get_class_schema(request=request)
    try:
        deserialized = schema.deserialize(json_body)
    except colander.Invalid, e:
        return generic_response(request, 400, 'Validation failed.', errors=e.asdict())
    obj = object_class(request, **deserialized)
    if __name__: obj.__name__ = __name__
    try:
        # We just validated the schema, so no need to do it again.
        context.add_child(obj, validate_schema=False)
    except Veto, e:
        return generic_response(request, 400, str(e))

    request.response.location = request.resource_url(obj)
    # FIXME: Should the body contain a representation of the object?
    return generic_response(request, 201)

def collection_schema(context, request):
    # Serve a JSON Schema for an object_type (specified as first subpath item).
    object_type = request.subpath[0]
    object_class = context.get_object_class(object_type)
    if object_class is None:
        return HTTPNotFound()
    schema = object_class.get_class_schema(request=request)
    jsonschema = SCHEMA_CONVERTER.to_jsonschema(schema)
    jsonschema['properties']['_object_type'] = dict(
        type='string',
        required=True,
        enum=[object_type],
    )
    request.response.content_type = 'application/schema+json'
    return jsonschema

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
