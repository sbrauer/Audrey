Audrey aims to be a minimal framework for creating Pyramid applications that use MongoDB for storage, ElasticSearch for fulltext search, traversal for resource lookup, and colander for schema declaration and user input validation.
It will include views that implement a RESTful API, and a scaffold for quickly starting new Audrey projects.

My goal is to keep Audrey otherwise unopinionated.  For example, Audrey intentionally does nothing regarding authentication, authorization, permissions, __acl__, etc.  A developer building on Audrey can make those decisions as appropriate for their app and implement them using standard Pyramid facilities.
