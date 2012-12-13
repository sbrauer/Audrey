from pyramid.response import Response
from gridfs.errors import NoFile
from pyramid.httpexceptions import HTTPNotFound

class File(object):
    """ Wrapper around a GridFS file.
    Instances of BaseObject use this File type for attributes 
    that refer to files in the GridFS.
    """

    def __init__(self, _id):
        self._id = _id

    def get_gridfs_file(self, request):
        # Would use reify, but we need access to a request to get to gridfs.
        if hasattr(self, '_gridfs_file'):
            return self._gridfs_file
        try:
            self._gridfs_file = request.registry.settings['gridfs'].get(self._id)
        except NoFile, e:
            self._gridfs_file = None
        return self._gridfs_file

    def __json__(self, request):
        return str(self._id)

    def __cmp__(self, other):
        return cmp(self._id, other._id)

    def serve(self, request):
        file = self.get_gridfs_file(request)
        if file is None:
            return HTTPNotFound("No file found for %s." % repr(self._id))
        response = Response()
        response.content_type = str(file.content_type)
        response.last_modified = file.upload_date
        response.etag = file.md5
        for chunk in file:
            response.body_file.write(chunk)
        file.close()
        response.content_length = file.length
        return response

