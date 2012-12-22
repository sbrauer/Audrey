import audrey
import audrey.types
import colander

# The following classes are just some examples to get you started with Audrey.
# For the sake of an example, the Person type (and People collection)
# are non-naming, while the Post type (and Posts collection) are naming.
# Whether or not to use names depends on your app and how meaningful
# (or not) you want your URLs to be.

class Person(audrey.resources.object.Object):
    _object_type = "person"

    @classmethod
    def get_class_schema(cls, request=None):
        schema = colander.SchemaNode(colander.Mapping())
        schema.add(colander.SchemaNode(colander.String(), name='firstname'))
        schema.add(colander.SchemaNode(colander.String(), name='lastname'))
        schema.add(colander.SchemaNode(audrey.types.File(), name='photo',
                                       default=None, missing=None))
        return schema

    def _title(self):
        parts = []
        for att in ('firstname', 'lastname'):
            val = getattr(self, att, '')
            if val:
                parts.append(val)
        if parts:
            return " ".join(parts)
        else:
            return "Untitled"

class People(audrey.resources.collection.Collection):
    _collection_name = 'people'
    _object_classes = (Person,)

class Post(audrey.resources.object.NamedObject):
    _object_type = "post"

    @classmethod
    def get_class_schema(cls, request=None):
        schema = colander.SchemaNode(colander.Mapping())
        schema.add(colander.SchemaNode(colander.String(), name='title'))
        schema.add(colander.SchemaNode(colander.DateTime(), name='dateline',
                                       missing=audrey.dateutil.utcnow()))
        schema.add(colander.SchemaNode(colander.String(), name='body',
                                       is_html=True))
        schema.add(colander.SchemaNode(
            audrey.types.Reference(collection='people'),
            name='author', default=None, missing=None))
        return schema

    def _title(self):
        return getattr(self, 'title', None) or 'Untitled'

class Posts(audrey.resources.collection.NamingCollection):
    _collection_name = 'posts'
    _object_classes = (Post,)

class Root(audrey.resources.root.Root):
    _collection_classes = (People, Posts, )

def root_factory(request): # pragma: no cover
    return Root(request)
