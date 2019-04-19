#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `epochs` package."""

import os
import pytest

import epochs

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_str2type():
    assert(epochs.parser.str2type('str') == str)
    assert(epochs.parser.str2type('int') == int)
    assert(epochs.parser.str2type('float') == float)
    assert(epochs.parser.str2type('bool') == bool)
    assert(epochs.parser.str2type('boolean') == bool)


@pytest.mark.xfail(raises=ValueError)
def test_str2type_error():
    t = epochs.parser.str2type('other')


def test_convert():
    value = epochs.parser.convert('True', bool, False)
    assert(value == True)
    assert(type(value) == bool)

    value = epochs.parser.convert('False', bool, False)
    assert(value == False)
    assert(type(value) == bool)

    value = epochs.parser.convert('1.23', float, False)
    assert(abs(value - 1.23) < 0.001)
    assert(type(value) == float)

    value = epochs.parser.convert('123', int, False)
    assert(value == 123)
    assert(type(value) == int)


def lists_equal(lst1, lst2):
    for l1, l2 in zip(lst1, lst2):
        assert(l1 == l2)


def test_convert_list():
    value = epochs.parser.convert('[a, b, c]', str, True)
    lists_equal(value, ['a', 'b', 'c'])
    assert(type(value) == list)


@pytest.mark.xfail(raises=ValueError)
def test_convert_error():
    value = epochs.parser.convert('other', bool, False)


def test_parse_specline_truth():
    for v in ['True', 'true', 'Yes', 'yes']:
        spec = epochs.parser.parse_specline(f'required={v}, type=int, default=1')
        assert(spec.required == True)
        assert(spec.type == int)
        assert(spec.default == 1)


def test_parse_specline():
    spec = epochs.parser.parse_specline('type=float, default=1')
    assert(spec.required == False)
    assert(spec.type == float)
    assert(spec.default == 1.0)
    assert(spec.list == False)

    spec = epochs.parser.parse_specline('default=1')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default == '1')
    assert(spec.list == False)

    spec = epochs.parser.parse_specline('')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default is None)
    assert(spec.list == False)

    spec = epochs.parser.parse_specline('default="Boulder, CO"')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default == 'Boulder, CO')
    assert(spec.list == False)

    spec = epochs.parser.parse_specline('type=List[int], default="[1, 3, 7]"')
    assert(spec.required == False)
    assert(spec.type == int)
    lists_equal(spec.default, [1, 3, 7])
    assert(spec.list == True)


def test_configparser():
    cp = epochs.ConfigParser(os.path.join(CURRENT_DIR, 'spec.cfg'))
    cp.read(os.path.join(CURRENT_DIR, 'good.cfg'))

    basedir = cp.get('logging', 'basedir')
    assert(basedir == '/Users/mgalloy/data')
    assert(type(basedir) == str)

    rotate = cp.get('logging', 'rotate')
    assert(not rotate)
    assert(type(rotate) == bool)

    max_version = cp.get('logging', 'max_version')
    assert(max_version == 3)
    assert(type(max_version) == int)

    wavelengths = cp.get('level1', 'wavelengths')
    assert(len(wavelengths) == 3)
    assert(type(wavelengths) == list)
    assert(wavelengths[0] == '1074')
    assert(wavelengths[1] == '1079')
    assert(wavelengths[2] == '1083')
