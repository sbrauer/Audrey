.. _resource-modelling:

Resource Modelling
==================

Audrey provides some base resource classes for a developer to subclass
to model the objects specific to their application.  The main classes
are:

1. :class:`audrey.resources.object.Object` - This is the fundamental
building block of an Audrey application.  Objects have methods to
save/load/remove themselves in MongoDB and index/reindex/unindex
themselves in ElasticSearch.

2. :class:`audrey.resources.collection.Collection` - Collections are sets
of Objects.  They correspond to MongoDB collections and have various methods
to access and manipulate their child objects.

3. :class:`audrey.resources.root.Root` - Root is the container of 
Collections and represents the root of your app.  It also provides
various "global" services (such as search, cross-collection references
and file uploads/downloads).

As the application developer, you define your Object classes  (using colander
to define the schema for each class), your Collection classes
(specifying which Object classes can be created in each Collection), 
and a Root class (specifying the list of Collections).
Audrey then provides what I hope is a comfortable and Pythonic interface
that handles the boring, repetitve yet error-prone details of interacting 
with MongoDB and ElasticSearch, validating your schemas, etc.

.. note::
   The base ``Object`` and ``Collection`` classes don't allow explicit control of the ``__name__`` attribute used for traversal.  For cases where you need such control, use the :class:`audrey.resources.object.NamedObject` and :class:`audrey.resources.collection.NamingCollection` classes instead.

After you create a new project using the ``audrey`` scaffold (as described
in :ref:`creating-new-project`), you'll have a couple of example
Objects and Collections defined in the file ``resources.py`` inside
your package directory (which will be the same name as your project name,
but in lowercase).  You'll of course want to replace these examples with
your own Objects and Collections, and may even want to split the single
file up into a ``resources`` sub-package.

Let's take a close look at the example ``resources.py`` file and see
how it subclasses the base Audrey classes.  The file should have content
similar to the following:

.. literalinclude:: resources.py
   :linenos:

Starting at line 7, a ``Person`` class is defined that subclasses :class:`audrey.resources.object.Object`.

At line 8, the class attribute ``_object_type`` is overridden.  The value of 
this attribute should be a string that uniquely identifies the Object type
(within the context of your project).  It's used in many places as a key
to lookup a given Object class.  There are no restrictions on the characters it may contain, so feel free to make it human-friendly (using spaces instead of underscores to separate words, for example).

In lines 10-14, the class attribute ``_schema`` is overridden.  The value of
this attribute should be a colander schema representing the user-editable
attributes for the Object type (the sort of attributes that might
be shown as fields in an edit form).  This is standard colander stuff, and
you can use all the colander types (including Mapping and Sequence).
Additionally Audrey defines a couple of its own colander types:

1. :class:`audrey.types.File` - This type represents an uploaded file which
will be stored in the MongoDB GridFS.  As an example, see line 15 where a
File attribute with the name ``photo`` is defined for the ``person`` type.

2. :class:`audrey.types.Reference` - This type represents a reference
to another Object (possibly in another collection).
As an example, see lines 46-48 where a Reference attribute with the name ``author`` is defined to allow a reference from the ``post`` type to the ``person`` type.

In lines 16-25, the method ``get_title()`` is overridden.  This method should
return a string suitable for use as a human-friendly title of an Object 
instance (as might be shown as the text in a link to the object).
If you don't override this method, it will return the object's ``__name__``
by default.  The implementation of ``Person.get_title()`` is a little long 
since it tries to be flexible and handle cases where the "firstname" and "lastname" attributes may be missing.  The implementation 
of ``Post.get_title()`` at line 45 is a one-liner suitable for types that
have a single attribute that's a natural fit for a title.

For a lot of object types, that's all you'll need to override.
It should go without saying that since these are just Python classes,
you're free to override other methods and add your own to suit your
specific needs.

Moving on, lines 27-29 define a ``People`` class that subclasses :class:`audrey.resources.collection.Collection`.  This is pretty short and sweet.

Line 28 overrides the ``_collection_name`` class attribute.  The value of this
attribute is a string that uniquely identifies the Collection within the content of your project.  It's used as a key/name to traverse from the root of the app
to a singleton instance of the Collection.

Line 29 overrides the ``_object_classes`` class attribute.  The value of this attribute is a sequence of Object classes representing the types of Objects that may exist in the Collection.  In this case, the People Collection is homogenous and only contains Person Objects.  You can, however, define Collections that may contain multiple Object types (presumably with some common sub-schema).  When creating Object types that will be in a non-homogenous Collection, be sure to set the :attr:`audrey.resources.object.Object._save_object_type_to_mongo` class attribute to ``True``; otherwise the Collection will raise an exception while deserializing from MongoDB since it won't be able to determine the correct Object class to construct.

Lines 31-49 define another Object type and another homogenous Collection.

Lines 51-52 define a ``Root`` class that subclasses :class:`audrey.resources.root.Root` and overrides the ``_collection_classes`` class attribute.  The value of this attribute is a sequence of Collection classes representing all the Collections in use in the app.

Lines 54-55 define a ``root_factory()`` function which returns an instance of ``Root`` for a request.  This function is used by Audrey to configure the Pyramid application to find the traversal root.

If you haven't read the :doc:`introduction` section yet, you may want to now.
It demonstrates some of the functionality Audrey provides using the 
``Person`` and ``People`` classes defined here as examples.

You may also want to explore the :doc:`api` documentation to discover further functionality and details.
