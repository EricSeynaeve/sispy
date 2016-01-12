#! /usr/bin/env python

from SisPy.lib import SisPy
from SisPy.lib import Outlet
from SisPy.lib import OutletCurrentScheduleItem
from SisPy.lib import OutletSchedule
from SisPy.lib import OutletScheduleItem

import pytest
import time

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
                    data = outlet_current_schedule_item_data_ok_off()
                if outlet == 1:
                    data = outlet_current_schedule_item_data_ok_on()
                if outlet == 2:
                    data = outlet_current_schedule_item_data_ok_off_rampup()
                if outlet == 3:
                    data = outlet_current_schedule_item_data_ok_off_done()
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
def outlet_current_schedule_item_data_ok_off():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override)

       This data is also used to mock the current schedule of outlet 0.
    """
    return bytearray([0x01, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_item_data_ok_off_long_time():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is a lot (0x3002).
       This schedule set the outlet off at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 1.
    """
    return bytearray([0x01, 0x2, 0x30])


@pytest.fixture
def outlet_current_schedule_item_data_ok_on():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet on at it's start (status now can be different due to override).

       This data is also used to mock the current schedule of outlet 2.
    """
    return bytearray([0x01, 0x2, 0x80])


@pytest.fixture
def outlet_current_schedule_item_data_error_off():
    """Executing the first schedule (second schedule is the next one).
       Time it will still execute is 2 minutes.
       This schedule set the outlet off at it's start (status now can be different due to override).
       A timer error occured while executing this schedule (e.g. the power was off for a very long time).

       This data is also used to mock the current schedule of outlet 3.
    """
    return bytearray([0x81, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_item_data_ok_off_rampup():
    """Still waiting to start the schedules (first schedule is the next one).
       Time it will still wait is 2 minutes.
    """
    return bytearray([0x10, 0x2, 0x0])


@pytest.fixture
def outlet_current_schedule_item_data_ok_off_done():
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
    assert sispy.outlets[0].current_schedule_item._data == outlet_current_schedule_item_data_ok_off()
    assert sispy.outlets[1].current_schedule_item._data == outlet_current_schedule_item_data_ok_on()
    assert sispy.outlets[2].current_schedule_item._data == outlet_current_schedule_item_data_ok_off_rampup()
    assert sispy.outlets[3].current_schedule_item._data == outlet_current_schedule_item_data_ok_off_done()


# test outlet current schedule item class

def _test_outlet_current_schedule(current_schedule, timing_error=False, switched_it_on=False, minutes_to_next_schedule_item=2,
                                  next_schedule_nr=1, sequence_rampup=False, sequence_done=False):
    assert current_schedule.timing_error == timing_error
    assert current_schedule.switched_it_on == switched_it_on
    assert current_schedule.minutes_to_next_schedule_item == minutes_to_next_schedule_item
    assert current_schedule.next_schedule_nr == next_schedule_nr
    assert current_schedule.sequence_rampup == sequence_rampup
    assert current_schedule.sequence_done == sequence_done


def test_outlet_current_schedule_item_ok_off(outlet_current_schedule_item_data_ok_off):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_ok_off)
    _test_outlet_current_schedule(current_schedule)


def test_outlet_current_schedule_item_ok_off_long_time(outlet_current_schedule_item_data_ok_off_long_time):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_ok_off_long_time)
    _test_outlet_current_schedule(current_schedule, minutes_to_next_schedule_item=12290)


def test_outlet_current_schedule_item_error_off(outlet_current_schedule_item_data_error_off):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_error_off)
    _test_outlet_current_schedule(current_schedule, timing_error=True)


def test_outlet_current_schedule_item_ok_on(outlet_current_schedule_item_data_ok_on):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_ok_on)
    _test_outlet_current_schedule(current_schedule, switched_it_on=True)


def test_outlet_current_schedule_item_ok_off_rampup(outlet_current_schedule_item_data_ok_off_rampup):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_ok_off_rampup)
    _test_outlet_current_schedule(current_schedule, sequence_rampup=True, next_schedule_nr=0)


def test_outlet_current_schedule_item_ok_off_done(outlet_current_schedule_item_data_ok_off_done):
    current_schedule = OutletCurrentScheduleItem(outlet_current_schedule_item_data_ok_off_done)
    _test_outlet_current_schedule(current_schedule, sequence_done=True, minutes_to_next_schedule_item=0, next_schedule_nr=2)


# test outlet schedule class

def test_outlet_schedule(outlet_schedule_data):
    schedule = OutletSchedule(outlet_schedule_data)

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
    assert entry1.minutes_to_next_schedule_item == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule_item == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_non_periodic(outlet_schedule_data_non_periodic):
    schedule = OutletSchedule(outlet_schedule_data_non_periodic)

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
    assert entry1.minutes_to_next_schedule_item == 3
    assert entry1.start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry1.end_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    entry2 = schedule.entries[1]
    assert entry2.switch_on is False
    assert entry2.minutes_to_next_schedule_item == 2
    assert entry2.start_time == time.strptime('2016-01-05 17:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert entry2.end_time == time.strptime('2016-01-05 17:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')


def test_outlet_schedule_reset(outlet_schedule_data_reset):
    schedule = OutletSchedule(outlet_schedule_data_reset)

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


def test_outlet_schedule_vanilla(outlet_schedule_data_vanilla):
    schedule = OutletSchedule(outlet_schedule_data_vanilla)

    assert schedule.time_activated == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 0
    assert schedule.start_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.periodic is False
    assert schedule.periodicity_minutes is None
    assert schedule.schedule_minutes == 0
    assert schedule.end_time == time.strptime('1970-01-01 00:00:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert len(schedule.entries) == 0


def test_outlet_schedule_change_first_entry(outlet_schedule_data):
    schedule = OutletSchedule(outlet_schedule_data)

    schedule_entry1 = schedule.entries[0]

    schedule_entry1.start_time = time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.time_activated == time.strptime('2016-01-05 17:12:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 4 * 60 + 3
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_item == 3
    assert schedule_entry1.end_time == time.strptime('2016-01-05 21:18:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[1].start_time == time.strptime('2016-01-05 21:18:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(TypeError):
        schedule_entry1.start_time = 'abc'
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(ValueError):
        schedule_entry1.start_time = time.strptime('2016-01-05 17:12:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1._construct_data() == bytearray([0x3, 0x80])

    schedule_entry1.minutes_to_next_schedule_item = 8 * 60
    assert schedule.time_activated == time.strptime('2016-01-05 17:12:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.rampup_minutes == 4 * 60 + 3
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_item == 8 * 60
    assert schedule_entry1.end_time == time.strptime('2016-01-06 05:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[1].start_time == time.strptime('2016-01-06 05:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1._construct_data() == bytearray([0xE0, 0x81])

    with pytest.raises(TypeError):
        schedule_entry1.minutes_to_next_schedule_item = 'abc'
    assert schedule_entry1.minutes_to_next_schedule_item == 8 * 60
    with pytest.raises(ValueError):
        schedule_entry1.minutes_to_next_schedule_item = -1
    assert schedule_entry1.minutes_to_next_schedule_item == 8 * 60
    with pytest.raises(ValueError):
        schedule_entry1.minutes_to_next_schedule_item = 0xFFFF
    assert schedule_entry1.minutes_to_next_schedule_item == 8 * 60

    schedule_entry1.end_time = time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.start_time == time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry1.minutes_to_next_schedule_item == 10
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


def test_outlet_schedule_change_second(outlet_schedule_data):
    schedule = OutletSchedule(outlet_schedule_data)

    schedule_entry2 = schedule.entries[1]

    schedule_entry2.start_time = time.strptime('2016-01-05 21:15:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.time_activated == time.strptime('2016-01-05 17:10:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[0].start_time == time.strptime('2016-01-05 17:11:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule.entries[0].minutes_to_next_schedule_item == 4 * 60 + 3
    assert schedule.entries[0].end_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_item == 2
    assert schedule_entry2.end_time == time.strptime('2016-01-05 21:16:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    with pytest.raises(ValueError):
        schedule_entry2.start_time = time.strptime('2016-01-05 17:11:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    schedule_entry2.minutes_to_next_schedule_item = 8 * 60
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_item == 8 * 60
    assert schedule_entry2.end_time == time.strptime('2016-01-06 05:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

    schedule_entry2.end_time = time.strptime('2016-01-05 21:25:15 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.start_time == time.strptime('2016-01-05 21:14:35 UTC', '%Y-%m-%d %H:%M:%S %Z')
    assert schedule_entry2.minutes_to_next_schedule_item == 10
    assert schedule_entry2.end_time == time.strptime('2016-01-05 21:24:35 UTC', '%Y-%m-%d %H:%M:%S %Z')

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
