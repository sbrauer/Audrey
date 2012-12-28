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
       python setup.py install

   Wait patiently for all of the dependencies to download and install.

   [FIXME: Upload Audrey to PyPI so you can just pip install it.]

.. note::
   At the time of this writing, the current release of pyramid_zcml (0.9.2)
   has a minor bug that prevents Audrey from properly handling XHR requests.
   Until the 0.9.3 release you'll have to make a tiny tweak to your copy of
   pyramid_zcml's __init__.py file.  Edit the file ``myenv/lib/python2.7/site-packages/pyramid_zcml-0.9.2-py2.7.egg/pyramid_zcml/__init__.py`` and change the two lines (166 and 248) that say::

      xhr=False,

   To::

      xhr=None,

   For more details, see https://github.com/Pylons/pyramid_zcml/pull/5/files

.. _creating-new-project:

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
as you walk through the :ref:`resource-modelling` section and see how everything fits together.

If you aren't running MongoDB and ElasticSearch on default ports on localhost (as described in the `Prerequisites`_ section above), edit ``development.ini`` and adjust the connection settings ``mongo_uri``, ``mongo_name``, ``elastic_uri`` and ``elastic_name``.
