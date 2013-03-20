Audrey
======

Audrey aims to be a minimal framework for creating `Pyramid <http://www.pylonsproject.org/>`_ applications that use `MongoDB <http://www.mongodb.org/>`_ for persistence, `ElasticSearch <http://www.elasticsearch.org/>`_ for full text search (optional), `traversal <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/traversal.html>`_ for resource/view lookup, and `colander <http://pypi.python.org/pypi/colander>`_ for schema declaration and user input validation.

Audrey also provides views that implement a RESTful API.  In an attempt to satisfy the hypermedia constraint (HATEOAS), GET responses use the `HAL+JSON <http://stateless.co/hal_specification.html>`_ mediatype.  In a further attempt to be self-describing, links to `JSON Schema <http://json-schema.org/>`_ documents (generated automatically from your types' colander schemas) are provided which describe the bodies for POST and PUT requests.  Audrey doesn't provide any HTML views, but it does include `HAL-Browser <https://github.com/mikekelly/hal-browser>`_ which can be used to explore the RESTful API.  (Please be aware that the included API is tightly coupled to your resource models. Such an API may be handy for prototypes or even in cases where you control all client use, but it is **definitely not recommended for use by third-parties**. Creating your own custom versioned API is highly recommended.)

My goal is to keep Audrey otherwise unopinionated.  For example, Audrey intentionally does nothing regarding authentication, authorization, permissions, etc.  A developer building on Audrey can make those decisions as appropriate for their app and implement them using standard Pyramid facilities.

Status
------
Audrey is a pet project serving as a playground to explore some ideas. Too soon to tell whether it will mature or not.

Docs and Demo
-------------

`Documentation at ReadTheDocs.org <https://audrey.readthedocs.org/>`_

Explore the default API views at http://audreydemo.aws.af.cm/hal-browser/

If you'd rather keep it old school::

    curl http://audreydemo.aws.af.cm

This is running with the example resource models that are setup when you use the Audrey scaffold.  You may want to refer to the `documentation that introduces the RESTful views <https://audrey.readthedocs.org/en/latest/introduction.html#restful-views>`_.

The demo site uses free services from these providers:

* `AppFog <https://www.appfog.com/>`_
* `MongoLab <https://mongolab.com/>`_
* `SearchBox.io <https://searchbox.io/>`_
