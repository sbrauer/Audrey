from bson.dbref import DBRef
from pyramid.traversal import find_root

class Reference(object):
    """ Represents a reference to a document in MongoDB.
    Similar to Mongo's standard DBRef, but has an option
    to serialize only the ID, which can be more space/bandwidth
    efficient when the reference will always be to the same 
    collection.
    """
    def __init__(self, collection, id, serialize_id_only=False):
        self.collection = collection
        self.id = id
        self.serialize_id_only = serialize_id_only

    def __json__(self, request):
        if self.serialize_id_only:
            return dict(ObjectId=str(self.id))
        else:
            return dict(collection=self.collection, ObjectId=str(self.id))

    def to_mongo(self):
        if self.serialize_id_only:
            return self.id
        else:
            return DBRef(self.collection, self.id)

    def dereference(self, context):
        """ Return the :class:`Object` this Reference refers to.
        ``context`` can be any resource and is simply used to find the root
        (which in turn is used to resolve the reference).
        """
        root = find_root(context)
        return root.get_object_for_reference(self)

class IdReference(Reference):
    """ Just a little syntactic sugar around :class:`Reference`
    with ``serialize_id_only`` = ``True``.
    """
    def __init__(self, collection, id):
        Reference.__init__(self, collection, id, serialize_id_only=True)
