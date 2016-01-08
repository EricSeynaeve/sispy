#! /usr/bin/env python

from SisPy.lib import SisPy
from SisPy.lib import OutletCurrentSchedule
from SisPy.lib import Schedule

import pytest
import time

# test data was obtained in CET
time.altzone = -7200
time.timezone = -3600
time.daylight = 0


@pytest.fixture
def device():
    class MockDevice:
        def in_type(self, value):
            return (value & (1 << 7)) == (1 << 7)

        def ctrl_transfer(self, request_type, request, value=0, index=0, data_or_length=None, timeout=None):
            assert (request_type & (1 << 5 | 1)) == (1 << 5 | 1)
            if self.in_type(request_type) is True:
                assert request == 0x1
            else:
                assert request == 0x9
            assert (value & (3 << 8)) == (3 << 8)
            value = value & (~ (3 << 8))
            assert index == 0
            assert timeout == 500

            if value == 1 and self.in_type(request_type):
                assert data_or_length == 4
                return id_data()
    return MockDevice()


@pytest.fixture
def sispy(device):
    class MockSisPy(SisPy):
        def __init__(self):
            SisPy.__init__(self)

        def _get_device(self):
            return device
    return MockSisPy()


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


@pytest.fixture
def outlet_schedule_data():
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0x3, 0x80, 0x2, 0x0, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_non_periodic():
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0x3, 0x80, 0x2, 0x0, 0x0, 0x0, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_reset():
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_vanilla():
    return bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])


def id_data():
    return bytearray([0x1, 0x2, 0x3, 0x4])


def test_mock(sispy):
    assert isinstance(sispy, SisPy)


def test_property_defaults(sispy):
    assert sispy.id == 67305985
    assert sispy.nr_outlets == 4
    assert sispy.count_outlets_from_1 is True
    sispy.count_outlets_from_1 = False
    assert sispy.count_outlets_from_1 is False


def _test_outlet_current_schedule(current_schedule, sispy, timing_error=False, switched_it_on=False, minutes_to_next_schedule=2,
                                  next_schedule_nr=2, sequence_rampup=False, sequence_done=False):
    assert current_schedule.timing_error == timing_error
    assert current_schedule.switched_it_on == switched_it_on
    assert current_schedule.minutes_to_next_schedule == minutes_to_next_schedule
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
    _test_outlet_current_schedule(current_schedule, sispy, minutes_to_next_schedule=12290)


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
    _test_outlet_current_schedule(current_schedule, sispy, sequence_done=True, minutes_to_next_schedule=0, next_schedule_nr=3)


def test_outlet_schedule(sispy, outlet_schedule_data):
    schedule = Schedule(outlet_schedule_data, sispy)

    # time.strptime doesn't take the timezone information into account. It just assumes it's alwasy in UTC
    # Need to compensate for this in the tests
    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 1
    assert schedule.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is True
    assert schedule.periodicity_minutes == 5
    assert schedule.schedule_minutes is None
    assert schedule.end_time == time.strptime('2999-12-31 23:59:59 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 2

    entry1 = schedule.entries[0]
    assert entry1.switch_on is True
    assert entry1.minutes_to_next_schedule == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_non_periodic(sispy, outlet_schedule_data_non_periodic):
    schedule = Schedule(outlet_schedule_data_non_periodic, sispy)

    # time.strptime doesn't take the timezone information into account. It just assumes it's alwasy in UTC
    # Need to compensate for this in the tests
    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 1
    assert schedule.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 5
    assert schedule.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 2

    entry1 = schedule.entries[0]
    assert entry1.switch_on is True
    assert entry1.minutes_to_next_schedule == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_reset(sispy, outlet_schedule_data_reset):
    schedule = Schedule(outlet_schedule_data_reset, sispy)

    # time.strptime doesn't take the timezone information into account. It just assumes it's alwasy in UTC
    # Need to compensate for this in the tests
    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 0
    assert schedule.start_time == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 0
    assert schedule.end_time == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 0


def test_outlet_schedule_vanilla(sispy, outlet_schedule_data_vanilla):
    schedule = Schedule(outlet_schedule_data_vanilla, sispy)

    assert schedule.time_activated == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 0
    assert schedule.start_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 0
    assert schedule.end_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 0

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
