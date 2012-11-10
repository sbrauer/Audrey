class SortSpec(object):
    """ It seems that everything that supports sorting has a different
    way of specifying the sort parameters.
    SortSpec tries to be a generic way to specify sort parms, and
    has methods to convert to sort specifications used by other 
    systems in Audrey (MongoDB and Elastic).

    SortSpec's preferred way to represent sort parms is as a 
    comma-delimited string.  Each part of the string is a field name
    optionally prefixed with a plus or minus sign.  Minus indicates 
    descending order; plus (or the absence of a sign) indicates ascending.

    Example: "foo,-bar" or "+foo,-bar"
    both indicate primary sort by "foo" ascending
    and secondary sort by "bar" descending.

    Rationale: Strings are easy to sling around as HTTP query parameters
    (compared for example to Mongo's sequence of two-tuples).
    This string format is as simple, concise and understandable
    (even for normal folks) as I could come up with (contrast with
    Elastic's more verbose ":desc" suffixes).
    """

    def __init__(self, sort_string=None):
        # fields is a list of two-item tuples.
        # the first item is a name string
        # the second is a boolean: True for ascending, False for descending
        self.fields = []
        if sort_string:
            self.set_from_string(sort_string)

    def add_field(self, name, ascending):
        self.fields.append((name, ascending))

    def set_from_string(self, sort_string):
        self.fields = []
        for part in sort_string.split(','):
            ascending = True
            if part.startswith('-'):
                ascending = False
                name = part[1:]
            elif part.startswith('+'):
                name = part[1:]
            else:
                name = part
            self.add_field(name, ascending)

    def to_string(self, pluses=False):
        parts = []
        for (name, ascending) in self.fields:
            pm = ''
            if ascending:
                if pluses:
                    pm = '+'
            else:
                pm = '-'
            parts.append('%s%s' % (pm, name))
        return ','.join(parts)

    def __str__(self):
        return self.to_string()

    def to_mongo(self):
        return [(name, ascending and 1 or -1) for (name, ascending) in self.fields]

    def to_elastic(self):
        return ','.join([ascending and name or name+':desc' for (name, ascending) in self.fields])

# Some convenience functions:

def sort_string_to_mongo(sort_string):
    return SortSpec(sort_string).to_mongo()

def sort_string_to_elastic(sort_string):
    return SortSpec(sort_string).to_elastic()
