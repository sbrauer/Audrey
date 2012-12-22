.. Audrey documentation master file, created by
   sphinx-quickstart on Wed Dec 19 18:22:42 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Audrey
******
Audrey is a minimal framework for creating
`Pyramid <http://www.pylonsproject.org/>`_ applications that
use `MongoDB <http://www.mongodb.org/>`_ for persistence,
`ElasticSearch <http://www.elasticsearch.org/>`_ for fulltext
search (optional), `traversal <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/traversal.html>`_ for resource/view lookup, and
`colander <http://pypi.python.org/pypi/colander>`_ for schema declaration
and user input validation.

.. note::
   Just want to see some example code? Skip ahead to the `Usage`_ section below.

Audrey also provides views that implement a RESTful API.  In an attempt
to satisfy the hypermedia constraint (HATEOAS), GET responses use the
`HAL+JSON <http://stateless.co/hal_specification.html>`_ mediatype.
In a further attempt to be self-describing, links to `JSON Schema
<http://json-schema.org/>`_ documents (generated automatically from your
types' colander schemas) are provided for POST and PUT requests.
(Note that Audrey doesn't provide any HTML views, but it does include
`HAL-browser <https://github.com/mikekelly/hal-browser>`_ which can be used to 
explore the RESTful API.)

My goal is to keep Audrey otherwise unopinionated.  For example, Audrey
intentionally does nothing regarding authentication, authorization,
permissions, etc.  A developer building on Audrey can make those decisions
as appropriate for their app and implement them using `standard Pyramid
facilities <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/security.html>`_.

.. warning::
   Audrey is currently in the pre-alpha development stage.
   The API is subject to change.

.. toctree::
   :maxdepth: 2

Installation
============

.. note::
   I'm developing Audrey on Linux. I'm assuming that the instructions below would work just as well under OS X, but can't say for sure.  No idea about Windows.

Prerequisites
-------------

1. Python 2.7 and virtualenv

   If you don't already have these, refer to the `Pyramid docs for instructions <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/install.html>`_.

2. MongoDB

   If you don't already have a MongoDB server, install the latest production release from http://www.mongodb.org/downloads

   If you just want to quickly try out Audrey, here's a recipe for running a MongoDB server in the foreground under your non-root user account::

        wget http://fastdl.mongodb.org/linux/mongodb-linux-x86_64-2.0.6.tgz
        tar xfz mongodb-linux-x86_64-2.0.6.tgz
        ln -s mongodb-linux-x86_64-2.0.6 mongodb
        cd mongodb
        mkdir -p data
        bin/mongod --dbpath=data --rest

3. ElasticSearch (optional; fulltext and cross-collection search won't work without it)

   If you don't already have an ElasticSearch server, install the latest production release from http://www.elasticsearch.org/download/
   
   If you just want to quickly try out Audrey, here's a recipe for running an ElasticSearch server in the foreground under your non-root user account::

        wget https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-0.19.4.tar.gz
        tar xfz elasticsearch-0.19.4.tar.gz
        ln -s elasticsearch-0.19.4 elasticsearch
        cd elasticsearch
        bin/plugin -install elasticsearch/elasticsearch-transport-thrift/1.2.0
        bin/elasticsearch -f

Setup Audrey
------------

1. Create and activate a Python virtual environment.  For example::

       virtualenv myenv
       cd myenv
       source bin/activate

2. Move the ``Audrey`` directory from Github into ``myenv``.
   Then::

       cd Audrey
       python setup.py develop

   [FIXME: Upload Audrey to PyPI so you can just pip install it.]

Creating a new project
----------------------

Audrey includes a scaffold to bootstrap a new project.  From the root directory of your virtualenv run the following::

    pcreate -s audrey MyProject
    cd MyProject
    python setup.py develop

As examples to get you started, ``myaudreyproject/resources.py`` defines two
object types (Person and Post) as well as two collections (People and Posts)
and a Root class to tie it all together.  You will of course want to replace
these classes with your own app-specific types, but for now just refer to them
as you walk through the `Usage`_ section below and see how everything fits 
together.

If you aren't running MongoDB and ElasticSearch on default ports on localhost (as described in the `Prerequisites`_ section above), edit ``development.ini`` and adjust the connection settings ``mongo_uri``, ``mongo_name``, ``elastic_uri`` and ``elastic_name``.

Usage
=====

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
various "global" services (such as search, cross-collection references,
and file uploads).

As the application developer, you define your Object classes  (using colander
to define the schema for each class), your Collection classes
(specifying which Object classes can be created in each Collection), 
and a Root class (specifying the list of Collections).
Audrey takes care of the details of interacting with MongoDB and
ElasticSearch.

So let's dive into the details...

After you create a new project using the ``audrey`` scaffold, you'll have
a ``resources.py`` file with example content similar to the following:

.. literalinclude:: resources.py
   :linenos:

Starting at line 4, a ``Person`` class is defined that subclasses :class:`audrey.resources.object.Object`.

At line 5, the class attribute ``_object_type`` is overridden.  The value of 
this attribute should be a string that uniquely identifies the Object type
(within the context of your project).  It's used in many places as a key
to lookup a given Object class.  There are no restrictions on the characters it may contain, so feel free to make it human readable (using spaces instead of underscores to separate words, for example).

In lines 7-14, the class method ``get_class_schema()`` is overridden.  This
method should return a colander schema representing the user-editable
attributes for the Object type (the sort of attributes that might
be shown as fields in an edit form).  This is standard colander stuff, but note
that Audrey defines a couple of its own colander types:

1. :class:`audrey.types.File` - This type represents an uploaded file which
will be stored in the MongoDB GridFS.  As an example, see line 12 where a
File attribute with the name ``photo`` is defined for the ``person`` type.

2. :class:`audrey.types.Reference` - This type represents a reference
to another Object (possibly in another collection).
As an example, see lines 42-44 where a Reference attribute with the name ``author`` is defined for the ``post`` type.

In lines 16-25, the method ``_title()`` is overridden.  This method should
return a string suitable for use as a human-friendly title of an Object 
instance (as might be shown as the text in a link to the object).
If you don't override this method, it will return the object's ``__name__``
by default.  The implementation of ``Person._title()`` is a little long 
since it tries to be flexible and handle cases where the "firstname" and "lastname" attributes may not have been set yet, or may be empty.  The implementation 
of ``Post._title()`` at line 48 is a one-liner suitable for types that
have a single attribute that's a natural fit for a title.

For a lot of object types, these two methods and one attribute will be all
you need to override.  Of course, you may opt to add new methods and/or 
attributes of your own.

Moving on, lines 27-29 define a ``People`` class that subclasses :class:`audrey.resources.collection.Collection`.  This is pretty short and sweet.

Line 28 overrides the ``_collection_name`` class attribute.  The value of this
attribute is a string that uniquely identifies the Collection within the content of your project.  It's used as a key/name to traverse from the root of the app
to a singleton instance of the Collection.

Line 29 overrides the ``_object_classes`` class attribute.  The value of this attribute is a sequence of Object classes representing the types of Objects that may exist in the Collection.  In this case, the People Collection is homogenous and only contains Person Objects.  You can, however, define Collections that may contain multiple Object types (presumably with some common sub-schema).

.. FIXME - link classnames in next paragrah

Lines 31-52 define another Object type and another homogenous Collection.
The only significant difference is that instead of subclassing :class:`Object`
and :class:`Collection`, NamedObject and NamingCollection are subclassed.
This is done purely for the sake of an example.  The distinction between
the two is that NamedObject and NamingCollection allow end users to 
assign the ``__name__`` attributes of object instances.  Since the ``__name__`` is used for traversal, this is useful in cases where you want to allow users
to have some control over the URLs used to access resources.  The non-naming
Object and Collection classes automatically assign opaque ``__name__`` values;
in fact, string versions of the ObjectIds that MongoDB assigns to newly inserted documents are used as the names.  Pick whichever makes sense for your use case.

.. note::
   On the TODO list for Audrey is the addition of a FolderObject and corresponding HierarchicalCollection (names subject to change).  These would allow for nesting of NamedObjects which would allow end users even more control over URLs with the ability to create arbitrarily deep hierarchies.  This could be useful for applications like a CMS (similar to Zope CMF and Plone).

Lines 54 and 55 define a ``Root`` class that subclasses :class:`audrey.resources.root.Root` and overrides the ``_collection_classes`` class attribute.  The value of this attribute is a sequence of Collection classes representing all the Collections in use in the app.

Lines 57 and 58 define a ``root_factory()`` function which returns an instance of ``Root`` for a request.  This function is used by Audrey to configure the Pyramid application to find the traversal root.


API
===

audrey.resources
----------------

object
++++++
.. automodule:: audrey.resources.object
    :members:

collection
++++++++++
.. automodule:: audrey.resources.collection
    :members:

root
++++
.. automodule:: audrey.resources.root
    :members:

file
++++
.. automodule:: audrey.resources.file
    :members:

reference
+++++++++
.. automodule:: audrey.resources.reference
    :members:

audrey.types
------------
.. automodule:: audrey.types
    :members:

audrey.views
------------
.. automodule:: audrey.views
    :members:

audrey.colanderutil
-------------------
.. automodule:: audrey.colanderutil
    :members:

audrey.dateutil
---------------
.. automodule:: audrey.dateutil
    :members:

audrey.sortutil
---------------
.. automodule:: audrey.sortutil
    :members:

audrey.exceptions
-----------------
.. automodule:: audrey.exceptions
    :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

