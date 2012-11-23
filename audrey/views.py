import colander
import webob # for datetime_utils

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
    request.response.content_type = 'application/json'
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

def collection_post(context, request):
    # Create a new object/resource.
    # Request body should be a JSON document with
    # the new object's schema values and _object_type.
    # On success, return 201 Created with an empty body and Content-Location
    # header with url of new resource.
    # On failure, response is simple application/json document
    # with an "error" key containing an error message string.
    # In the event of schema validation errors, there will also be an "errors"
    # key containing a dictionary mapping field names to error messages.
    # Possible failure statuses:
    # 400 Bad Request: _object_type missing or invalid, or validation failed.
    request.response.content_type = 'application/json'
    json_body = request.json_body
    _object_type = json_body.get('_object_type', None)
    if _object_type is None:
        request.response.status_int = 400 # Bad Request
        return dict(error='Request is missing _object_type.')
    object_class = context._object_classes_by_type.get(_object_type, None)
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
    context.add_child(obj)
    request.response.status_int = 201 # Created
    request.response.content_location = request.resource_url(obj)
    request.response.location = request.resource_url(obj)
    return {}

def object_delete(context, request):
    # Delete an existing object.
    # On success, response is an empty body (204).
    # On failure, response is simple application/json document
    # with an "error" key containing an error message string.
    # Possible failure statuses:
    # 403 Forbidden: Precondition headers (If-Unmodified-Since and If-Match) missing.
    # 412 Precondition Failed
    request.response.content_type = 'application/json'
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

# FIXME: implement OPTIONS, DELETE, POST and PUT (as appropriate)
