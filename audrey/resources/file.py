from pyramid.response import Response
from gridfs.errors import NoFile
from pyramid.httpexceptions import HTTPNotFound

class File(object):
    """ Wrapper around a GridFS file.
    Instances of Object use this File type for attributes 
    that refer to files in the GridFS.
    """

    def __init__(self, _id):
        self._id = _id

    def get_gridfs_file(self, request):
        """ Returns an instance of :class:`gridfs.grid_file.GridOut`
        for the GridFS file that this File object refers to by ID.
        If no match in GridFS is found, returns ``None``.
        """
        # Would use reify, but we need access to a request to get to gridfs.
        if hasattr(self, '_gridfs_file'):
            return self._gridfs_file
        try:
            self._gridfs_file = request.registry.settings['gridfs'].get(self._id)
        except NoFile, e:
            self._gridfs_file = None
        return self._gridfs_file

    def __json__(self, request):
        return dict(FileId=str(self._id))

    def __cmp__(self, other):
        return cmp(self._id, other._id)

    def serve(self, request):
        """ Serve the GridFS file referred to by this object.
        Returns a :class:`pyramid.response.Response` if a matching file was found in the GridFS.
        Otherwise returns :class:`pyramid.httpexceptions.HTTPNotFound`.
        """
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


