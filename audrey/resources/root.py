from bson.objectid import ObjectId
from os.path import basename
import pyes
from audrey import dateutil
from audrey import sortutil
from collections import OrderedDict
from audrey.resources.file import File

class Root(object):
    """
    The root of the application (starting point for traversal) and container
    of Collections.

    Developers extending Audrey should create their own subclass of Root
    that:

    * overrides either the :attr:`_collection_classes` class attribute or
      the :meth:`get_collection_classes` class method.  Either way, :meth:`get_collection_classes` should return a sequence of :class:`audrey.resources.collection.Collection` classes.
    """

    _collection_classes = ()

    @classmethod
    def get_collection_classes(cls):
        """ Returns a sequence of the Collection classes in this app.

        :rtype: sequence of :class:`audrey.resources.collection.Collection` classes
        """
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

    def get_collection(self, name):
        """ Return the Collection for the given ``name``.
        The returned Collection will have the Root object
        as its traversal ``__parent__``.

        :param name: a collection name
        :type name: string
        :rtype: :class:`audrey.resources.collection.Collection` class or ``None``
        """
        coll = None
        if name in self._collection_classes_by_name:
            coll = self._collection_classes_by_name[name](self.request)
            coll.__name__ = name
            coll.__parent__ = self
        return coll

    def __getitem__(self, name):
        ret = self.get_collection(name)
        if ret is None:
            raise KeyError
        return ret

    def get_collection_names(self):
        """ Get the names of the collections.

        :rtype: list of strings
        """
        return self._collection_classes_by_name.keys()

    def get_collections(self):
        """ Get all the collections.

        :rtype: list of :class:`audrey.resources.collection.Collection` instances
        """
        result = []
        for name in self.get_collection_names():
            result.append(self.get_collection(name))
        return result

    def get_mongo_connection(self):
        """ Return a connection to the MongoDB server.

        :rtype: :class:`pymongo.connection.Connection`
        """
        return self.request.registry.settings['mongo_conn']

    def get_mongo_db_name(self):
        """ Return the name of the MongoDB database.

        :rtype: string
        """
        return self.request.registry.settings['mongo_name']

    def get_mongo_db(self):
        """ Return the MongoDB database for the app.

        :rtype: :class:`pymongo.database.Database`
        """
        return self.request.registry.settings['mongo_db']

    def get_mongo_collection(self, coll_name):
        """ Return the collection identified by ``coll_name``.

        :rtype: :class:`pymongo.collection.Collection`
        """
        return self.get_mongo_db()[coll_name]

    def get_gridfs(self):
        """ Return the MongoDB GridFS for the app.

        :rtype: :class:`gridfs.GridFS`
        """
        return self.request.registry.settings['gridfs']
    
    def get_elastic_connection(self):
        """ Return a connection to the ElasticSearch server.
        May return ``None`` if no ElasticSearch connection is configured
        for the app.

        :rtype: :class:`pyes.es.ES` or ``None``
        """
        return self.request.registry.settings['elastic_conn']
    
    def get_elastic_index_name(self):
        """ Return the name of the ElasticSearch index.

        Note that all objects in an Audrey app will use the same Elastic
        index (the index name is analogous to a database name).

        :rtype: string
        """
        return self.request.registry.settings['elastic_name']

    def get_object_for_collection_and_id(self, collection_name, id, fields=None):
        """ Return the Object identified by the given ``collection_name``
        and ``id``.

        :param collection_name: name of a collection
        :type collection_name: string
        :param id: an ObjectId
        :type id: :class:`bson.objectid.ObjectId`
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
i       :param fields: like ``fields`` param to :meth:`audrey.resources.collection.Collection.get_children`)
        """
        coll = self.get_collection(collection_name)
        if coll is None:
            return None
        return coll.get_child_by_id(id, fields=fields)

    def get_object_for_reference(self, reference, fields=None):
        """ Return the Object identified by the given ``reference``.

        :param reference: a reference
        :type reference: :class:`audrey.resources.reference.Reference`
i       :param fields: like ``fields`` param to :meth:`audrey.resources.collection.Collection.get_children`)
        :rtype: :class:`audrey.resources.object.Object` class or ``None``
        """
        if reference is None:
            return None
        return self.get_object_for_collection_and_id(reference.collection, reference.id, fields=fields)

    def serve_gridfs_file_for_id(self, id):
        """ Attempt to serve the GridFS file referred to by ``id``.

        :param id: an ObjectId
        :type id: :class:`bson.objectid.ObjectId`
        :rtype: :class:`pyramid.response.Response` if a matching file was found in the GridFS, otherwise :class:`pyramid.httpexceptions.HTTPNotFound`
        """
        return File(id).serve(self.request)

    def create_gridfs_file(self, file, filename, mimetype, parents=None):
        """ Create a new GridFS file.

        :param file: file content/data
        :type file: a file-like object (providing a read() method) or a string
        :param filename: a filename
        :type filename: string
        :param mimetype: a mime-type
        :type mimetype: string
        :param parents: list of references to the Objects that "own" the file
        :type parents: list of :class:`bson.dbref.DBRef` instances, or ``None``
        :rtype: :class:`audrey.resources.file.File`
        """
        if parents is None: parents = []
        # FIXME: if image, get dimensions (via PIL?) and store as two custom attributes (width and height)
        return File(self.get_gridfs().put(file, filename=filename, contentType=mimetype, parents=parents, lastmodDate=dateutil.utcnow()))

    def create_gridfs_file_from_fieldstorage(self, fieldstorage, parents=None):
        """ Create a new GridFS file from the given ``fieldstorage``.

        :param fieldstorage: a FieldStorage (such as found in WebOb request.POST for each file upload)
        :type fieldstorage: :class:`cgi.FieldStorage`
        :param parents: list of references to the Objects that "own" the file
        :type parents: list of :class:`bson.dbref.DBRef` instances, or ``None``
        :rtype: :class:`audrey.resources.file.File`
        """
        filename = fieldstorage.filename
        # IE likes to include the full path of uploaded files ("c:\foo\bar.gif")
        if(len(filename) > 1 and filename[1] == ':'): filename = filename[2:]  # remove drive prefix
        filename = basename(filename.replace('\\', '/'))
        # FIXME: instead of trusting client's content-type, use python-magic to determine type server-side?
        mimetype = fieldstorage.headers.get('content-type')
        return self.create_gridfs_file(fieldstorage.file, filename, mimetype, parents)

    # FIXME: add a method to purge orphaned files (files where parents=[])
    # that were modified more than some cutoff ago (cutoff should be
    # an argument with a sane default... like 24 hrs).

    def search_raw(self, query=None, doc_types=None, **query_parms):
        """ A thin wrapper around :meth:`pyes.ES.search_raw`

        :param query: a :class:`pyes.query.Search` or a :class:`pyes.query.Query` or a custom dictionary of search parameters using the query DSL to be passed directly
        :param doc_types: which doc types to search
        :type doc_types: list of strings or ``None``
        :param query_parms: extra kwargs
        :rtype: dictionary

        The returned dictionary is like that returned by :meth:`pyes.ES.search_raw`

        Keys are ['hits', '_shards', 'took', 'timed_out'].
        
        result['took'] is the search time in ms

        result['hits'] has the keys: ['hits', 'total', 'max_score']

        result['hits']['total'] is total number of hits

        result['hits']['hits'] is a list of hit dictionaries, each with the keys: ['_score', '_type', '_id', '_source', '_index', 'highlight']
        Although if the ``fields`` kwarg is a list of field names (instead 
        of the default value ``None``), instead of a '_source' key, each hit will
        have a '_fields' key whose value is a dictionary of the requested fields.
        
        The "highlight" key will only be present if the query has highlight
        fields and there was a match in at least one of those fields.
        In that case, the value of "highlight" will be dictionary of strings.
        Each dictionary key is a field name and each string is an HTML fragment
        where the matched term is in an ``<em>`` tag.
        """
        econn = self.get_elastic_connection()
        if econn is None:
            raise RuntimeError("Use of ElasticSearch is disabled.")
        # Normalize query_parms by removing items where the value is None.
        keys = query_parms.keys()
        for key in keys:
            val = query_parms[key]
            if val == None:
                del query_parms[key]
        return econn.search_raw(query or {}, indices=(self.get_elastic_index_name(),), doc_types=doc_types, **query_parms)

    def get_objects_and_highlights_for_raw_search_results(self, results, object_fields=None):
        """ Given a ``pyes`` result dictionary (such as returned by
        :meth:`search_raw`) return a new dictionary with the keys:

        * "total": total number of matching hits
        * "took": search time in ms
        * "items": a list of dictionaries, each with the keys "object" and highlight"

i       :param object_fields: like ``fields`` param to :meth:`audrey.resources.collection.Collection.get_children`)
        """
        items = []
        for hit in results['hits']['hits']:
            _id = ObjectId(hit['_id'])
            collection_name = hit['_type']
            obj = self.get_object_for_collection_and_id(collection_name, _id, fields=object_fields)
            if obj:
                items.append(dict(object=obj, highlight=hit.get('highlight')))
        return dict(
            items = items,
            total = results['hits']['total'],
            took = results['took'],
        )

    def get_objects_for_raw_search_results(self, results, object_fields=None):
        """ Given a ``pyes`` result dictionary (such as returned by
        :meth:`search_raw`) return a new dictionary with the keys:

        * "total": total number of matching hits
        * "took": search time in ms
        * "items": a list of :class:`audrey.resources.object.Object` instances

i       :param object_fields: like ``fields`` param to :meth:`audrey.resources.collection.Collection.get_children`)
        """
        ret = self.get_objects_and_highlights_for_raw_search_results(results, object_fields=object_fields)
        ret['items'] = [item['object'] for item in ret['items']]
        return ret

    def get_objects_and_highlights_for_query(self, query=None, doc_types=None, object_fields=None, **query_parms):
        """ A convenience method that returns the result of calling 
        :meth:`get_objects_and_highlights_for_raw_search_results`
        on :meth:`search_raw` with the given parameters.
        """
        return self.get_objects_and_highlights_for_raw_search_results(self.search_raw(query=query, doc_types=doc_types, **query_parms), object_fields=object_fields)

    def get_objects_for_query(self, query=None, doc_types=None, object_fields=None, **query_parms):
        """ A convenience method that returns the result of calling 
        :meth:`get_objects_for_raw_search_results`
        on :meth:`search_raw` with the given parameters.
        """
        return self.get_objects_for_raw_search_results(self.search_raw(query=query, doc_types=doc_types, **query_parms), object_fields=object_fields)

    def basic_fulltext_search(self, search_string='', collection_names=None, skip=0, limit=10, sort=None, highlight_fields=None, object_fields=None):
        """ A functional basic full text search.
        Also a good example of using the other search methods.

        All parms are optional; calling the method without specifying any parms
        is querying for anything and everything.

        :param query: a query string that may contain wildcards or boolean operators
        :type query: string
        :param collection_names: restrict search to specific Collections
        :type collection_names: list of strings, or ``None``
        :param skip: number of results to omit from start of result set
        :type skip: integer
        :param limit: maximum number of results to return
        :type limit: integer
        :param sort: a :class:`audrey.sortutil.SortSpec` string
        :type sort: string or ``None``
        :param highlight_fields: a list of Elastic mapping fields in which to highlight ``search_string`` matches. For example, to highlight matches in Audrey's default full "text" field: ``['text']``
        :type highlight_fields: list of strings, or ``None``
i       :param object_fields: like ``fields`` param to :meth:`audrey.resources.collection.Collection.get_children`)
        :rtype: dictionary

        Returns a dictionary like :meth:`get_objects_and_highlights_for_raw_search_results` when ``highlight_fields``.  Otherwise returns a dictionary like :meth:`get_objects_for_raw_search_results`.
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
        return method(query=search, doc_types=collection_names, sort=elastic_sort, object_fields=object_fields)

    def clear_elastic(self):
        """ Delete all documents from Elastic for all Collections.
        """
        for coll in self.get_collections():
            coll.clear_elastic()

    def reindex_all(self, clear=False):
        """ Reindex all documents in Elastic for all Collections.
        Returns a count of the objects reindexed.

        :param clear: Should we clear the index first?
        :type clear: boolean
        :rtype: integer
        """
        count = 0
        for coll in self.get_collections():
            count += coll.reindex_all(clear=clear)
        return count
