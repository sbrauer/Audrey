from colander import null, Invalid
import bson.objectid
import bson.dbref
import audrey.resources.file

class ObjectId(object):
    """ colander type for a MongoDB ObjectId
    Serializes to/from a dict with the key "ObjectId" whose value is a
    string representation of the id.
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, bson.objectid.ObjectId):
           raise Invalid(node, '%r is not an ObjectId' % appstruct)
        return dict(ObjectId=str(appstruct))

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
        return id

    def cstruct_children(self, node, cstruct):
        return []

class DBRef(object):
    """ colander type for a MongoDB DBRef (collection name and _id,
    with optional database name)
    Serializes to/from a dict with the keys:
    - "collection" is the collection name 
    - "ObjectId" is a string representation of the id
    - "database" is the database name (missing if None)
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, bson.dbref.DBRef):
           raise Invalid(node, '%r is not a DBRef' % appstruct)
        ret = dict(collection=appstruct.collection, ObjectId=str(appstruct.id))
        if appstruct.database:
            ret['database'] = appstruct.database
        return ret

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, dict):
            raise Invalid(node, '%r is not a dict' % cstruct)
        if 'collection' not in cstruct:
            raise Invalid(node, '%r does not have a "collection" key' % cstruct)
        if 'ObjectId' not in cstruct:
            raise Invalid(node, '%r does not have a "ObjectId" key' % cstruct)
        try:
            id = bson.objectid.ObjectId(cstruct['ObjectId'])
        except bson.errors.InvalidId, e:
            raise Invalid(node, '%r is not a valid ObjectId' % cstruct['ObjectId'])
        collection = cstruct['collection']
        database = cstruct.get('database', None)
        return bson.dbref.DBRef(collection, id, database)

    def cstruct_children(self, node, cstruct):
        return []
    
class File(object):
    """ colander type for an audrey.resources.file.File
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
