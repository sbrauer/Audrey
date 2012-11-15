from pyramid.decorator import reify
from bson.objectid import ObjectId
import pyes
from audrey import sortutil
from collections import OrderedDict

class Root(object):

    # Developers extending Audrey should create their own subclass of Root
    # that overrides either the _collection_classes attribute or
    # the get_collection_classes() class method.
    # Either way, get_collection_classes() should return 
    # a sequence of Collection classes.

    _collection_classes = ()

    @classmethod
    def get_collection_classes(cls):
        return cls._collection_classes

    def __init__(self, request):
        self.request = request
        self.__name__ = ''
        self.__parent__ = None
        self._collection_classes_by_name = OrderedDict()
        for coll_cls in self.get_collection_classes():
            coll_name = coll_cls._collection_name
            if coll_name in self._collection_classes_by_name:
                raise ValueError("Non-unique collection name: %s" % coll_name)
            self._collection_classes_by_name[coll_name] = coll_cls

    def get_child(self, name):
        child = None
        if name in self._collection_classes_by_name:
            child = self._collection_classes_by_name[name](self.request)
            child.__name__ = name
            child.__parent__ = self
        return child

    def __getitem__(self, name):
        child = self.get_child(name)
        if child is None:
            raise KeyError
        return child

    def get_child_names(self):
        return self._collection_classes_by_name.keys()

    def get_children(self):
        result = []
        for name in self.get_child_names():
            result.append(self[name])
        return result

    def get_mongo_connection(self):
        return self.request.registry.settings['mongo_conn']

    def get_mongo_db_name(self):
        return self.request.registry.settings['mongo_name']

    @reify
    def _mongo_db(self):
        return self.get_mongo_connection()[self.get_mongo_db_name()]

    def get_mongo_collection(self, coll_name):
        return self._mongo_db[coll_name]
    
    def get_elastic_connection(self):
        return self.request.registry.settings['elastic_conn']
    
    def get_elastic_index_name(self):
        return self.request.registry.settings['elastic_name']

    def get_object_for_collection_and_id(self, collection_name, id):
        coll = self.get_child(collection_name)
        return coll.get_child_by_id(id)

    def search_raw(self, query=None, doc_types=None, **query_parms):
        """ A thin wrapper around pyes.ES.search_raw().
        query must be a Search object, a Query object, or a custom dictionary of search parameters using the query DSL to be passed directly.

        Returns a dictionary like pyes.ES.search_raw().
        Keys are [u'hits', u'_shards', u'took', u'timed_out'].
        result['hits'] has the keys: [u'hits', u'total', u'max_score']
        
        result['took'] -> search time in ms
        result['hits']['total'] -> total number of hits
        result['hits']['hits'] -> list of hit dictionaries, each with the keys: [u'_score', u'_type', u'_id', u'_source', u'_index', u'highlight']
        Although if the fields kwarg is a list of field names (instead 
        of the default value None), instead of a '_source' key, each hit will
        have a '_fields' key whose value is a dictionary of the requested fields.
        
        The "highlight" key will only be present if highlight_fields were used
        and there was a match in at least one of those fields.
        In that case, the value of "highlight" will be dictionary of strings.
        Each dictionary key is a field name and each string is an HTML fragment
        where the matched term is in an <em> tag.
        """
        # Normalize query_parms by removing items where the value is None.
        keys = query_parms.keys()
        for key in keys:
            val = query_parms[key]
            if val == None:
                del query_parms[key]
        return self.get_elastic_connection().search_raw(query or {}, indices=(self.get_elastic_index_name(),), doc_types=doc_types, **query_parms)

    def get_objects_and_highlights_for_raw_search_results(self, results):
        """ Given a pyes result dictionary (such as returned by search_raw(),
        return a dictionary with the keys:
        "total": total number of matching hits
        "took": search time in ms
        "items": a list of dictionaries, each with the keys "object" and highlight"
        """
        items = []
        for hit in results['hits']['hits']:
            _id = ObjectId(hit['_id'])
            collection_name = hit['_type']
            obj = self.get_object_for_collection_and_id(collection_name, _id)
            if obj:
                items.append(dict(object=obj, highlight=hit.get('highlight')))
        return dict(
            items = items,
            total = results['hits']['total'],
            took = results['took'],
        )

    def get_objects_for_raw_search_results(self, results):
        """ Given a pyes result dictionary (such as returned by search_raw(),
        return a dictionary with the keys:
        "total": total number of matching hits
        "took": search time in ms
        "items": a list of Objects
        """
        ret = self.get_objects_and_highlights_for_raw_search_results(results)
        ret['items'] = [item['object'] for item in ret['items']]
        return ret

    def get_objects_and_highlights_for_query(self, query=None, doc_types=None, **query_parms):
        return self.get_objects_and_highlights_for_raw_search_results(self.search_raw(query=query, doc_types=doc_types, **query_parms))

    def get_objects_for_query(self, query=None, doc_types=None, **query_parms):
        return self.get_objects_for_raw_search_results(self.search_raw(query=query, doc_types=doc_types, **query_parms))

    def basic_fulltext_search(self, search_string='', collection_names=None, skip=0, limit=10, sort=None, highlight_fields=None):
        """ A functional basic full text search.
        Also a good example of using Root's other search methods.

        All parms are optional...
        query - query string that may contain wildcards or boolean operators
        collection_names - use to restrict search to specific Collections
        skip and limit - used for batching/pagination
        sort - a sortutil.SortSpec string
        highlight_fields - a list of Elastic mapping fields in which to highlight search_string matches; example: ['text']

        Returns a dictionary like get_objects_and_highlights_for_raw_search_results when highlight_fields.
        Otherwise returns a dictionary like get_objects_for_raw_search_results.
        """
        search_string = search_string.strip()
        if search_string:
            query = pyes.StringQuery(search_string)
        else:
            query = pyes.MatchAllQuery()
        # Set fields=[] since we only need _id and _type (which are always
        # in Elastic results) to get the objects out of MongoDB.
        # Retrieving _source would just waste resources.
        search = pyes.Search(query=query, fields=[], start=skip, size=limit)
        if highlight_fields:
            for hf in highlight_fields:
                search.add_highlight(hf)
        elastic_sort = sort and sortutil.sort_string_to_elastic(sort) or None
        method = highlight_fields and self.get_objects_and_highlights_for_query or self.get_objects_for_query
        return method(query=search, doc_types=collection_names, sort=elastic_sort)

    def _clear_elastic(self):
        """ Delete all documents from Elastic for all Collections.
        """
        for coll in self.get_children():
            coll._clear_elastic()

    # Returns the number of objects indexed.
    def _reindex_all(self, clear=False):
        """ Reindex all documents in Elastic for all Collections.
        """
        count = 0
        for coll in self.get_children():
            count += coll._reindex_all(clear=clear)
        return count
