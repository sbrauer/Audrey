import colander
import webob
from pyramid.httpexceptions import HTTPNotFound
import resources
from exceptions import Veto

# FIXME: implement OPTIONS, DELETE, POST and PUT (as appropriate)

def object_get(context, request):
    ret = context.get_schema_values()
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context)),
        collection = dict(href=request.resource_url(context.__parent__)),
    )
    ret['_id'] = str(context._id)
    ret['_created'] = context._created
    ret['_modified'] = context._modified
    ret['_object_type'] = context._object_type
    request.response.content_type = 'application/hal+json'
    request.response.etag = context._etag
    request.response.last_modified = context._modified
    request.response.conditional_response = True
    return ret

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

def root_get(context, request):
    ret = {}
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context)),
        # FIXME: figure out optional parms for sorting/filtering collections
        #item = [dict(name=c.__name__, href=request.resource_url(c)+"{?sort,filter}", templated=True) for c in context.get_children()],
        item = [dict(name=c.__name__, href=request.resource_url(c)) for c in context.get_children()],
        # FIXME: add a search link (and implement a search resource)
    )
    request.response.content_type = 'application/hal+json'
    return ret

def collection_get(context, request):
    # FIXME: add support for paging, sorting and filtering via optional parms to to_hal()
    ret = {}
    # FIXME: add option to put children inside _embedded instead of _links
    ret['_links'] = dict(
        self = dict(href=request.resource_url(context)),
        collection = dict(href=request.resource_url(context.__parent__)),
        # FIXME: add paging, sorting and filtering
        item = [dict(name=c.__name__, href=request.resource_url(c)) for c in context.get_children()],
    )
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
        # We want a name, but only if there's no subpath.
        # We only care about creating direct children.
        if name and not request.subpath:
            return collection_post(request.context, request, name)
    return HTTPNotFound()

def notfound_default(request):
    return HTTPNotFound()

