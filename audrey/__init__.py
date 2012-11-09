from pyramid.config import Configurator
from pyramid.settings import aslist
from audrey.resources import root_factory, root
import pymongo
import pyes

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    
    # Handle custom settings that require type conversion.
    mongo_uri = aslist(settings['mongo_uri'])
    settings['mongo_uri'] = mongo_uri
    elastic_uri = aslist(settings['elastic_uri'])
    settings['elastic_uri'] = elastic_uri
    elastic_timeout = float(settings.get('elastic_timeout', '5.0'))
    settings['elastic_timeout'] = elastic_timeout

    # Standard Pyramid ZCML configuration.
    config = Configurator(root_factory=root_factory, settings=settings)
    zcml_file = settings.get('configure_zcml', 'configure.zcml')
    config.include('pyramid_zcml')
    config.load_zcml(zcml_file)

    # Do initialization based on custom settings.
    mongo_conn = pymongo.Connection(mongo_uri, tz_aware=True)
    config.registry.settings['mongo_conn'] = mongo_conn
    ensure_mongo_indexes(mongo_conn, settings['mongo_name'])

    # Not all projects will use Elastic.
    elastic_conn = None
    if elastic_uri:
        elastic_conn = pyes.ES(elastic_uri, timeout=elastic_timeout)
        ensure_elastic_index(elastic_conn, settings['elastic_name'])
    config.registry.settings['elastic_conn'] = elastic_conn

    # Finally, return a wsgi app.
    return config.make_wsgi_app()

def ensure_mongo_indexes(conn, db_name):
    db = conn[db_name]
    for coll_cls in root.Root.get_collection_classes():
        cls.ensure_mongo_indexes(db)

def ensure_elastic_index(conn, idx_name):
    conn.create_index_if_missing(idx_name)
    for coll_cls in root.Root.get_collection_classes():
        cls.put_elastic_mappings(conn, idx_name)
