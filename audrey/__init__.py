from pyramid.config import Configurator
from pyramid.settings import aslist
import pymongo
from gridfs import GridFS
import pyes
from audrey.resources import root_factory, root

from pyramid.renderers import JSON
import datetime
from bson.objectid import ObjectId
from bson.dbref import DBRef

# TODO: After pyramid_zcml 0.9.3 is out, require that version as min,
# and remove this monkey business.
# See https://github.com/Pylons/pyramid_zcml/pull/5/files
from audrey.monkey import patch_zcml_view
patch_zcml_view()

def audrey_main(root_factory, root_cls, global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Handle custom settings that require type conversion.
    mongo_uri = aslist(settings['mongo_uri'])
    settings['mongo_uri'] = mongo_uri
    elastic_uri = aslist(settings['elastic_uri'])
    settings['elastic_uri'] = elastic_uri
    # If "elastic_name" setting not found, fallback to "mongo_name".
    if 'elastic_name' not in settings:
        settings['elastic_name'] = settings['mongo_name']

    elastic_basic_auth_username = settings.get('elastic_basic_auth_username')
    elastic_basic_auth_password = settings.get('elastic_basic_auth_password')

    # Standard Pyramid ZCML configuration.
    config = Configurator(root_factory=root_factory, settings=settings)

    json_renderer = JSON()
    def datetime_adapter(obj, request):
        return obj.isoformat()
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    def objectid_adapter(obj, request):
        return dict(ObjectId=str(obj))
    json_renderer.add_adapter(ObjectId, objectid_adapter)
    def dbref_adapter(obj, request):
        ret = dict(collection=obj.collection, ObjectId=str(obj.id))
        if obj.database:
            ret['database'] = obj.database
        return ret
    json_renderer.add_adapter(DBRef, dbref_adapter)
    config.add_renderer('json', json_renderer)

    zcml_file = settings.get('configure_zcml', 'configure.zcml')
    config.include('pyramid_zcml')
    config.load_zcml(zcml_file)

    # Do initialization based on custom settings.
    mongo_conn = pymongo.Connection(mongo_uri, tz_aware=True)
    mongo_db = mongo_conn[settings['mongo_name']]
    # Note that for simplicity we use one GridFS (the default "fs")
    # for the entire DB/webapp.
    gridfs = GridFS(mongo_db)
    config.registry.settings['mongo_conn'] = mongo_conn
    config.registry.settings['mongo_db'] = mongo_db
    config.registry.settings['gridfs'] = gridfs
    ensure_mongo_indexes(mongo_db, root_cls)

    # Not all projects will use Elastic.
    elastic_conn = None
    if elastic_uri:
        basic_auth = None
        if elastic_basic_auth_username:
            basic_auth = dict(username=elastic_basic_auth_username,
                              password=elastic_basic_auth_password)
        elastic_conn = pyes.ES(elastic_uri, basic_auth=basic_auth)
        ensure_elastic_index(elastic_conn, settings['elastic_name'], root_cls)
    config.registry.settings['elastic_conn'] = elastic_conn

    # Finally, return a wsgi app.
    return config.make_wsgi_app()

def ensure_mongo_indexes(db, root_cls):
    for coll_cls in root_cls.get_collection_classes():
        mongo_coll = db[coll_cls._collection_name]
        for (key_or_list, kwargs) in coll_cls.get_mongo_indexes():
            mongo_coll.ensure_index(key_or_list, **kwargs)

def ensure_elastic_index(conn, idx_name, root_cls):
    # Not working w/ pyes-0.19.1
    # See https://github.com/aparo/pyes/issues/69
    #conn.indices.create_index_if_missing(idx_name)
    if not conn.indices.exists_index(idx_name):
        conn.indices.create_index(idx_name)
    for coll_cls in root_cls.get_collection_classes():
        if coll_cls._use_elastic:
            conn.indices.put_mapping(coll_cls._collection_name, {'properties':coll_cls.get_elastic_mapping()}, [idx_name])

def main(global_config, **settings):  # pragma: no cover
    return audrey_main(root_factory, root.Root, global_config, **settings)
