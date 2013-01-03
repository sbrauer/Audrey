Overview
========

Let's say you just installed Audrey and used its starter scaffold to create
a new project (as described in :ref:`creating-new-project`).  You'd have two
example object types (``Person`` and ``Post``) to play with.
(As you read this section, if you find yourself wondering things like
how the types and their schemas are defined, you may want to jump ahead to the :ref:`resource-modelling` section.)

Let's take a look around in a pshell session::

    $ pshell development.ini#main
    Python 2.7.3 (default, Nov 13 2012, 15:00:33) 
    [GCC 4.4.5] on linux2
    Type "help" for more information.

    Environment:
      app          The WSGI application.
      registry     Active Pyramid registry.
      request      Active request object.
      root         Root of the default resource tree.
      root_factory Default root factory used to create `root`.

    >>> root
    <myproject.resources.Root object at 0x9d35a6c>
    >>> root.get_collection_names()
    ['people', 'posts']

OK. So we have a Root object with two collections named "people" and "posts".
Let's check out one of those::

    >>> people = root['people']
    >>> people
    <myproject.resources.People object at 0xa26c04c>
    >>> people.get_children()
    []

Look's like there aren't any people yet.  So let's create one::

    >>> from myproject import resources
    >>> person = resources.Person(request)
    >>> print person
    {'_created': None,
     '_etag': None,
     '_id': None,
     '_modified': None,
     'firstname': None,
     'lastname': None,
     'photo': None}

Kinda boring.  But let's see what would happen if we tried to save it (by
adding it to the ``people`` collection)::

    >>> people.add_child(person)
    ... traceback omitted ...
    Invalid: {'firstname': u'Required', 'lastname': u'Required'}

That's a :class:`colander.Invalid` exception letting us know that schema
validation failed.  Let's set the required attributes and try again::

    >>> person.firstname = 'Audrey'
    >>> person.lastname = 'Horne'
    >>> people.add_child(person)
    >>> print person
    {'_created': datetime.datetime(2012, 12, 24, 1, 52, 45, 281718, tzinfo=<UTC>),
     '_etag': '52779a9953bd01defd439bd29874c3d4',
     '_id': ObjectId('50d7b56dbf90af0e96bc8433'),
     '_modified': datetime.datetime(2012, 12, 24, 1, 52, 45, 281718, tzinfo=<UTC>),
     'firstname': 'Audrey',
     'lastname': 'Horne',
     'photo': None}

The object has been persisted in MongoDB and now has an ObjectId, creation and modification timestamps and an Etag. (It was also indexed in ElasticSearch.) Let's check the children of the ``People`` collection again::

    >>> people.get_children()
    [<myproject.resources.Person object at 0xa26cbac>]

As sort of an aside, we can traverse to the new Person object by the string
version of its ID like this::

    >>> root['people']['50d7b56dbf90af0e96bc8433']
    <myproject.resources.Person object at 0xa1f4d6c>
    >>> person.__name__
    '50d7b56dbf90af0e96bc8433'
    >>> person.__parent__
    <myproject.resources.People object at 0xa26c04c>

.. note::
   Using the ID as the __name__ is the behavior of the base Audrey :class:`Object` and :class:`Collection` types.  There exist subclasses :class:`NamedObject` and :class:`NamingCollection` that allow for explicit control over naming.  Whether you use one or the other depends on your use case.  For this example, I opted to keep it minimal and use the base classes.

Let's add a couple more Person objects to make things a little more interesting.
Note that we can pass kwargs to the object constructor to initialize attributes::

    >>> people.add_child(resources.Person(request, firstname='Laura', lastname='Palmer'))
    >>> people.add_child(resources.Person(request, firstname='Dale', lastname='Cooper'))
    >>> [child.get_title() for child in people.get_children()]
    [u'Dale Cooper', u'Audrey Horne', u'Laura Palmer']

You'll note that the order of the children is arbitrary.  Let's explicitly sort them::

    >>> [child.get_title() for child in people.get_children(sort=[('_created',1)])]
    [u'Audrey Horne', u'Dale Cooper', u'Laura Palmer']

Did you notice the ``photo`` attribute earlier?  Let's set a photo for Dale.
First let's retrieve his object::

    >>> obj = people.get_child({'firstname':'Dale'})
    >>> print obj
    {'_created': datetime.datetime(2012, 12, 24, 2, 10, 14, 856000, tzinfo=<UTC>),
     '_etag': u'a8ee673c5490be625bd720375add252f',
     '_id': ObjectId('50d7b986bf90af0e96bc8434'),
     '_modified': datetime.datetime(2012, 12, 24, 2, 10, 14, 856000, tzinfo=<UTC>),
     'firstname': u'Dale',
     'lastname': u'Cooper',
     'photo': None}

Now we'll open a file, add it to Audrey's GridFS, then update and save the Person::

    >>> f = open("dale-cooper.jpg")
    >>> obj.photo = root.create_gridfs_file(f, "dale-cooper.jpg", "image/jpeg")
    >>> f.close()
    >>> obj.save()
    >>> print obj
    {'_created': datetime.datetime(2012, 12, 24, 2, 10, 14, 856000, tzinfo=<UTC>),
     '_etag': '080b9d79d888e5d6714acc8cfb07d6ae',
     '_id': ObjectId('50d7b986bf90af0e96bc8434'),
     '_modified': datetime.datetime(2013, 1, 3, 1, 7, 31, 134749, tzinfo=<UTC>),
     'firstname': u'Dale',
     'lastname': u'Cooper',
     'photo': <audrey.resources.file.File object at 0xaa2190c>}

You'll notice that the ``photo`` is an instance of :class:`audrey.resources.file.File``.  This is simply a wrapper around the ObjectId of a GridFS file.  To access the GridFS file, call ``get_gridfs_file()``::

    >>> obj.photo.get_gridfs_file(request)
    <gridfs.grid_file.GridOut object at 0x947c64c>

We've covered creating and updating objects.  Now let's delete one::

    >>> obj = people.get_child({'firstname': 'Laura'})
    >>> people.delete_child(obj)
    >>> [child.get_title() for child in people.get_children()]
    [u'Dale Cooper', u'Audrey Horne']

.. note::
   ``Collection`` also has methods ``delete_child_by_id()`` and ``delete_child_by_name()``.  This overview doesn't try to demonstrate every method and parameter.

Now let's switch our focus to the web api.  (If you're running locally, you can
explore the api with HAL-browser by visiting http://127.0.0.1:6543/hal-browser/
in your web browser.)  For our current purposes, I'll use curl and Python's super-handy json.tool::

    $ curl http://127.0.0.1:6543/ | python -mjson.tool
    {
        "_links": {
            "audrey:upload": {
                "href": "http://127.0.0.1:6543/@@upload"
            }, 
            "curie": {
                "href": "http://127.0.0.1:6543/relations/{rel}", 
                "name": "audrey", 
                "templated": true
            }, 
            "item": [
                {
                    "href": "http://127.0.0.1:6543/people/{?sort}", 
                    "name": "people", 
                    "templated": true
                }, 
                {
                    "href": "http://127.0.0.1:6543/posts/{?sort}", 
                    "name": "posts", 
                    "templated": true
                }
            ], 
            "search": {
                "href": "http://127.0.0.1:6543/@@search?q={q}{&sort}{&collection*}", 
                "templated": true
            }, 
            "self": {
                "href": "http://127.0.0.1:6543/"
            }
        }
    }

.. note::
   These are just the default views that Audrey provides.  You can override and reconfigure to suit your needs, or ignore them entirely and create your own views from scratch.

This is a HAL+JSON document representing the root.  Since the root has no
state of its own, the document just has a number of links keyed by link
relation ("rel") names.  Besides "self" which is obligatory for HAL, Audrey
tries to stick to relations from the `IANA list <http://www.iana.org/assignments/link-relations/link-relations.xml>`_.

Here we see "item" used to list the children of root (the "people" and "posts" collections).  Note that the urls are templated, in this case indicating that
you may use an optional "sort" parameter.  In a moment, we'll follow one of these links.

There's also a link to a "search" endpoint (again with a URL template) and another to the "upload" endpoint.  Since there was no IANA rel that seemed suitable for the upload endpoint (which as you may have guessed is a factory for uploading files into the system), Audrey uses a namespaced URI.  Applying the "curie" template, "audrey:upload" expands to "http://127.0.0.1:6543/relations/upload"; visiting that url returns some HTML documentation of the endpoint including the expected request and response details.

Now let's GET the "people" collection using the "sort" parameter to sort by creation time::

    $ curl http://127.0.0.1:6543/people?sort=_created | python -mjson.tool
    {
        "_factory": {
            "method": "POST", 
            "schemas": [
                "person"
            ]
        }, 
        "_links": {
            "audrey:schema": [
                {
                    "href": "http://127.0.0.1:6543/people/@@schema/person", 
                    "name": "person"
                }
            ], 
            "collection": {
                "href": "http://127.0.0.1:6543/"
            }, 
            "curie": {
                "href": "http://127.0.0.1:6543/relations/{rel}", 
                "name": "audrey", 
                "templated": true
            }, 
            "item": [
                {
                    "href": "http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/", 
                    "name": "50d7b56dbf90af0e96bc8433", 
                    "title": "Audrey Horne"
                }, 
                {
                    "href": "http://127.0.0.1:6543/people/50d7b986bf90af0e96bc8434/", 
                    "name": "50d7b986bf90af0e96bc8434", 
                    "title": "Dale Cooper"
                }
            ], 
            "self": {
                "href": "http://127.0.0.1:6543/people/?sort=_created"
            }
        }, 
        "_summary": {
            "batch": 1, 
            "per_batch": 20, 
            "sort": "_created", 
            "total_batches": 1, 
            "total_items": 2
        }
    }

The Collection view has some similarities with the Root view.
Again we see the obligatory "self" link and a list of "item" links (this time
the items are the two ``Person`` instances we created earlier).  
The "collection" rel is used to indicate a link to the container of the current
resource, which in this case is the root.  Finally there's a custom namespaced
"schema" rel.  As the documentation at http://127.0.0.1:6543/relations/schema explains, the "schema" rel is a list of links to JSON Schema documents; there's one such link for each object type that can be created in the current Collection.

We also see two custom properties: "_factory" and "_summary".

The first identifies the HTTP method to be used to create new resources inside
the collection.  Here it's POST since People is a base Collection and assigns names automatically.  If it was a NamingCollection, the method would be PUT indicating that clients should specify new resource names by doing a PUT to a new url (such as "/people/harry-truman").

The "_summary" property contains some metadata about the current item listing.  Here we see that there are 2 items total.  Since the batch size is 20, there's only one batch.  If there were more than 20 people, the "item" link array would only include a batch of up to 20 and there may be links with the rel "next" and/or "prev" with the urls for the next and previous batches (as appropriate).

Now let's follow the first "item" link::

    $ curl http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/ | python -mjson.tool
    {
        "_created": "2012-12-24T01:52:45.281000+00:00", 
        "_etag": "52779a9953bd01defd439bd29874c3d4", 
        "_id": {
            "ObjectId": "50d7b56dbf90af0e96bc8433"
        }, 
        "_links": {
            "audrey:file": [], 
            "audrey:reference": [], 
            "collection": {
                "href": "http://127.0.0.1:6543/people/"
            }, 
            "curie": {
                "href": "http://127.0.0.1:6543/relations/{rel}", 
                "name": "audrey", 
                "templated": true
            }, 
            "describedby": {
                "href": "http://127.0.0.1:6543/people/@@schema/person"
            }, 
            "self": {
                "href": "http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/"
            }
        }, 
        "_modified": "2012-12-24T01:52:45.281000+00:00", 
        "_object_type": "person", 
        "_title": "Audrey Horne", 
        "firstname": "Audrey", 
        "lastname": "Horne", 
        "photo": null
    }

Finally, something with some state data; here we see the schema properties "firstname", "lastname" and "photo", as well as various metadata properties which I've used the convention of starting with an underscore.  Now let's look at the ubiquitous links.

There's "self" of course.  The "collection" link refers to the current object's container.  The "describedby" link refers to a JSON Schema for the object.  Finally there are two custom rels "file" and "reference".

The "file" rel is used to indicate a list of links to (you guessed it) files referenced by this resource object.  In this case, if "photo" wasn't null there would be a link to the photo file.  (Keep reading and we'll upload a photo file and update this person to refer to it.)

The "reference" rel is used to indicate a list of links to other object resources referenced by this one.  The ``Person`` type doesn't have any reference attributes in its schema, so this will always be an empty list for this class.

Now let's demonstrate POSTing a new ``Person``::

    $ curl -i -XPOST http://127.0.0.1:6543/people/ -d '{
          "_object_type": "person",
          "firstname": "Shelly",
          "lastname": "Johnson"
      }'

    HTTP/1.1 201 Created
    Content-Length: 2
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 24 Dec 2012 18:25:35 GMT
    Location: http://127.0.0.1:6543/people/50d89e1fbf90af0d7169df5d/
    Server: waitress

    {}

Cool... Audrey responds with the ``201 Created`` success status and "Location" header with the URL of the new resource.

You might wonder what would happen if we tried to POST an invalid request.
First let's try POSTing an empty JSON document::

    $ curl -i -XPOST http://127.0.0.1:6543/people/ -d '{}'
    HTTP/1.1 400 Bad Request
    Content-Length: 45
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 24 Dec 2012 18:27:34 GMT
    Server: waitress

    {"error": "Request is missing _object_type."}

Uh oh... we got ``400 Bad Request`` and an error message in the body with the reason.
So now let's POST a document that just contains an "_object_type"::

    curl -i -XPOST http://127.0.0.1:6543/people/ -d '{"_object_type": "person"}'
    HTTP/1.1 400 Bad Request
    Content-Length: 92
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 24 Dec 2012 18:27:57 GMT
    Server: waitress

    {"errors": {"lastname": "Required", "firstname": "Required"}, "error": "Validation failed."}

Another 400 error and another "error" message.  Since this one's a validation error, the JSON document in the response also includes an "errors" key with the field-specific errors (courtesy of colander).

Now let's upload a photo::

    $ curl -F file=@audrey.jpg http://127.0.0.1:6543/@@upload
    {"file": {"FileId": "50d8a64bbf90af0d7169df5e"}}

The server creates a GridFS file in MongoDB for each file from the request
and responds with a JSON document containing the ID of each file using as
keys the same parameter names you used in the request.  (In other words,
if you were to upload two files with the parameter names "foo" and "bar"
then the response would have two FileIds with the keys "foo" and "bar".)

Let's update Audrey Horne's record with the new photo file::

    $ curl -i -XPUT http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/ -d '{
          "_object_type": "person",
          "firstname": "Audrey",
          "lastname": "Horne",
          "photo":  {"FileId": "50d8a64bbf90af0d7169df5e"}
      }'
    HTTP/1.1 412 Precondition Failed
    Content-Length: 75
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 24 Dec 2012 20:04:37 GMT
    Server: waitress
    
    {"error": "Requests must supply If-Unmodified-Since and If-Match headers."}

What's going on here?  The views implement `optimistic concurrency control <http://en.wikipedia.org/wiki/Optimistic_concurrency_control>`_ in an effort to avoid silent data loss.  PUT requests to update an existing resource and DELETE requests to remove an existing resource must include "If-Unmodified-Since" and "If-Match" headers whose values must match the "Last-Modified" and "Etag" headers from the response to a GET of that same resource.  Let's examine the response headers to get those two values::

    $ curl -i http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/ 
    HTTP/1.1 200 OK
    Content-Length: 660
    Content-Type: application/hal+json; charset=UTF-8
    Date: Mon, 24 Dec 2012 20:13:42 GMT
    Etag: "52779a9953bd01defd439bd29874c3d4"
    Last-Modified: Mon, 24 Dec 2012 01:52:45 GMT
    Server: waitress

    {"_links": {"audrey:file": [], "self": {"href": "http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/"}, "collection": {"href": "http://127.0.0.1:6543/people/"}, "curie": {"href": "http://127.0.0.1:6543/relations/{rel}", "name": "audrey", "templated": true}, "audrey:reference": [], "describedby": {"href": "http://127.0.0.1:6543/people/@@schema/person"}}, "photo": null, "firstname": "Audrey", "lastname": "Horne", "_modified": "2012-12-24T01:52:45.281000+00:00", "_created": "2012-12-24T01:52:45.281000+00:00", "_title": "Audrey Horne", "_id": {"ObjectId": "50d7b56dbf90af0e96bc8433"}, "_etag": "52779a9953bd01defd439bd29874c3d4", "_object_type": "person"}

Now let's try that PUT again with the two headers for OCC::

    $ curl -i -H 'If-Unmodified-Since:Mon, 24 Dec 2012 01:52:45 GMT' \
    -H 'If-Match:"52779a9953bd01defd439bd29874c3d4"' \
    -XPUT http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/ -d '{
        "_object_type": "person",
        "firstname": "Audrey",
        "lastname": "Horne",
        "photo":  {"FileId": "50d8a64bbf90af0d7169df5e"}
    }'
    HTTP/1.1 204 No Content
    Content-Length: 0
    Location: http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 24 Dec 2012 20:19:23 GMT
    Server: waitress

Success!  Let's confirm the change by doing another GET::

    $ curl http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/ | python -mjson.tool
    {
        "_created": "2012-12-24T01:52:45.281000+00:00", 
        "_etag": "3c418f678d1cb636fca4cadc599bf725", 
        "_id": {
            "ObjectId": "50d7b56dbf90af0e96bc8433"
        }, 
        "_links": {
            "audrey:file": [
                {
                    "href": "http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/@@download/50d8a64bbf90af0d7169df5e", 
                    "name": "50d8a64bbf90af0d7169df5e", 
                    "type": "image/jpeg"
                }
            ], 
            "audrey:reference": [], 
            "collection": {
                "href": "http://127.0.0.1:6543/people/"
            }, 
            "curie": {
                "href": "http://127.0.0.1:6543/relations/{rel}", 
                "name": "audrey", 
                "templated": true
            }, 
            "describedby": {
                "href": "http://127.0.0.1:6543/people/@@schema/person"
            }, 
            "self": {
                "href": "http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/"
            }
        }, 
        "_modified": "2012-12-24T20:19:23.660000+00:00", 
        "_object_type": "person", 
        "_title": "Audrey Horne", 
        "firstname": "Audrey", 
        "lastname": "Horne", 
        "photo": {
            "FileId": "50d8a64bbf90af0d7169df5e"
        }
    }

Note that the "photo" is no longer null and the list of "file" links now
contains one item with type="image/jpeg" and name="50d8a64bbf90af0d7169df5e".
A client could match up that name with the value of the photo FileId.

Try viewing the photo by hitting http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/@@download/50d8a64bbf90af0d7169df5e

You could also traverse to the ``photo`` attribute like so:
http://127.0.0.1:6543/people/50d7b56dbf90af0e96bc8433/photo


As our final stop before ending this introduction, let's try out the search api.
We'll do a search for "dale"::

    $ curl http://127.0.0.1:6543/@@search?q=dale | python -mjson.tool
    {
        "_links": {
            "item": [
                {
                    "href": "http://127.0.0.1:6543/people/50d7b986bf90af0e96bc8434/", 
                    "name": "people:50d7b986bf90af0e96bc8434", 
                    "title": "Dale Cooper"
                }
            ], 
            "self": {
                "href": "http://127.0.0.1:6543/@@search?q=dale"
            }
        }, 
        "_summary": {
            "batch": 1, 
            "collections": [], 
            "per_batch": 20, 
            "q": "dale", 
            "sort": null, 
            "total_batches": 1, 
            "total_items": 1
        }
    }

The search found Dale's ``Person`` object.  As you might guess, if there were lots of results they would be batched with "next" and "prev" links.

Well that wraps up this introduction.  It didn't cover all of Audrey's functionality and nuances, but hopefully it provided a sufficient taste.
