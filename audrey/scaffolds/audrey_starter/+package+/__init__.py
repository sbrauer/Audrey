import audrey
from .resources import root_factory, Root

def main(global_config, **settings): # pragma: no cover
    """ This function returns a Pyramid WSGI application.
    """
    return audrey.audrey_main(root_factory, Root, global_config, **settings)
