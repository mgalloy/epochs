#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `epochs` package."""

import pytest

import epochs


def test_convert():
    value = epochs.parser.convert('True', bool)
    assert(value == True)
    assert(type(value) == bool)

    value = epochs.parser.convert('False', bool)
    assert(value == False)
    assert(type(value) == bool)

    value = epochs.parser.convert('1.23', float)
    assert(abs(value - 1.23) < 0.001)
    assert(type(value) == float)


@pytest.mark.xfail(raises=ValueError)
def test_convert_error():
    value = epochs.parser.convert('other', bool)


def test_parse_specline():
    spec = epochs.parser.parse_specline('t : required=True, type=int, default=1')
    assert(spec.name == 't')
    assert(spec.required == True)
    assert(spec.type == int)
    assert(spec.default == 1)

    spec = epochs.parser.parse_specline('_name_ : type=float, default=1')
    assert(spec.name == '_name_')
    assert(spec.required == False)
    assert(spec.type == float)
    assert(spec.default == 1.0)

    spec = epochs.parser.parse_specline('name.subname : default=1')
    assert(spec.name == 'name.subname')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default == '1')

    spec = epochs.parser.parse_specline('name :')
    assert(spec.name == 'name')
    assert(spec.required == False)
    assert(spec.type == str)
    assert(spec.default is None)