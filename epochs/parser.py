# -*- coding: utf-8 -*-

"""Module defining parsers. The ``ConfigParser`` is an extended
``configparser`` that can use a specification file to define types/default
values for the config files options, as well as to validate the file against.
The ``EpochParser`` is a parser which organizes options by date. An option
value is found by matching the option in the section with the latest datetime
before the given datetime."""

import collections
import configparser
import datetime
import io
import re
from typing import List, TypeVar, TextIO

import dateutil.parser


OptionValue = TypeVar('OptionValue',
                      bool, float, int, str,
                      List[bool], List[float], List[int], List[str])
DateValue = TypeVar('DateValue', str, datetime.datetime)
FileType = TypeVar('FileType', str, TextIO)

OptionSpec = collections.namedtuple('OptionSpec', 'required type default list')
OptionSpec.__doc__ = '''Specification for an option'''

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
        whether ``value`` is a list or just a scalar

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


def _parse_specline(specline: str) -> OptionSpec:
    '''Parse a spec line

    Parameters
    ----------
    specline : str
        spec line to parse

    Returns
    -------
    NamedTuple
        fields required, type, default, and list
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

    def __init__(self, spec_filename: str=None, **kwargs) -> None:
        '''Create a ConfigParser object

        spec_filename : str
            file to use as a specification
        '''
        super().__init__(**kwargs)

        self.spec_filename = spec_filename

        if spec_filename is None:
            self.specification = None
        else:
            self.specification = configparser.ConfigParser()
            self.specification.read(spec_filename)

    def get(self, section: str, option: str,
            raw: bool=False, use_spec: bool=True, **kwargs) -> OptionValue:
        '''Get an option using the type and default from the specification file

        Parameters
        ----------
        section : str
            section name
        option : str
            option name
        raw : bool
            set to True to not interpolate
        use_spec : bool
            set to False to not use the specification
        '''
        if self.specification is None or use_spec == False:
            return super().get(section, option, raw=raw, **kwargs)

        specline = self.specification.get(section, option)
        spec = _parse_specline(specline)

        if not super().has_option(section, option):
            return spec.default

        value = super().get(section, option, raw=raw, **kwargs)

        return value if raw else _convert(value, spec.type, spec.list)

    def _write(self, fileobject: TextIO) -> None:
        '''Write the configuration to a file-like object

        Parameters
        ----------
        fileobject : TextIO
            file-like object to write to
        '''
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
                v = self.get(s, o)
                fileobject.write(f'{o:{max_len}s} = {v}\n')

    def write(self, file: FileType, space_around_delimiters: bool=True) -> None:
        '''Write config file to a file-like object

        Parameters
        ----------
        file : FileType
            file-like object to write to
        space_around_delimiters : bool
            whether to put spaces around the delimiter, i.e., ":" or "="
        '''
        if isinstance(file, str):
            with open(file, 'w') as f:
                self._write(f)
        else:
            self._write(file)

    def __repr__(self) -> str:
        '''Representation of config file
        '''
        return f'{self.__class__.__name__}("{self.spec_filename}")'

    def __str__(self) -> str:
        '''Config file as a string
        '''
        f = io.StringIO()
        self._write(f)
        f.seek(0)
        return f.read()

    # TODO: probably should have option to not check certain aspects, e.g.,
    # sometimes its probably OK to have extra options not in the spec
    def is_valid(self) -> bool:
        '''Verify that the ``ConfigParser`` matches the specification. A
        ``ConfigParser`` without a spec is automatically valid.
        '''
        if self.specification is None:
            return True

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


def _parse_datetime(d : DateValue) -> datetime.datetime:
    if isinstance(d, datetime.datetime):
        return d
    else:
        return dateutil.parser.parse(d)


class EpochParser(ConfigParser):
    '''EpochParser parses config files with dates as section name. Retrieving an
    option for a given date returns the option value on the date closest, but
    before, the given date.
    '''

    def __init__(self, spec_filename: str=None, **kwargs) -> None:
        super().__init__(spec_filename, **kwargs)
        self._date = None

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, date: DateValue):
        '''
        Parameters
        ----------
        date : DateValue
            date as a string or ``datetime.datetime``
        '''
        self._date = _parse_datetime(date)

    def get(self, option: str,
            date: DateValue=None, raw: bool=False, **kwargs) -> OptionValue:
        '''Get an option using the type and default from the specification file

        Parameters
        ----------
        option : str
            option name
        date : FileValue
            date as a string or ``datetime.datetime``
        raw : bool
            set to True is disable interpolation
        '''
        dt = self._date if date is None else _parse_datetime(date)
        if dt is None:
            raise KeyError('no date for access given')

        specs = {k: _parse_specline(v) for k, v in self.specification.defaults().items()}

        epoch_names = self.sections()

        epoch_dts = [_parse_datetime(s) for s in epoch_names]
        sorted_epoch_dts = sorted(zip(epoch_dts, epoch_names), key=lambda x: x[0])

        value = specs[option].default
        for e_dt, e_name in sorted_epoch_dts:
            if e_dt <= dt and self.has_option(e_name, option):
                value = _convert(super().get(e_name, option, raw=True, use_spec=False),
                                 specs[option].type,
                                 specs[option].list)

        return value

    def is_valid(self) -> bool:
        '''Verify that the `EpochParser` matches the specification. A
        `configparser` without a spec is automatically valid.
        '''
        if self.specification is None:
            return True

        # check to make sure sections are dates
        for s in self.sections():
            try:
                d = dateutil.parser.parse(s)
            except ValueError:
                return False

        # check options are in spec
        for s in self.sections():
            for o in self.options(s):
                if not self.specification.has_option('DEFAULT', o):
                    return False

        return True
