% Audrey
% 
% 

Audrey aims to be a minimal framework for creating
[Pyramid](http://www.pylonsproject.org/) applications that use
[MongoDB](http://www.mongodb.org/) for persistence,
[ElasticSearch](http://www.elasticsearch.org/) for full text search
(optional),
[traversal](http://docs.pylonsproject.org/projects/pyramid/en/1.4-branch/narr/traversal.html)
for resource/view lookup, and
[colander](http://pypi.python.org/pypi/colander) for schema
declaration and user input validation.

Audrey also provides views that implement a RESTful API. In an
attempt to satisfy the hypermedia constraint (HATEOAS), GET
responses use the
[HAL+JSON](http://stateless.co/hal_specification.html) mediatype.
In a further attempt to be self-describing, links to
[JSON Schema](http://json-schema.org/) documents (generated
automatically from your types' colander schemas) are provided for
POST and PUT requests.

My goal is to keep Audrey otherwise unopinionated. For example,
Audrey intentionally does nothing regarding authentication,
authorization, permissions, etc. A developer building on Audrey can
make those decisions as appropriate for their app and implement
them using standard Pyramid facilities.

# Docs and Demo

[Documentation at ReadTheDocs.org](https://audrey.readthedocs.org/)

Explore the default API views at
[http://audreydemo.aws.af.cm/hal-browser/](http://audreydemo.aws.af.cm/hal-browser/)

If you'd rather keep it old school:

    curl http://audreydemo.aws.af.cm

This is running with the example resource models that are setup
when you use the Audrey scaffold. You may want to refer to the
[documentation that introduces the RESTful views](https://audrey.readthedocs.org/en/latest/introduction.html#restful-views).
(Please note that the demo doesn't have ElasticSearch enabled. I'll
enable search once I find a free hosting solution.)

The demo site uses free services from these great providers:

-   [AppFog](https://www.appfog.com/)
-   [MongoLab](https://mongolab.com/)



