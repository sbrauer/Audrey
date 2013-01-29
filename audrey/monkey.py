import pyramid_zcml

def patched_view(
    _context,
    permission=None,
    for_=None,
    view=None,
    name="",
    request_type=None,
    route_name=None,
    request_method=None,
    request_param=None,
    containment=None,
    attr=None,
    renderer=None,
    wrapper=None,
    xhr=None,  # was xhr=False in version 0.9.2
    accept=None,
    header=None,
    path_info=None,
    traverse=None,
    decorator=None,
    mapper=None,
    custom_predicates=(),
    context=None,
    cacheable=True, # not used, here for b/w compat < 0.8
    ):

    context = context or for_
    config = pyramid_zcml.with_context(_context)
    config.add_view(
        permission=permission, context=context, view=view, name=name,
        request_type=request_type, route_name=route_name,
        request_method=request_method, request_param=request_param,
        containment=containment, attr=attr, renderer=renderer,
        wrapper=wrapper, xhr=xhr, accept=accept, header=header,
        path_info=path_info, custom_predicates=custom_predicates,
        decorator=decorator, mapper=mapper)

def patch_zcml_view():
    """ Replace pyramid_zcml 0.9.2 view function """
    if pyramid_zcml.view.func_defaults == (None, None, None, '', None, None, None, None, None, None, None, None, False, None, None, None, None, None, None, (), None, True):
        pyramid_zcml.view = patched_view
