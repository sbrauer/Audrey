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


def _getBaseObjectClass():
    from audrey import resources
    return resources.object.BaseObject

def _getExampleObjectClass():
    from audrey import resources
    import colander
    class ExampleObject(resources.object.BaseObject):
        _object_type = 'example_object'
        @classmethod
        def get_class_schema(cls, request=None):
            schema = colander.SchemaNode(colander.Mapping())
            schema.add(colander.SchemaNode(colander.String(), name='title'))
            schema.add(colander.SchemaNode(colander.String(), name='body'))
            return schema
    return ExampleObject

def _getExampleCollectionClass():
    from audrey import resources
    class ExampleCollection(resources.collection.BaseCollection):
        _collection_name = 'example_collection'
        _object_classes = (_getExampleObjectClass(),)
    return ExampleCollection

def _getExampleRootClass():
    from audrey import resources
    class ExampleRoot(resources.root.Root):
        _collection_classes = (_getExampleCollectionClass(),)
    return ExampleRoot

def _makeOneRoot(request):
    return _getExampleRootClass()(request)

def _makeOneObject(request, title='A Title', body='Some body.'):
    return _getExampleObjectClass()(request, title=title, body=body)

def _makeOneCollection(request):
    return _getExampleCollectionClass()(request)

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
        self.assertEqual(len(_getExampleObjectClass().get_class_schema().children), 2)

    def test_constructor(self):
        request = testing.DummyRequest()
        instance = _makeOneObject(request)
        self.assertEqual(instance.title, "A Title")
        self.assertEqual(instance._created, None)

    def test_use_elastic(self):
        request = testing.DummyRequest()
        instance = _makeOneObject(request)
        coll = _makeOneCollection(request)
        instance.__parent__ = coll
        self.assertTrue(instance.use_elastic())
        coll._use_elastic = False
        self.assertFalse(instance.use_elastic())

    def test_get_nonschema_values(self):
        request = testing.DummyRequest()
        instance = _makeOneObject(request)
        vals = instance.get_nonschema_values()
        self.assertTrue('_id' not in vals)
        self.assertTrue('_created' in vals)
        instance._id = 'test'
        vals = instance.get_nonschema_values()
        self.assertTrue('_id' in vals)
        
