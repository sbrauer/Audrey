from colander import null, Invalid
import bson.objectid
import bson.dbref
import audrey.resources.file
import audrey.resources.reference

class Reference(object):
    """ colander type representing an audrey.resources.reference.Reference.

    This type constructor accepts one argument:

    ``collection``
       The name of the :class:`audrey.resources.collection.Collection`
       that this reference will always refer to.
       May be None if this reference may refer to multiple collections.

       When collection is None, the Reference is serialized to and 
       deserialized from a dict with the keys:
       "ObjectId"
       "collection"

       When collection is not None, the dictionary will only
       have the "ObjectId" key.
    """
    def __init__(self, collection=None):
        self.collection = collection

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, audrey.resources.reference.Reference):
           raise Invalid(node, '%r is not a Reference' % appstruct)
        ret = dict(ObjectId=str(appstruct.id))
        if self.collection is None:
            ret['collection'] = appstruct.collection
        return ret

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, dict):
            raise Invalid(node, '%r is not a dict' % cstruct)
        if 'ObjectId' not in cstruct:
            raise Invalid(node, '%r does not have a "ObjectId" key' % cstruct)
        try:
            id = bson.objectid.ObjectId(cstruct['ObjectId'])
        except bson.errors.InvalidId, e:
            raise Invalid(node, '%r is not a valid ObjectId' % cstruct['ObjectId'])
        if self.collection is None:
            if 'collection' not in cstruct:
                raise Invalid(node, '%r does not have a "collection" key' % cstruct)
            collection = cstruct['collection']
        else:
            collection = self.collection
        return audrey.resources.reference.Reference(collection, id)

    def cstruct_children(self, node, cstruct):
        return []

class File(object):
    """ colander type representing an audrey.resources.file.File
    Serializes to/from a dict with the key "FileId" whose value is a
    string representation of the file's ID in the GridFS.
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, audrey.resources.file.File):
           raise Invalid(node, '%r is not a File' % appstruct)
        return dict(FileId=str(appstruct._id))

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, dict):
            raise Invalid(node, '%r is not a dict' % cstruct)
        if 'FileId' not in cstruct:
            raise Invalid(node, '%r does not have a "FileId" key' % cstruct)
        try:
            id = bson.objectid.ObjectId(cstruct['FileId'])
        except bson.errors.InvalidId, e:
            raise Invalid(node, '%r is not a valid ObjectId' % cstruct['FileId'])
        return audrey.resources.file.File(id)

    def cstruct_children(self, node, cstruct):
        return []
