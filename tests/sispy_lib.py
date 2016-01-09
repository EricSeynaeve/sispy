#! /usr/bin/env python

from SisPy.lib import SisPy
from SisPy.lib import OutletCurrentSchedule
from SisPy.lib import Schedule
from SisPy.lib import Outlet

import pytest
import time

# test data was obtained in CET
time.altzone = -7200
time.timezone = -3600
time.daylight = 0


@pytest.fixture
def device():
    class MockDevice:
        def __init__(self):
            self.outlet_on = [True, False, False, True]

        def in_type(self, value):
            return (value & (1 << 7)) == (1 << 7)

        def get_outlet_status(self, outlet_nr):
            assert outlet_nr >= 0
            assert outlet_nr < 4

            if self.outlet_on[outlet_nr] is True:
                return 0x03
            else:
                return 0x00

        def ctrl_transfer(self, request_type, request, value=0, index=0, data_or_length=None, timeout=None):
            assert (request_type & (1 << 5 | 1)) == (1 << 5 | 1)
            if self.in_type(request_type) is True:
                assert request == 1
            else:
                assert request == 8 | 1
            assert (value & (3 << 8)) == (3 << 8)
            value = value & (~ (3 << 8))
            assert index == 0
            assert timeout == 500

            # get id
            if value == 1 and self.in_type(request_type):
                assert data_or_length == 4
                return id_data()
            # get status outlet
            if (value in (3, 6, 9, 12)) and self.in_type(request_type):
                assert data_or_length == 1
                return self.get_outlet_status((value - 3) / 3)
            # get full schedule outlet
            if (value in (4, 7, 10, 13)) and self.in_type(request_type):
                assert data_or_length == 38
                outlet = (value - 4) / 3
                if outlet == 0:
                    return outlet_schedule_data()
                if outlet == 1:
                    return outlet_schedule_data_vanilla()
                if outlet == 2:
                    return outlet_schedule_data_non_periodic()
                if outlet == 3:
                    return outlet_schedule_data_reset()
            # get current schedule outlet
            if (value in (5, 8, 11, 14)) and self.in_type(request_type):
                assert data_or_length == 3
                outlet = (value - 5) / 3
                if outlet == 0:
                    return outlet_current_schedule_data_ok_off()
                if outlet == 1:
                    return outlet_current_schedule_data_ok_on()
                if outlet == 2:
                    return outlet_current_schedule_data_ok_off_rampup()
                if outlet == 3:
                    return outlet_current_schedule_data_ok_off_done()

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
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override)

       This data is also used to mock the current schedule of outlet 0.
    """
    return bytearray([0x01, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_long_time():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is a lot (0x3002).
       This schedule set the outlet off at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 1.
    """
    return bytearray([0x01, 0x2, 0x30])


@pytest.fixture
def outlet_current_schedule_data_ok_on():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet on at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 2.
    """
    return bytearray([0x01, 0x2, 0x80])


@pytest.fixture
def outlet_current_schedule_data_error_off():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override).
       A timer error occured while executing this schedule (e.g. the power was off for a very long time).

       This data is also used to mock the current schedule of outlet 3.
    """
    return bytearray([0x81, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_rampup():
    """Still waiting to start the schedules (first schedule is the next one).
       Time it will still wait is 2 minutes.
    """
    return bytearray([0x10, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_data_ok_off_done():
    """All schedules were executed.
       This also means that no looping was requested.
    """
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
    assert len(sispy.outlets) == sispy.nr_outlets
    assert isinstance(sispy.outlets[0], Outlet)


def test_outlet_status(sispy):
    outlet = Outlet(0, sispy)
    assert outlet.switched_on is True
    outlet = Outlet(2, sispy)
    assert outlet.switched_on is False


def test_outlets_status(sispy):
    assert sispy.outlets[0].switched_on is True
    assert sispy.outlets[1].switched_on is False
    assert sispy.outlets[2].switched_on is False
    assert sispy.outlets[3].switched_on is True


def test_outlets_schedule(sispy):
    assert sispy.outlets[0].schedule._data == outlet_schedule_data()
    assert sispy.outlets[1].schedule._data == outlet_schedule_data_vanilla()
    assert sispy.outlets[2].schedule._data == outlet_schedule_data_non_periodic()
    assert sispy.outlets[3].schedule._data == outlet_schedule_data_reset()


def test_outlets_current_schedule(sispy):
    assert sispy.outlets[0].current_schedule._data == outlet_current_schedule_data_ok_off()
    assert sispy.outlets[1].current_schedule._data == outlet_current_schedule_data_ok_on()
    assert sispy.outlets[2].current_schedule._data == outlet_current_schedule_data_ok_off_rampup()
    assert sispy.outlets[3].current_schedule._data == outlet_current_schedule_data_ok_off_done()


def _test_outlet_current_schedule(current_schedule, sispy, timing_error=False, switched_it_on=False, minutes_to_next_schedule=2,
                                  next_schedule_nr=1, sequence_rampup=False, sequence_done=False):
    assert current_schedule.timing_error == timing_error
    assert current_schedule.switched_it_on == switched_it_on
    assert current_schedule.minutes_to_next_schedule == minutes_to_next_schedule
    assert current_schedule.next_schedule_nr == next_schedule_nr
    assert current_schedule.sequence_rampup == sequence_rampup
    assert current_schedule.sequence_done == sequence_done


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
    _test_outlet_current_schedule(current_schedule, sispy, sequence_rampup=True, next_schedule_nr=0)


def test_outlet_current_schedule_ok_off_done(sispy, outlet_current_schedule_data_ok_off_done):
    current_schedule = OutletCurrentSchedule(outlet_current_schedule_data_ok_off_done, sispy)
    _test_outlet_current_schedule(current_schedule, sispy, sequence_done=True, minutes_to_next_schedule=0, next_schedule_nr=2)


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
