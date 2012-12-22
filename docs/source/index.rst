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
       python setup.pt develop

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

1. `Object <#module-audrey.resources.object>`_ - This is the fundamental
building block of an Audrey application.  Objects have methods to save
themselves to MongoDB, load themselves from MongoDB and index/reindex/unindex
themselves in ElasticSearch.

2. `Collection <#module-audrey.resources.collection>`_ - Collections are sets
of Objects.  They correspond to MongoDB collections and have various methods
to access and manipulate their child objects.

3. `Root <#module-audrey.resources.root>`_ - Root is the container of 
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
a ``resources.py`` file with content similar to the following::

    FIXME

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

