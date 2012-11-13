import unittest
from pyramid import testing

# FIXME: this is just the default from the starter scaffold
class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info['project'], 'Audrey')

import datetime
today = datetime.datetime.utcnow().date()
today_with_time = datetime.datetime.combine(today, datetime.time())

classes = {}

def _getBaseObjectClass():
    from audrey import resources
    return resources.object.BaseObject

def _getExampleBaseObjectClass():
    TYPE_NAME = 'example_base_object'
    if TYPE_NAME in classes: return classes[TYPE_NAME]
    from audrey import resources
    import colander
    class ExampleBaseObject(resources.object.BaseObject):
        _object_type = TYPE_NAME
        @classmethod
        def get_class_schema(cls, request=None):
            schema = colander.SchemaNode(colander.Mapping())
            schema.add(colander.SchemaNode(colander.String(), name='title'))
            schema.add(colander.SchemaNode(colander.String(), name='body', is_html=True))
            schema.add(colander.SchemaNode(colander.Date(), name='dateline'))
            schema.add(colander.SchemaNode(colander.Sequence(), colander.SchemaNode(colander.String()), name='tags', missing=[], default=[]))
            return schema
    classes[TYPE_NAME] = ExampleBaseObject
    return ExampleBaseObject

def _getExampleBaseCollectionClass():
    TYPE_NAME = 'example_base_collection'
    if TYPE_NAME in classes: return classes[TYPE_NAME]
    from audrey import resources
    class ExampleBaseCollection(resources.collection.BaseCollection):
        _collection_name = TYPE_NAME
        _object_classes = (_getExampleBaseObjectClass(),)
    classes[TYPE_NAME] = ExampleBaseCollection
    return ExampleBaseCollection

def _getExampleNamingObjectClass():
    TYPE_NAME = 'example_naming_object'
    if TYPE_NAME in classes: return classes[TYPE_NAME]
    from audrey import resources
    import colander
    class ExampleNamingObject(resources.object.NamedObject):
        _object_type = TYPE_NAME
        @classmethod
        def get_class_schema(cls, request=None):
            schema = colander.SchemaNode(colander.Mapping())
            schema.add(colander.SchemaNode(colander.String(), name='title'))
            return schema
    classes[TYPE_NAME] = ExampleNamingObject
    return ExampleNamingObject

def _getExampleNamingCollectionClass():
    TYPE_NAME = 'example_naming_collection'
    if TYPE_NAME in classes: return classes[TYPE_NAME]
    from audrey import resources
    class ExampleNamingCollection(resources.collection.NamingCollection):
        _collection_name = TYPE_NAME
        _object_classes = (_getExampleNamingObjectClass(),)
    classes[TYPE_NAME] = ExampleNamingCollection
    return ExampleNamingCollection

def _getExampleRootClass():
    TYPE_NAME = 'example_root'
    if TYPE_NAME in classes: return classes[TYPE_NAME]
    from audrey import resources
    class ExampleRoot(resources.root.Root):
        _collection_classes = (_getExampleBaseCollectionClass(), _getExampleNamingCollectionClass(), )
    classes[TYPE_NAME] = ExampleRoot
    return ExampleRoot

def _makeOneRoot(request):
    return _getExampleRootClass()(request)

def _makeOneBaseObject(request, title='A Title', body='<p>Some body.</p>', dateline=today, tags=set(['foo', 'bar'])):
    return _getExampleBaseObjectClass()(request, title=title, dateline=dateline, body=body, tags=tags)

def _makeOneBaseCollection(request):
    return _getExampleBaseCollectionClass()(request)

def _makeOneNamingObject(request, name, title='A Title'):
    return _getExampleNamingObjectClass()(request, __name__=name, title=title)

def _makeOneNamingCollection(request):
    return _getExampleNamingCollectionClass()(request)

class UtilTests(unittest.TestCase):

    def test_dateutil(self):
        import datetime, pytz
        from audrey import dateutil
        utc_dt_aware = datetime.datetime(2012, 7, 4, 16, 20, tzinfo=pytz.utc)
        utc_dt_naive = datetime.datetime(2012, 7, 4, 16, 20)
        est_dt_aware = datetime.datetime(2012, 7, 4, 11, 20, tzinfo=pytz.timezone('US/Eastern'))
        est_dt_naive = datetime.datetime(2012, 7, 4, 11, 20)
        self.assertEqual(dateutil.convert_aware_datetime(utc_dt_aware, 'US/Eastern'), est_dt_aware)
        self.assertEqual(dateutil.convert_aware_datetime(est_dt_aware, 'utc'), utc_dt_aware)
        self.assertEqual(dateutil.convert_naive_datetime(utc_dt_naive, 'utc', 'US/Eastern'), est_dt_aware)
        self.assertEqual(dateutil.convert_naive_datetime(est_dt_naive, 'US/Eastern', 'utc'), utc_dt_aware)
        self.assertEqual(dateutil.make_naive(est_dt_aware), est_dt_naive)

        now_zero = dateutil.utcnow(zero_seconds=True)
        now_later = dateutil.utcnow(zero_seconds=False)
        self.assertEqual(now_zero.second, 0)
        self.assertTrue(now_later > now_zero)
        self.assertEqual(now_zero.tzinfo, pytz.utc)
        self.assertEqual(now_later.tzinfo, pytz.utc)

    def test_htmlutil_sniff(self):
        from audrey import htmlutil
        self.assertTrue(htmlutil.sniff_html('''This is some <em>html</em>.'''))
        self.assertFalse(htmlutil.sniff_html('''No html here.'''))

    def test_exceptions(self):
        from audrey import exceptions
        msg = "Sheesh!"
        self.assertEqual(exceptions.Veto(msg).args[0], msg)

    def test_htmlutil_html_to_text(self):
        from audrey import htmlutil
        self.assertEqual(htmlutil.html_to_text(u'''<html><head><title>Title</title></head><body><h1>Header1</h1><p>Hello <unknown foo="bar">world!</unknown> Perhaps some other &#198;on...<br/><a href="http://python.org">Ooh, a link!</a><ul><li>animal</li><li>vegetable</li><li>mineral</li></ul></p><p>&copy; 2012</p></body></html>'''), u'''Header1\n\n\n\nHello world! Perhaps some other \xc6on...\nOoh, a link!\n\n- animal\n\n- vegetable\n\n- mineral\n\n\xa9 2012''')
        self.assertEqual(htmlutil.html_to_text('''<a href="http://python.org">Ooh, a link!</a>''', show_link_urls=True), '''Ooh, a link! [http://python.org]''')
        self.assertEqual(htmlutil.html_to_text('''Foo &meh; Bar''', unknown_entity_replacement='?'), 'Foo ? Bar')

    def test_sortutil(self):
        from audrey import sortutil
        self.assertTrue(sortutil.sort_string_to_mongo('foo,-bar,+baz'), [('foo', 1), ('bar', -1), ('baz', 1)])
        self.assertTrue(sortutil.sort_string_to_elastic('foo,-bar,+baz'), 'foo,bar:desc,baz'), 
        self.assertTrue(sortutil.SortSpec('foo,-bar,+baz').to_string(pluses=True), '+foo,-bar,+baz')
        self.assertTrue(str(sortutil.SortSpec('foo,-bar,+baz')), 'foo,-bar,baz')

class RootTests(unittest.TestCase):
    def test_constructor(self):
        request = testing.DummyRequest()
        instance = _makeOneRoot(request)
        self.assertEqual(instance.__name__, "")
        self.assertEqual(instance.__parent__, None)

class ObjectTests(unittest.TestCase):
    def test_get_schema(self):
        self.assertEqual(len(_getBaseObjectClass().get_class_schema().children), 0)
        self.assertEqual(len(_getExampleBaseObjectClass().get_class_schema().children), 4)

    def test_constructor(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        self.assertEqual(instance.title, "A Title")
        self.assertEqual(instance._created, None)

    def test_use_elastic(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        coll = _makeOneBaseCollection(request)
        instance.__parent__ = coll
        self.assertTrue(instance.use_elastic())
        coll._use_elastic = False
        self.assertFalse(instance.use_elastic())

    def test_get_nonschema_values(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        vals = instance.get_nonschema_values()
        self.assertTrue('_id' not in vals)
        self.assertTrue('_created' in vals)
        instance._id = 'test'
        vals = instance.get_nonschema_values()
        self.assertTrue('_id' in vals)

    def test_get_schema_values(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        vals = instance.get_schema_values()
        self.assertEqual(vals['title'], 'A Title')
        self.assertEqual(vals['body'], '<p>Some body.</p>')

    def test_get_mongo_save_doc(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        doc = instance.get_mongo_save_doc()
        self.assertEqual(doc, {'body': '<p>Some body.</p>', '_created': None, '_modified': None, 'title': 'A Title', 'dateline': today_with_time, 'tags': ['foo', 'bar']})

    def test_load_mongo_doc(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request, title='x', body='x', tags=[])
        self.assertEqual(instance.title, "x")
        self.assertEqual(instance.body, "x")
        self.assertEqual(instance.tags, [])
        instance.load_mongo_doc({'body': 'Some body.', '_created': None, '_modified': None, 'title': 'A Title', 'tags': ['foo', 'bar']})
        self.assertEqual(instance.title, "A Title")
        self.assertEqual(instance.body, "Some body.")
        self.assertEqual(instance.tags, ['foo', 'bar'])

    def test_get_elastic_index_doc(self):
        request = testing.DummyRequest()
        instance = _makeOneBaseObject(request)
        doc = instance.get_elastic_index_doc()
        self.assertEqual(doc, {'text': 'A Title\nSome body.\nfoo\nbar', '_modified': None, '_created': None})
        
class FunctionalTests(unittest.TestCase):

    def setUp(self):
        settings = dict(
            mongo_uri = "mongodb://127.0.0.1",
            mongo_name = "audrey_unittests",
            elastic_uri = "thrift://127.0.0.1:9500",
        )
        import audrey
        root_cls = _getExampleRootClass()
        self.app = audrey.audrey_main(root_cls, root_cls, {}, **settings)
        self.mongo_conn = self.app.registry.settings['mongo_conn']
        self.elastic_conn = self.app.registry.settings['elastic_conn']
        self.settings = self.app.registry.settings
        self.request = testing.DummyRequest()
        self.request.registry = self.app.registry

    def tearDown(self):
        db = self.mongo_conn[self.settings['mongo_name']]
        names = db.collection_names()
        for name in names:
            if name == 'system.indexes': continue
            db.drop_collection(name)
        self.mongo_conn.disconnect()
        
        self.elastic_conn.close_index(self.settings['elastic_name'])
        self.elastic_conn.delete_index(self.settings['elastic_name'])

    def test_add_child(self):
        root = _makeOneRoot(self.request)
        collection = root['example_base_collection']
        instance = _makeOneBaseObject(self.request)
        self.assertEqual(instance._id, None)
        self.assertEqual(instance._created, None)
        self.assertEqual(instance._modified, None)
        collection.add_child(instance)
        self.assertNotEqual(instance._id, None)
        self.assertNotEqual(instance._created, None)
        self.assertNotEqual(instance._modified, None)
        self.assertEqual(instance.__name__, str(instance._id))
        self.assertEqual(instance.__parent__, collection)

    def test_basic_crud(self):
        root = _makeOneRoot(self.request)
        collection = root['example_base_collection']
        instance = _makeOneBaseObject(self.request)
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 0)
        collection.add_child(instance)
        child_name = instance.__name__
        self.assertTrue(collection.has_child_with_name(child_name))
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]._id, instance._id)

        # Get another copy of the same object and compare attribute vals.
        instance2 = collection.get_child_by_name(child_name)
        self.assertEqual(instance._id, instance2._id)
        self.assertEqual(instance.title, instance2.title)
        self.assertEqual(instance.body, instance2.body)
        # Note that sets going into mongo become lists.
        self.assertEqual(list(instance.tags), list(instance2.tags))
        # Note that dates going into mongo become datetimes (with 0 hr,min,sec).
        self.assertEqual(instance.dateline, instance2.dateline.date())
        
        # Delete the child and make sure mongo and elastic are updated.
        collection.delete_child_by_name(child_name)
        self.assertFalse(collection.has_child_with_name(child_name))
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 0)

    def test_unindex_notfound(self):
        instance = _makeOneBaseObject(self.request)
        root = _makeOneRoot(self.request)
        collection = root['example_base_collection']
        collection.add_child(instance)
        self.assertEqual(instance.unindex(), 1)
        self.assertEqual(instance.unindex(), 0)

    def test_naming_crud(self):
        root = _makeOneRoot(self.request)
        collection = root['example_naming_collection']
        name = 'name1'
        instance = _makeOneNamingObject(self.request, name)
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 0)
        collection.add_child(instance)
        self.assertTrue(collection.has_child_with_name(name))
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]._id, instance._id)
        # FIXME: do a search by name
        collection.delete_child_by_name(name)
        self.assertFalse(collection.has_child_with_name(name))
        result = root.basic_fulltext_search()
        self.assertEqual(result['total'], 0)
    # FIXME... test renames, and test query/search results with more than one object of each type

