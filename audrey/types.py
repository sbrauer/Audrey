from colander import null, Invalid
import bson.objectid
import bson.dbref
import audrey.resources.file

class ObjectId(object):
    """ colander type for serializing an ObjectId to a string
    and deserializing it back.
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, bson.objectid.ObjectId):
           raise Invalid(node, '%r is not an ObjectId' % appstruct)
        return str(appstruct)

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, basestring):
            raise Invalid(node, '%r is not a string' % cstruct)
        return bson.objectid.ObjectId(cstruct)

    def cstruct_children(self, node, cstruct):
        return []

# FIXME: perhaps instead of a delimited string, we should
# serialize to/from a dictionary with keys "collection", "id" and "database"
class DBRef(object):
    """ colander type for serializing a DBRef (collection name and _id)
    to a string and deserializing it back.
    The string format is "collection:_id".
    If an optional database name is used, it's "collection:_id:database".
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, bson.dbref.DBRef):
           raise Invalid(node, '%r is not a DBRef' % appstruct)
        parts = [appstruct.collection, str(appstruct.id)]
        if appstruct.database: parts.append(appstruct.database)
        return ':'.join(parts)

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, basestring):
            raise Invalid(node, '%r is not a string' % cstruct)
        parts = cstruct.split(':')
        if len(parts) not in (2,3):
            raise Invalid(node, '%r is not in the expected format.' % cstruct)
        collection = parts[0]
        id = bson.objectid.ObjectId(parts[1])
        if len(parts) == 3:
            database = parts[2]
        else:
            database = None
        return bson.dbref.DBRef(collection, id, database)

    def cstruct_children(self, node, cstruct):
        return []
    
class GridFile(object):
    """ colander type for serializing an audrey.resources.file.File
    to a string (representing an ObjectId) and back.
    """
    def serialize(self, node, appstruct):
        if appstruct is null:
            return null
        if not isinstance(appstruct, audrey.resources.file.File):
           raise Invalid(node, '%r is not a File' % appstruct)
        return str(appstruct._id)

    def deserialize(self, node, cstruct):
        if cstruct is null:
           return null
        if not isinstance(cstruct, basestring):
            raise Invalid(node, '%r is not a string' % cstruct)
        return audrey.resources.file.File(bson.objectid.ObjectId(cstruct))

    def cstruct_children(self, node, cstruct):
        return []
