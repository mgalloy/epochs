# -*- coding: utf-8 -*-

"""Main module."""

import collections
import configparser
import re
from typing import List, TypeVar


OptionValue = TypeVar('OptionValue',
                      bool, float, int, str,
                      List[bool], List[float], List[int], List[str])

OptionSpec = collections.namedtuple('OptionSpec', 'required type default list')

TYPES = {'bool': bool, 'boolean': bool, 'float': float, 'int': int, 'str': str}

identifier_re = re.compile('[.\w\[\]]')
whitespace_re = re.compile('\s')
listtypes_re  = re.compile('List\[(.*)\]')


def _parse_specline_tokens(specline: str) -> OptionSpec:
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
                elif c in {'=', ','}:
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


def _parse_list(list_expr):
    list_expr = list_expr.strip()
    if list_expr[0] != '[' or list_expr[-1] != ']':
        raise ValueError(f'invalid list expr "{list_expr}"')
    list_expr = list_expr[1:-1]
    return list_expr.split(', ')


def _str2type(s: str) -> OptionValue:
    '''Convert a string type specification to the actual type

    Parameters
    ----------
    s : str
        string specification of a type

    Returns
    -------
    type
    '''
    if s.lower() in set(TYPES):
        return TYPES[s.lower()]
    else:
        raise ValueError(f'invalid type: {s}')


def _convert(value: str, type_value: type, is_list: bool=False) -> OptionValue:
    '''Convert a value to a given type

    Parameters
    ----------
    value : str
        value to convert
    type_value : type
        type to convert `value` to
    is_list : bool
        whether `value` is a list or just a scalar

    Returns
    -------
    scalar or List with same type as type_value
    '''
    if is_list:
        return [_convert(v, type_value, False) for v in _parse_list(value) if v != '']
    else:
        if type_value == bool:
            if value.lower() in {'yes', 'true', '1'}:
                return True
            elif value.lower() in {'no', 'false', '0'}:
                return False
            else:
                raise ValueError(f'invalid value "{value}" for bool type')
        else:
            return type_value(value)


def _parse_specline(specline) -> OptionSpec:
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
    tokens = _parse_specline_tokens(specline)

    # default attributes
    required   = False
    type_value = str
    default    = None
    is_list    = False

    try:
        while True:
            attr_name  = next(tokens)
            equals     = next(tokens)
            attr_value = next(tokens)

            # handle attribute
            if attr_name.lower() == 'required':
                required = _convert(attr_value, bool, False)
            elif attr_name.lower() == 'type':
                m = listtypes_re.match(attr_value)
                if m:
                    type_value = _str2type(m[1])
                    is_list = True
                else:
                    type_value = _str2type(attr_value)
            elif attr_name.lower() == 'default':
                default = attr_value
            else:
                raise ValueError(f'invalid attribute {attr}')

            comma      = next(tokens)
    except StopIteration:
        pass

    # convert default value to spec type
    if default is not None:
        default = _convert(default, type_value, is_list)

    return OptionSpec(required=required, type=type_value, default=default, list=is_list)


class ConfigParser(configparser.ConfigParser):
    '''ConfigParser subclass which can verify a config file against a
    specification and uses types/defaults from the specification.
    '''

    def __init__(self, spec_filename: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.specification = configparser.ConfigParser()
        self.specification.read(spec_filename)

    def get(self, section: str, option: str, raw=False,
            **kwargs) -> OptionValue:
        '''Get an option using the type and default from the specification file
        '''
        specline = self.specification.get(section, option)
        spec = _parse_specline(specline)

        if not super().has_option(section, option):
            return spec.default

        value = super().get(section, option, raw=raw, **kwargs)

        return value if raw else _convert(value, spec.type, spec.list)

    def _write(self, fileobject) -> None:
        max_len = 0
        for s in self.specification.sections():
            for o in self.specification.options(s):
                max_len = max(max_len, len(o))

        new_line = '\n'
        first_section = True
        for s in self.specification.sections():
            new_line = '' if first_section else '\n'
            fileobject.write(f'{new_line}[{s}]\n')
            first_section = False
            for o in self.specification.options(s):
                v = self.typed_get(s, o)
                fileobject.write(f'{o:{max_len}s} = {v}\n')

    def write(self, file) -> None:
        if isinstance(file, str):
            with open(file, 'w') as f:
                self._write(f)
        else:
            self._write(file)

    def __str__(self) -> str:
        f = io.StringIO()
        self._write(f)
        f.seek(0)
        return f.read()

    def is_valid(self) -> bool:
        '''Verify that the configparser matches the specification.
        '''
        # check that every option given by f is in specification
        for s in self.sections():
            for o in self.options(s):
                if self.has_option('DEFAULT', o):
                    continue
                if not self.specification.has_option(s, o):
                    return False

        # check that all options without a default value are given by f
        for s in self.specification.sections():
            for o in self.specification.options(s):
                if self.specification.has_option('DEFAULT', o):
                    continue
                specline = self.specification.get(s, o)
                spec = _parse_specline(specline)
                if spec.default is None:
                    if not self.has_option(s, o):
                        return False

        # TODO: make sure values are the correct type

        return True


class EpochParser():
    pass
