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

3. ElasticSearch (optional; full text and cross-collection search won't work without it)

   If you don't already have an ElasticSearch server, install the latest production release from http://www.elasticsearch.org/download/
   
   If you just want to quickly try out Audrey, here's a recipe for running an ElasticSearch server in the foreground under your non-root user account::

        wget http://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.20.2.tar.gz
        tar xfz elasticsearch-0.20.2.tar.gz 
        ln -s elasticsearch-0.20.2 elasticsearch
        cd elasticsearch
        bin/plugin -install elasticsearch/elasticsearch-transport-thrift/1.4.0
        bin/elasticsearch -f

Setup Audrey
------------

1. Create and activate a Python virtual environment.  For example::

       virtualenv myenv
       cd myenv
       source bin/activate

2. Move or clone the ``Audrey`` directory from Github into ``myenv``.
   Then::

       cd Audrey
       python setup.py install

   Wait patiently for all of the dependencies to download and install.

   [FIXME: Upload Audrey to PyPI so you can just pip install it.]

.. _creating-new-project:

Creating a new project
----------------------

Audrey includes a scaffold to bootstrap a new project.  Run it from the root directory of your virtualenv like this example::

    cd $VIRTUAL_ENV
    pcreate -s audrey MyProject
    cd MyProject
    python setup.py develop

As examples to get you started, ``myaudreyproject/resources.py`` defines two
object types (Person and Post) as well as two collections (People and Posts)
and a Root class to tie it all together.  You will of course want to replace
these classes with your own app-specific types, but for now just refer to them
as you walk through the :ref:`resource-modelling` section and see how everything fits together.

If you aren't running MongoDB and ElasticSearch on default ports on localhost (as described in the `Prerequisites`_ section above), edit ``development.ini`` and adjust the connection settings ``mongo_uri``, ``mongo_name``, ``elastic_uri`` and ``elastic_name``.

Startup commands
----------------

You can now use the usual Pyramid commands, such as these examples.

Start the web server::

    pserve development.ini --reload

Start an interactive shell::

    pshell development.ini#main

Run tests::

    nosetests --cover-package=myproject --cover-erase --with-coverage --cover-html

