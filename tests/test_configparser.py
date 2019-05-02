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
    assert(epochs.configparser._str2type('str') == str)
    assert(epochs.configparser._str2type('int') == int)
    assert(epochs.configparser._str2type('float') == float)
    assert(epochs.configparser._str2type('bool') == bool)
    assert(epochs.configparser._str2type('boolean') == bool)


@pytest.mark.xfail(raises=ValueError)
def test_str2type_error():
    epochs.configparser._str2type('other')


def test_convert():
    value = epochs.configparser._convert('True', bool, False)
    assert(value)
    assert(type(value) == bool)

    value = epochs.configparser._convert('False', bool, False)
    assert(value is False)
    assert(type(value) == bool)

    value = epochs.configparser._convert('1.23', float, False)
    assert(abs(value - 1.23) < 0.001)
    assert(type(value) == float)

    value = epochs.configparser._convert('123', int, False)
    assert(value == 123)
    assert(type(value) == int)


def lists_equal(lst1, lst2):
    for l1, l2 in zip(lst1, lst2):
        assert(l1 == l2)


def test_convert_list():
    value = epochs.configparser._convert('[a, b, c]', str, True)
    lists_equal(value, ['a', 'b', 'c'])
    assert(type(value) == list)


@pytest.mark.xfail(raises=ValueError)
def test_convert_error():
    epochs.configparser._convert('other', bool, False)


def test_parse_specline_truth():
    for v in ['True', 'true', 'Yes', 'yes']:
        spec_line = f'required={v}, type=int, default=1'
        spec = epochs.configparser._parse_specline(spec_line)
        assert(spec.required)
        assert(spec.type == int)
        assert(spec.default == 1)


def test_parse_specline():
    spec = epochs.configparser._parse_specline('type=float, default=1')
    assert(spec.required is False)
    assert(spec.type == float)
    assert(spec.default == 1.0)
    assert(spec.list is False)

    spec = epochs.configparser._parse_specline('default=1')
    assert(spec.required is False)
    assert(spec.type == str)
    assert(spec.default == '1')
    assert(spec.list is False)

    spec = epochs.configparser._parse_specline('')
    assert(spec.required is False)
    assert(spec.type == str)
    assert(spec.default is None)
    assert(spec.list is False)

    spec = epochs.configparser._parse_specline('default="Boulder, CO"')
    assert(spec.required is False)
    assert(spec.type == str)
    assert(spec.default == 'Boulder, CO')
    assert(spec.list is False)

    spec = epochs.configparser._parse_specline('type=List[int], default="[1, 3, 7]"')
    assert(spec.required is False)
    assert(spec.type == int)
    lists_equal(spec.default, [1, 3, 7])
    assert(spec.list)


def test_configparser():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'user.cfg'))

    basedir = cp.get('logging', 'basedir')
    assert(basedir == '/export/data1/Data/logs.master')
    assert(type(basedir) == str)

    basename = cp.get('logging', 'basename')
    assert(basename is None)

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

    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'extra.cfg'))
    # has "extra_option" not in spec
    print(cp.is_valid(allow_extra_options=True))
    assert(cp.is_valid(allow_extra_options=True))


def test_configparser_is_notvalid():
    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'site.cfg'))
    assert(not cp.is_valid())   # no basedir which is required

    cp = epochs.ConfigParser(os.path.join(DATA_DIR, 'spec.cfg'))
    cp.read(os.path.join(DATA_DIR, 'extra.cfg'))
    assert(not cp.is_valid())   # has "extra_option" not in spec


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
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
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
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
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
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs_.cfg'))
    assert(ep.is_valid())

    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs_extra.cfg'))
    # has "extra_option" which is not in spec
    assert(ep.is_valid(allow_extra_options=True))


def test_epochparser_is_notvalid():
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs_extra.cfg'))
    assert(not ep.is_valid())   # has "extra_option" which is not in spec


def test_epoch_parser_interp():
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.read(os.path.join(DATA_DIR, 'epochs_interp.cfg'))

    dist_filename = ep.get('dist_filename', '2018-01-02')

    assert(type(dist_filename) == str)
    assert(dist_filename == '/export/data1/Data/dist-1.ncdf')


def test_epoch_parser_format():
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'epochs_spec.cfg'))
    ep.formats = ['%Y%m%d', '%Y%m%d.%H%M%S']
    ep.read(os.path.join(DATA_DIR, 'epochs_format.cfg'))

    cal_version = ep.get('cal_version', '20171231')
    assert(type(cal_version) == int)
    assert(cal_version == 0)

    cal_version = ep.get('cal_version', '20180101.060000')
    assert(type(cal_version) == int)
    assert(cal_version == 1)

    cal_version = ep.get('cal_version', '20180101.100000')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    cal_version = ep.get('cal_version', '20180102.100000')
    assert(type(cal_version) == int)
    assert(cal_version == 2)

    cal_version = ep.get('cal_version', '20180103.060000')
    assert(type(cal_version) == int)
    assert(cal_version == 3)


def test_kcor():
    ep = epochs.EpochConfigParser(os.path.join(DATA_DIR, 'kcor.epochs.spec.cfg'))
    ep.formats = ['%Y%m%d', '%Y%m%d.%H%M%S']
    ep.read(os.path.join(DATA_DIR, 'kcor.epochs.cfg'))

    dist = ep.get('distortion_correction_filename', '20190306.235959')
    assert(type(dist) == str)
    assert(dist == 'dist_coeff_20170522_205121.sav')

    dist = ep.get('distortion_correction_filename', '20190307.000000')
    assert(type(dist) == str)
    assert(dist == 'dist_coeff_20190308_185649_dot1.sav')
