from bson.dbref import DBRef

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
