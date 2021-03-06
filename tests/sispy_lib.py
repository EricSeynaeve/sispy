#! /usr/bin/env python

# Test script for SisPy.lib.
# Copyright (C) 2016  Eric Seynaeve
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from SisPy.lib import _min2human
from SisPy.lib import SisPy
from SisPy.lib import Outlet
from SisPy.lib import OutletCurrentScheduleEntry
from SisPy.lib import OutletSchedule
from SisPy.lib import OutletScheduleEntry

import pytest
import time
import calendar

# test data was obtained in CET
time.altzone = -7200
time.timezone = -3600
time.daylight = 0


#####
# some mock objects to be able to inject test data
#####

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

        def mock_read_data(self, report_nr, data_or_length):
            data = None
            # get id
            if report_nr == 1:
                assert data_or_length == 5
                data = id_data()
            # get status outlet
            if (report_nr in (3, 6, 9, 12)):
                assert data_or_length == 2
                data = [self.get_outlet_status((report_nr - 3) / 3)]
            # get full schedule outlet
            if (report_nr in (4, 7, 10, 13)):
                assert data_or_length == 39
                outlet = (report_nr - 4) / 3
                if outlet == 0:
                    data = outlet_schedule_data()
                if outlet == 1:
                    data = outlet_schedule_data_vanilla()
                if outlet == 2:
                    data = outlet_schedule_data_non_periodic()
                if outlet == 3:
                    data = outlet_schedule_data_reset()
            # get current schedule outlet
            if (report_nr in (5, 8, 11, 14)):
                assert data_or_length == 4
                outlet = (report_nr - 5) / 3
                if outlet == 0:
                    data = outlet_current_schedule_entry_data_ok_off()
                if outlet == 1:
                    data = outlet_current_schedule_entry_data_ok_on()
                if outlet == 2:
                    data = outlet_current_schedule_entry_data_ok_off_rampup()
                if outlet == 3:
                    data = outlet_current_schedule_entry_data_ok_off_done()
            # the report number is added as first byte
            data.insert(0, report_nr)
            return data

        def ctrl_transfer(self, request_type, request, value=0, index=0, data_or_length=None, timeout=None):
            assert (request_type & (1 << 5 | 1)) == (1 << 5 | 1)
            if self.in_type(request_type) is True:
                assert request == 1
            else:
                assert request == 8 | 1
            assert (value & (3 << 8)) == (3 << 8)
            assert index == 0
            assert timeout == 500

            self.send_meta = None
            self.send_data = None

            if self.in_type(request_type) is True:
                report_nr = value & (~ (3 << 8))
                return self.mock_read_data(report_nr, data_or_length)
            else:
                self.send_meta = bytearray([request_type, request, value & 0xFF, int(value / 0xFF), index])
                self.send_data = data_or_length
                return len(data_or_length)

    return MockDevice()


@pytest.fixture
def sispy(device):
    class MockSisPy(SisPy):
        def __init__(self):
            SisPy.__init__(self)

        def _get_device(self):
            return device

    return MockSisPy()


####
# data that we can use for injection
####

@pytest.fixture
def outlet_current_schedule_entry_data_ok_off():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override)

       This data is also used to mock the current schedule of outlet 0.
    """
    return bytearray([0x01, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_entry_data_ok_off_long_time():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is a lot (0x3002).
       This schedule set the outlet off at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 1.
    """
    return bytearray([0x01, 0x2, 0x30])


@pytest.fixture
def outlet_current_schedule_entry_data_ok_on():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet on at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 2.
    """
    return bytearray([0x01, 0x2, 0x80])


@pytest.fixture
def outlet_current_schedule_entry_data_error_off():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override).
       A timer error occured while executing this schedule (e.g. the power was off for a very long time).

       This data is also used to mock the current schedule of outlet 3.
    """
    return bytearray([0x81, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_entry_data_ok_off_rampup():
    """Still waiting to start the schedules (first schedule is the next one).
       Time it will still wait is 2 minutes.
    """
    return bytearray([0x10, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_entry_data_ok_off_done():
    """All schedules were executed.
       This also means that no looping was requested.
    """
    return bytearray([0x02, 0x0, 0x0])


@pytest.fixture
def outlet_schedule_data():
    """Time activated is 2016-01-05 17:10:35 UTC
       Rampup time is 1 minute.
       2 schedule entries:
         - switch on and wait 3 minutes.
         - switch off and wait 2 minutes.
       Repeat this periodically.
    """
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0x3, 0x80, 0x2, 0x0, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_non_periodic():
    """Time activated is 2016-01-05 17:10:35 UTC
       Rampup time is 1 minute.
       2 schedule entries:
         - switch on and wait 3 minutes.
         - switch off and wait 2 minutes.
       Do this only once.
    """
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0x3, 0x80, 0x2, 0x0, 0x0, 0x0, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_reset():
    """Time activated is 2016-01-05 17:10:35 UTC
       Rampup time is 1 minute.
       All schedules are reset.
    """
    return bytearray([0xb, 0xf9, 0x8b, 0x56, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0x1, 0x0])


@pytest.fixture
def outlet_schedule_data_vanilla():
    """Entry as it should be after factory reset.
    """
    return bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])


def id_data():
    """Power outlet id 0x04030201"""
    return bytearray([0x1, 0x2, 0x3, 0x4])


####
# Actual test code
####

def test_mock(sispy):
    assert isinstance(sispy, SisPy)


# Test power switch

def test_property_defaults(sispy):
    assert sispy.id == 67305985
    assert sispy.nr_outlets == 4
    assert len(sispy.outlets) == sispy.nr_outlets
    assert isinstance(sispy.outlets[0], Outlet)


# Test outlet status

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


def test_outlets_status_change(sispy):
    sispy.outlets[0].switched_on = True
    assert sispy._dev.send_meta == bytearray([0x21, 0x09, 0x03, 0x03, 0x00])
    assert sispy._dev.send_data == bytearray([0x03, 0x01])

    sispy.outlets[0].switched_on = False
    assert sispy._dev.send_meta == bytearray([0x21, 0x09, 0x03, 0x03, 0x00])
    assert sispy._dev.send_data == bytearray([0x03, 0x00])

    sispy.outlets[1].switched_on = True
    assert sispy._dev.send_meta == bytearray([0x21, 0x09, 0x06, 0x03, 0x00])
    assert sispy._dev.send_data == bytearray([0x06, 0x01])

    with pytest.raises(TypeError):
        sispy.outlets[0].switched_on = 1


# Test outlet schedule

def test_outlets_schedule(sispy):
    assert sispy.outlets[0].schedule._data == outlet_schedule_data()
    assert sispy.outlets[1].schedule._data == outlet_schedule_data_vanilla()
    assert sispy.outlets[2].schedule._data == outlet_schedule_data_non_periodic()
    assert sispy.outlets[3].schedule._data == outlet_schedule_data_reset()


def test_outlets_current_schedule(sispy):
    assert sispy.outlets[0].current_schedule_entry._data == outlet_current_schedule_entry_data_ok_off()
    assert sispy.outlets[1].current_schedule_entry._data == outlet_current_schedule_entry_data_ok_on()
    assert sispy.outlets[2].current_schedule_entry._data == outlet_current_schedule_entry_data_ok_off_rampup()
    assert sispy.outlets[3].current_schedule_entry._data == outlet_current_schedule_entry_data_ok_off_done()


# test outlet current schedule entry class

def _test_outlet_current_schedule(current_schedule, timing_error=False, switched_it_on=False, minutes_to_next_schedule_entry=2,
                                  current_schedule_nr=1, sequence_rampup=False, sequence_done=False):
    assert current_schedule.timing_error == timing_error
    assert current_schedule.switched_it_on == switched_it_on
    assert current_schedule.minutes_to_next_schedule_entry == minutes_to_next_schedule_entry
    assert current_schedule.current_schedule_nr == current_schedule_nr
    assert current_schedule.sequence_rampup == sequence_rampup
    assert current_schedule.sequence_done == sequence_done


def test_outlet_current_schedule_entry_ok_off(outlet_current_schedule_entry_data_ok_off):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_ok_off)
    _test_outlet_current_schedule(current_schedule)


def test_outlet_current_schedule_entry_ok_off_long_time(outlet_current_schedule_entry_data_ok_off_long_time):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_ok_off_long_time)
    _test_outlet_current_schedule(current_schedule, minutes_to_next_schedule_entry=12290)


def test_outlet_current_schedule_entry_error_off(outlet_current_schedule_entry_data_error_off):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_error_off)
    _test_outlet_current_schedule(current_schedule, timing_error=True)


def test_outlet_current_schedule_entry_ok_on(outlet_current_schedule_entry_data_ok_on):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_ok_on)
    _test_outlet_current_schedule(current_schedule, switched_it_on=True)


def test_outlet_current_schedule_entry_ok_off_rampup(outlet_current_schedule_entry_data_ok_off_rampup):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_ok_off_rampup)
    _test_outlet_current_schedule(current_schedule, sequence_rampup=True, current_schedule_nr=None)


def test_outlet_current_schedule_entry_ok_off_done(outlet_current_schedule_entry_data_ok_off_done):
    current_schedule = OutletCurrentScheduleEntry(outlet_current_schedule_entry_data_ok_off_done)
    _test_outlet_current_schedule(current_schedule, sequence_done=True, minutes_to_next_schedule_entry=0, current_schedule_nr=2)


# test outlet schedule class

def test_min2human():
    assert _min2human(3) == "3m"
    assert _min2human(30) == "30m"
    assert _min2human(60) == "1h0m"
    assert _min2human(90) == "1h30m"
    assert _min2human(601) == "10h1m"
    assert _min2human(24 * 60) == "1d0h0m"
    assert _min2human(25 * 60 + 5) == "1d1h5m"


def test_outlet_schedule(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

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
    assert entry1.minutes_to_next_schedule_entry == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule_entry == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    assert str(schedule) == "Time activated: 2016-01-05 17:10:35 UTC, rampup time: 1m, periodic: True, periodicity: 5m min., Entry 0: [switch on: True, start time: 2016-01-05 17:11:35 UTC, time to next schedule entry: 3m, end time: 2016-01-05 17:14:35 UTC], Entry 1: [switch on: False, start time: 2016-01-05 17:14:35 UTC, time to next schedule entry: 2m, end time: 2016-01-05 17:16:35 UTC]"


def test_outlet_schedule_change_periodicity(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    assert schedule.periodic is True
    assert schedule.periodicity_minutes == 5
    assert schedule.schedule_minutes is None

    schedule.periodic = False
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 5

    with pytest.raises(TypeError):
        schedule.periodic = 1


def test_outlet_schedule_non_periodic(outlet_schedule_data_non_periodic, sispy):
    schedule = OutletSchedule(outlet_schedule_data_non_periodic, sispy)

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
    assert entry1.minutes_to_next_schedule_entry == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule_entry == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    assert str(schedule) == "Time activated: 2016-01-05 17:10:35 UTC, rampup time: 1m, periodic: False, total time: 5m min., end time: 2016-01-05 17:16:35 UTC, Entry 0: [switch on: True, start time: 2016-01-05 17:11:35 UTC, time to next schedule entry: 3m, end time: 2016-01-05 17:14:35 UTC], Entry 1: [switch on: False, start time: 2016-01-05 17:14:35 UTC, time to next schedule entry: 2m, end time: 2016-01-05 17:16:35 UTC]"


def test_outlet_schedule_reset(outlet_schedule_data_reset, sispy):
    schedule = OutletSchedule(outlet_schedule_data_reset, sispy)

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

    assert str(schedule) == "Time activated: 2016-01-05 17:10:35 UTC, rampup time: 0m, periodic: False, total time: 0m min., end time: 2016-01-05 17:10:35 UTC"


def test_outlet_schedule_vanilla(outlet_schedule_data_vanilla, sispy):
    schedule = OutletSchedule(outlet_schedule_data_vanilla, sispy)

    assert schedule.time_activated == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 0
    assert schedule.start_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 0
    assert schedule.end_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 0

    assert str(schedule) == "Time activated: 1970-01-01 00:00:00 UTC, rampup time: 0m, periodic: False, total time: 0m min., end time: 1970-01-01 00:00:00 UTC"


def test_outlet_schedule_change_first_entry(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    schedule_entry1 = schedule.entries[0]

    schedule_entry1.start_time = time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.time_activated == time.strptime('2016-01-05 17:12:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 4 * 60 + 3
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_entry == 3
    assert schedule_entry1.end_time == time.strptime('2016-01-05 21:18:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[1].start_time == time.strptime('2016-01-05 21:18:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(TypeError):
        schedule_entry1.start_time = 'abc'
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1._construct_data() == bytearray([0x3, 0x80])

    schedule_entry1.minutes_to_next_schedule_entry = 8 * 60
    assert schedule.time_activated == time.strptime('2016-01-05 17:12:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 4 * 60 + 3
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_entry == 8 * 60
    assert schedule_entry1.end_time == time.strptime('2016-01-06 05:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[1].start_time == time.strptime('2016-01-06 05:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1._construct_data() == bytearray([0xE0, 0x81])

    with pytest.raises(TypeError):
        schedule_entry1.minutes_to_next_schedule_entry = 'abc'
    assert schedule_entry1.minutes_to_next_schedule_entry == 8 * 60
    with pytest.raises(ValueError):
        schedule_entry1.minutes_to_next_schedule_entry = -1
    assert schedule_entry1.minutes_to_next_schedule_entry == 8 * 60
    with pytest.raises(ValueError):
        schedule_entry1.minutes_to_next_schedule_entry = 0xFFFF
    assert schedule_entry1.minutes_to_next_schedule_entry == 8 * 60

    schedule_entry1.end_time = time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_entry == 10
    assert schedule_entry1.end_time == time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[1].start_time == time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1._construct_data() == bytearray([0x0A, 0x80])
    with pytest.raises(TypeError):
        schedule_entry1.end_time = 'abc'
    assert schedule_entry1.end_time == time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(ValueError):
        schedule_entry1.end_time = time.strptime('2016-01-05 21:15:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.end_time == time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')

    assert schedule_entry1.switch_on is True
    schedule_entry1.switch_on = False
    assert schedule_entry1.switch_on is False
    assert schedule_entry1._construct_data() == bytearray([0x0A, 0x00])
    with pytest.raises(TypeError):
        schedule_entry1.switch_on = 1
    assert schedule_entry1.switch_on is False


def test_outlet_schedule_change_first_entry_start_time(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    schedule_entry1 = schedule.entries[0]

    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    # error should be raised if we assign a time before the last activation time
    with pytest.raises(ValueError):
        schedule_entry1.start_time = time.strptime('2016-01-05 17:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')

    # but not if it's between the last activation time and the start time
    schedule_entry1.start_time = time.strptime('2016-01-05 17:12:30 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_change_second(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    schedule_entry2 = schedule.entries[1]

    schedule_entry2.start_time = time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[0].start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[0].minutes_to_next_schedule_entry == 4 * 60 + 3
    assert schedule.entries[0].end_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_entry == 2
    assert schedule_entry2.end_time == time.strptime('2016-01-05 21:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(ValueError):
        schedule_entry2.start_time = time.strptime('2016-01-05 17:11:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    schedule_entry2.minutes_to_next_schedule_entry = 8 * 60
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_entry == 8 * 60
    assert schedule_entry2.end_time == time.strptime('2016-01-06 05:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    schedule_entry2.end_time = time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_entry == 10
    assert schedule_entry2.end_time == time.strptime('2016-01-05 21:24:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_entry_add(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    schedule.add_entry()
    assert len(schedule.entries) == 3

    schedule_entry2 = schedule.entries[1]
    schedule_entry3 = schedule.entries[2]
    assert schedule_entry3.switch_on is False
    assert schedule_entry3.start_time == schedule_entry2.end_time
    assert schedule_entry3.minutes_to_next_schedule_entry == 0
    assert schedule_entry3.end_time == schedule_entry2.end_time


def test_outlet_schedule_entry_remove(outlet_schedule_data, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)

    schedule.remove_entry()
    assert len(schedule.entries) == 1

    # make sure we removed the correct one ;-)
    entry1 = schedule.entries[0]
    assert entry1.switch_on is True
    assert entry1.minutes_to_next_schedule_entry == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_data(outlet_schedule_data, outlet_schedule_data_reset, sispy):
    schedule = OutletSchedule(outlet_schedule_data, sispy)
    begin_time = schedule.time_activated

    assert schedule._construct_data(begin_time) == outlet_schedule_data

    outlet_schedule_data[8] = 0
    outlet_schedule_data[9] = 0
    schedule.periodic = False
    assert schedule._construct_data(begin_time) == outlet_schedule_data

    schedule.reset()
    # when writing, the rampup time is set to 0 is no entries are found
    outlet_schedule_data_reset[36] = 0
    outlet_schedule_data_reset[37] = 0
    assert schedule._construct_data(begin_time) == outlet_schedule_data_reset


def test_outlet_schedule_apply_activated_change(sispy):
    schedule = sispy.outlets[0].schedule

    begin_time = schedule.time_activated
    rampup_minutes = schedule.rampup_minutes

    schedule._get_current_time = lambda: begin_time

    schedule.apply()
    assert schedule.time_activated == begin_time
    assert schedule.rampup_minutes == rampup_minutes

    new_begin_time = time.gmtime(calendar.timegm(begin_time) - 5 * 3600)
    schedule._get_current_time = lambda: new_begin_time
    new_rampup_minutes = rampup_minutes + 5 * 60

    schedule.apply()
    assert schedule.time_activated == new_begin_time
    assert schedule.rampup_minutes == new_rampup_minutes


def test_outlet_schedule_apply_data(sispy, outlet_schedule_data):
    schedule = sispy.outlets[0].schedule

    begin_time = schedule.time_activated

    schedule._get_current_time = lambda: begin_time

    schedule.apply()
    assert sispy._dev.send_meta == bytearray([0x21, 0x09, 0x04, 0x03, 0x00])
    assert sispy._dev.send_data == bytearray([0x04]) + outlet_schedule_data


# vim: set ai tabstop=4 shiftwidth=4 expandtab :
