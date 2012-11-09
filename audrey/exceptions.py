class Veto(Exception):
    """ May be raised when an attempt is made to do something that the app
    doesn't allow, such as adding an object to a folder with a name that's
    already in use.
    Higher level code (such as views) may want to catch these Veto exceptions
    and present them to end users in a friendly manner.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)
