# -*- coding: utf-8 -*-

"""Main module."""

import collections
import re


OptionSpec = collections.namedtuple('OptionSpec', 'name required type default')

identifier_re = re.compile('[.\w]')
whitespace_re = re.compile('\s')


def parse_specline_tokens(specline):
    '''Generator to tokenize spec line

    Parameters
    ----------
    specline : str
        spec line to tokenize

    Yields
    ------
    str
    '''
    identifier = ''
    in_quote = False
    for c in specline:
        if c == '"':
            if in_quote:
                yield identifier
                identifier = ''
                in_quote = False
            else:
                in_quote = True
        else:
            if in_quote:
                identifier += c
            else:
                if identifier_re.match(c):
                    identifier += c
                elif c in {':', '=', ','}:
                    if identifier != '':
                        yield identifier
                        identifier = ''
                    yield c
                elif whitespace_re.match(c):
                    if identifier != '':
                        yield identifier
                        identifier = ''
                else:
                    # invalid token
                    raise ValueError(f'invalid token {c}')

    if identifier != '':
        yield identifier


def str2type(s):
    '''Convert a string type specification to the actual type

    Parameters
    ----------
    s : str
        string specification of a type

    Returns
    -------
    type
    '''
    s = s.lower()
    if s == 'str':
        return str
    elif s == 'int':
        return int
    elif s == 'float':
        return float
    elif s in {'bool', 'boolean'}:
        return bool
    else:
        raise ValueError(f'invalid type: {s}')


def convert(value, type_value):
    '''Convert a value to a given type

    Parameters
    ----------
    value : str
        value to convert
    type_value : type
        type to convert `value` to

    Returns
    -------
    type_value
    '''
    if type_value == bool:
        if value.lower() in {'true', '1'}:
            return True
        elif value.lower() in {'false', '0'}:
            return False
        else:
            raise ValueError(f'syntax error: invalid value for bool type {value}')
    else:
        return type_value(value)


def parse_specline(specline):
    '''Parse a spec line

    Parameters
    ----------
    specline : str
        spec line to parse

    Returns
    -------
    NamedTuple
        fields name, required, type, default
    '''
    tokens = parse_specline_tokens(specline)

    # default attributes
    required   = False
    type_value = str
    default    = None

    name  = next(tokens)

    colon = next(tokens)
    if colon != ':': raise ValueError(f'syntax error at {colon}')

    try:
        while True:
            attr_name  = next(tokens)
            equals     = next(tokens)
            attr_value = next(tokens)

            # handle attribute
            if attr_name.lower() == 'required':
                if attr_value.lower() == 'true':
                    required = True
                elif attr_value.lower() == 'false':
                    required = False
                else:
                    raise ValueError(f'syntax error: invalid required value {attr_value}')
            elif attr_name.lower() == 'type':
                type_value = str2type(attr_value)
            elif attr_name.lower() == 'default':
                default = attr_value
            else:
                raise ValueError(f'syntax error: invalid attribute {attr}')

            comma      = next(tokens)
    except StopIteration:
        pass

    # convert default value to spec type
    if default is not None:
        default = convert(default, type_value)

    return (OptionSpec(name=name, required=required, type=type_value, default=default))

