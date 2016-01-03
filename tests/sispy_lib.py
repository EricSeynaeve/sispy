#! /usr/bin/env python

from SisPy.lib import SisPy

import pytest


@pytest.fixture
def sispy(tmpdir):
  return SisPy()

def test_mock(tmpdir, sispy):
  assert isinstance(sispy, SisPy)

def test_property_defaults(tmpdir, sispy):
  assert sispy.nr_outlets == 4
  assert sispy.count_outlets_from_1 == True
  sispy.count_outlets_from_1 = False
  assert sispy.count_outlets_from_1 == False
  assert sispy.time_in_GMT == True
  sispy.time_in_GMT = False
  assert sispy.time_in_GMT == False

# vim: set ai tabstop=2 shiftwidth=2 expandtab :
