#! /usr/bin/env python

from SisPy.lib import SisPy
from SisPy.lib import OutletCurrentSchedule

import pytest


@pytest.fixture
def sispy():
    return SisPy()


@pytest.fixture
def outlet_current_schedule_data_ok_off():
    return bytearray([0x01, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_long_time():
    return bytearray([0x01, 0x2, 0x30])


@pytest.fixture
def outlet_current_schedule_data_ok_on():
    return bytearray([0x01, 0x2, 0x80])


@pytest.fixture
def outlet_current_schedule_data_error_off():
    return bytearray([0x81, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_rampup():
    return bytearray([0x10, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_done():
    return bytearray([0x02, 0x0, 0x0])


def test_mock(sispy):
    assert isinstance(sispy, SisPy)


def test_property_defaults(sispy):
    assert sispy.nr_outlets == 4
    assert sispy.count_outlets_from_1 is True
    sispy.count_outlets_from_1 = False
    assert sispy.count_outlets_from_1 is False
    assert sispy.time_in_GMT is True
    sispy.time_in_GMT = False
    assert sispy.time_in_GMT is False


def _test_outlet_current_schedule(current_schedule, sispy, timing_error=False, switched_it_on=False, time_to_next_schedule=2,
                                  next_schedule_nr=2, sequence_rampup=False, sequence_done=False):
    assert current_schedule.timing_error == timing_error
    assert current_schedule.switched_it_on == switched_it_on
    assert current_schedule.time_to_next_schedule == time_to_next_schedule
    assert current_schedule.next_schedule_nr == next_schedule_nr
    assert current_schedule.sequence_rampup == sequence_rampup
    assert current_schedule.sequence_done == sequence_done

    sispy.count_outlets_from_1 = False
    assert current_schedule.next_schedule_nr == next_schedule_nr - 1


def test_outlet_current_schedule_ok_off(sispy, outlet_current_schedule_data_ok_off):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_off, sispy)
    _test_outlet_current_schedule(current_schedule, sispy)


def test_outlet_current_schedule_ok_off_long_time(sispy, outlet_current_schedule_data_ok_off_long_time):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_off_long_time, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, time_to_next_schedule=12290)


def test_outlet_current_schedule_error_off(sispy, outlet_current_schedule_data_error_off):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_error_off, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, timing_error=True)


def test_outlet_current_schedule_ok_on(sispy, outlet_current_schedule_data_ok_on):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_on, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, switched_it_on=True)


def test_outlet_current_schedule_ok_off_rampup(sispy, outlet_current_schedule_data_ok_off_rampup):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_off_rampup, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, sequence_rampup=True, next_schedule_nr=1)


def test_outlet_current_schedule_ok_off_done(sispy, outlet_current_schedule_data_ok_off_done):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_off_done, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, sequence_done=True, time_to_next_schedule=0, next_schedule_nr=3)

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
