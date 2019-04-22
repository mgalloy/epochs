#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `epochs` package."""

import os
import pytest

import epochs

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(REPO_DIR, 'data')


def test_str2type():
    assert(epochs.parser._str2type('str') == str)
    assert(epochs.parser._str2type('int') == int)
    assert(epochs.parser._str2type('float') == float)
    assert(epochs.parser._str2type('bool') == bool)
    assert(epochs.parser._str2type('boolean') == bool)


@pytest.mark.xfail(raises=ValueError)
def test_str2type_error():
    t = epochs.parser._str2type('other')


def test_convert():
    value = epochs.parser._convert('True', bool, False)
    assert(value == True)
    assert(type(value) == bool)

    value = epochs.parser._convert('False', bool, False)
    assert(value == False)
    assert(type(value) == bool)

    value = epochs.parser._convert('1.23', float, False)
    assert(abs(value - 1.23) < 0.001)
    assert(type(value) == float)

    value = epochs.parser._convert('123', int, False)
    assert(value == 123)
    assert(type(value) == int)


def lists_equal(lst1, lst2):
    for l1, l2 in zip(lst1, lst2):
        assert(l1 == l2)


def test_convert_list():
    value = epochs.parser._convert('[a, b, c]', str, True)
    lists_equal(value, ['a', 'b', 'c'])
    assert(type(value) == list)


@pytest.mark.xfail(raises=ValueError)
def test_convert_error():
    value = epochs.parser._convert('other', bool, False)


def test_parse_specline_truth():
    for v in ['True', 'true', 'Yes', 'yes']:
        spec = epochs.parser._parse_specline(f'required={v}, type=int, default=1')
        assert(spec.required == True)
        assert(spec.type == int)
        assert(spec.default == 1)


def test_parse_specline():
    spec = epochs.parser._parse_specline('type=float, default=1')
    assert(spec.required == False)
    assert(spec.type == float)
    assert(spec.default == 1.0)
    assert(spec.list == False)

    spec = epochs.parser._parse_specline('default=1')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default == '1')
    assert(spec.list == False)

    spec = epochs.parser._parse_specline('')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default is None)
    assert(spec.list == False)

    spec = epochs.parser._parse_specline('default="Boulder, CO"')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default == 'Boulder, CO')
    assert(spec.list == False)

    spec = epochs.parser._parse_specline('type=List[int], default="[1, 3, 7]"')
    assert(spec.required == False)
    assert(spec.type == int)
    lists_equal(spec.default, [1, 3, 7])
    assert(spec.list == True)


def test_configparser():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'user.cfg'))

    basedir = cp.get('logging', 'basedir')
    assert(basedir == '/Users/mgalloy/data')
    assert(type(basedir) == str)

    rotate = cp.get('logging', 'rotate')
    assert(not rotate)
    assert(type(rotate) == bool)

    max_version = cp.get('logging', 'max_version')
    assert(max_version == 3)
    assert(type(max_version) == int)

    wavetypes = cp.get('level1', 'wavetypes')
    assert(len(wavetypes) == 3)
    assert(type(wavetypes) == list)
    assert(wavetypes[0] == '1074')
    assert(wavetypes[1] == '1079')
    assert(wavetypes[2] == '1083')


def test_configparser_is_valid():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'user.cfg'))
    assert(cp.is_valid())


def test_configparser_is_notvalid():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'site.cfg'))
    assert(not cp.is_valid())   # no basedir which is required


def test_inheritance():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read([os.path.join(DATA_DIR, 'site.cfg'),
             os.path.join(DATA_DIR, 'user.cfg')])
    max_version = cp.get('logging', 'max_version')
    assert(max_version == 3)
    assert(cp.is_valid())

    max_width = cp.get('logging', 'max_width')
    assert(max_width == 100)


def test_epochparser():
    ep = epochs.EpochParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs.cfg'))

    cal_version = ep.get('cal_version', '2017-12-31')
    assert(type(cal_version) == int)
    assert(cal_version == 0)

    cal_version = ep.get('cal_version', '2018-01-01 06:00:00')
    assert(type(cal_version) == int)
    assert(cal_version == 1)

    cal_version = ep.get('cal_version', '2018-01-01 10:00:00')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    cal_version = ep.get('cal_version', '2018-01-02 10:00:00')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    cal_version = ep.get('cal_version', '2018-01-03 06:00:00')
    assert(type(cal_version) == int)
    assert(cal_version == 3)


def test_epochparser_property():
    ep = epochs.EpochParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs.cfg'))

    ep.date = '2017-12-31'
    cal_version = ep.get('cal_version')
    assert(type(cal_version) == int)
    assert(cal_version == 0)

    ep.date = '2018-01-01 06:00:00'
    cal_version = ep.get('cal_version')
    assert(type(cal_version) == int)
    assert(cal_version == 1)

    ep.date = '2018-01-01 10:00:00'
    cal_version = ep.get('cal_version')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    ep.date = '2018-01-02 10:00:00'
    cal_version = ep.get('cal_version')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    ep.date = '2018-01-03 06:00:00'
    cal_version = ep.get('cal_version')
    assert(type(cal_version) == int)
    assert(cal_version == 3)


def test_epochparser_is_valid():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'epochs_.cfg'))
    assert(cp.is_valid())


def test_epochparser_is_notvalid():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'epochs_extra.cfg'))
    assert(not cp.is_valid())   # has "extra_option" which is not in spec
