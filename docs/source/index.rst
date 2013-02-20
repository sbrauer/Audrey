Audrey
******

Audrey is a minimal framework for creating
`Pyramid <http://www.pylonsproject.org/>`_ applications that
use `MongoDB <http://www.mongodb.org/>`_ for persistence,
`ElasticSearch <http://www.elasticsearch.org/>`_ for full text
search (optional), `traversal <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/traversal.html>`_ for resource/view lookup, and
`colander <http://pypi.python.org/pypi/colander>`_ for schema declaration
and user input validation.

Audrey also provides views that implement a RESTful API.  In an attempt
to satisfy the hypermedia constraint (HATEOAS), GET responses use the
`HAL+JSON <http://stateless.co/hal_specification.html>`_ mediatype.
In a further attempt to be self-describing, links to `JSON Schema
<http://json-schema.org/>`_ documents (generated automatically from your
types' colander schemas) are provided for POST and PUT requests.
(Note that Audrey doesn't provide any HTML views, but it does include
`HAL-Browser <https://github.com/mikekelly/hal-browser>`_ which can be used to 
explore the RESTful API.)

My goal is to keep Audrey otherwise unopinionated.  For example, Audrey
intentionally does nothing regarding authentication, authorization,
permissions, etc.  A developer building on Audrey can make those decisions
as appropriate for their app and implement them using `standard Pyramid
facilities <http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/security.html>`_.

.. warning::
   Audrey is a pet project serving as a playground to explore some ideas. Too soon to tell whether it will mature or not.

.. toctree::
   :maxdepth: 3

   introduction
   resources
   install
   api
