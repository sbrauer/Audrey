import colander

class SchemaConverter(object):
    """ Converts a colander schema to a JSON Schema (expressed
    as a data structure consisting of primitive Python types, 
    suitable from serializing to JSON).
    """

    def __init__(self):
        self.converters = {
            colander.Mapping: self.convert_mapping,
            colander.Sequence: self.convert_sequence,
            colander.Tuple: self.convert_tuple,
            colander.String: self.convert_string,
            colander.Integer: self.convert_integer,
            colander.Float: self.convert_number,
            colander.Decimal: self.convert_number,
            colander.Money: self.convert_number,
            colander.Boolean: self.convert_boolean,
            colander.DateTime: self.convert_datetime,
            colander.Date: self.convert_date,
            colander.Time: self.convert_time,
        }

    def to_jsonschema(self, node):
        nodetype = type(node.typ)
        converter = self.converters.get(nodetype)
        if converter is None:
            raise ValueError, "Unexpected node type: %r" % nodetype
        else:
            ret = converter(node)
            ret['title'] = node.title
            ret['description'] = node.description
            if node.default != colander.null:
                ret['default'] = node.default
            return ret

    def convert_mapping(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'object'
            ret['required'] = True
        else:
            ret['type'] = ['null', 'object']
            ret['required'] = False
        props = {}
        ret['properties'] = props
        for cnode in node.children:
            name = cnode.name
            props[name] = self.to_jsonschema(cnode)
        return ret

    def convert_tuple(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'array'
            ret['required'] = True
        else:
            ret['type'] = ['null', 'array']
            ret['required'] = False
        items = []
        ret['items'] = items
        for cnode in node.children:
            items.append(self.to_jsonschema(cnode))
        return ret

    def convert_sequence(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'array'
            ret['required'] = True
        else:
            ret['type'] = ['null', 'array']
            ret['required'] = False
        ret['items'] = self.to_jsonschema(node.children[0])

        for v in self.normalize_node_validators(node):
            if type(v) == colander.Length:
                if v.min is not None:
                    ret['minItems'] = v.min
                if v.max is not None:
                    ret['maxItems'] = v.max
        return ret

    def convert_datetime(self, node, format='date-time'):
        ret = {}
        if node.required:
            ret['type'] = 'string'
            ret['minLength'] = 1
            ret['required'] = True
        else:
            ret['type'] = ['null', 'string']
            ret['required'] = False
        ret['format'] = format
        return ret

    def convert_date(self, node):
        return self.convert_datetime(node, format='date')

    def convert_time(self, node):
        return self.convert_datetime(node, format='time')

    def convert_string(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'string'
            ret['minLength'] = 1
            ret['required'] = True
        else:
            ret['type'] = ['null', 'string']
            ret['required'] = False

        for v in self.normalize_node_validators(node):
            if type(v) == colander.Length:
                if v.min is not None:
                    ret['minLength'] = v.min
                if v.max is not None:
                    ret['maxLength'] = v.max
            elif type(v) == colander.Email:
                ret['format'] = 'email'
            elif type(v) == colander.Regex:
                ret['pattern'] = v.match_object.pattern
            elif type(v) == colander.OneOf:
                ret['enum'] = v.choices
        return ret

    def convert_number(self, node, typename='number'):
        ret = {}
        if node.required:
            ret['type'] = typename
            ret['required'] = True
        else:
            ret['type'] = ['null', typename]
            ret['required'] = False

        for v in self.normalize_node_validators(node):
            if type(v) == colander.Range:
                if v.min is not None:
                    ret['minimum'] = v.min
                if v.max is not None:
                    ret['maximum'] = v.max
            elif type(v) == colander.OneOf:
                ret['enum'] = v.choices
        return ret

    def convert_integer(self, node):
        return self.convert_number(node, typename='integer')

    def convert_boolean(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'boolean'
            ret['required'] = True
        else:
            ret['type'] = ['null', 'boolean']
            ret['required'] = False
        return ret

    def normalize_node_validators(self, node):
        # Returns a sequence (possibly empty) of validators.
        ret = []
        if node.validator is not None:
            if type(node.validator) == colander.All:
                ret = node.validator.validators
            else:
                ret.append(node.validator)
        return ret

# FIXME: move SchemaConverter into a separate module/package...?
# Seems like it could be useful outside of Audrey.

import audrey.types

OBJECTID_REGEX = '^[0-9a-f]{24}$'

class AudreySchemaConverter(SchemaConverter):

    # FIXME: add ObjectId and DBRef converters

    def convert_gridfile(self, node):
        ret = {}
        if node.required:
            ret['type'] = 'object'
            ret['required'] = True
        else:
            ret['type'] = ['null', 'object']
            ret['required'] = False
        ret['properties'] = dict(
            FileId=dict(type='string', required=True, pattern=OBJECTID_REGEX)
        )
        return ret

    def __init__(self):
        SchemaConverter.__init__(self)
        self.converters[audrey.types.GridFile] = self.convert_gridfile

