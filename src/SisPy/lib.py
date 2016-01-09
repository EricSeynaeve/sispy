#! /usr/bin/env python

import struct
import time
import usb


class SisPy(object):
    ID = 1
    OUTLET_STATUS = 3
    OUTLET_SCHEDULES = 4
    OUTLET_CURRENT_SCHEDULE = 5

    def __init__(self):
        self._dev = self._get_device()
        self._id = self._usb_read(SisPy.ID)
        self._outlets = []
        for i in range(4):
            self._outlets.append(Outlet(i, self))

    def _get_device(self):  # pragma: no cover
        devs = usb.core.find(find_all=True, idVendor=0x04b4)
        if devs is None:
            print("No Energenie products found")
            sys.exit(0)
        return devs.next()

    def _usb_read(self, command, outlet_nr=None):
        request_type = 0xa1
        request = 0x01
        if command == SisPy.ID:
            data = self._dev.ctrl_transfer(request_type, request, 0x0301, 0, 4, 500)
            return struct.unpack('<L', data)[0]
        if command == SisPy.OUTLET_STATUS:
            data = self._dev.ctrl_transfer(request_type, request, 0x0303 + outlet_nr * 3, 0, 1, 500)
            return data
        if command == SisPy.OUTLET_CURRENT_SCHEDULE:
            data = self._dev.ctrl_transfer(request_type, request, 0x0305 + outlet_nr * 3, 0, 3, 500)
            return data

    @property
    def id(self):
        return self._id

    @property
    def nr_outlets(self):
        return len(self._outlets)

    @property
    def outlets(self):
        return self._outlets


class Outlet(object):
    def __init__(self, nr, syspi):
        self._nr = nr
        self._syspi = syspi

    @property
    def switched_on(self):
        data = self._syspi._usb_read(SisPy.OUTLET_STATUS, self._nr)
        return data == 0x03

    @property
    def current_schedule(self):
        data = self._syspi._usb_read(SisPy.OUTLET_CURRENT_SCHEDULE, self._nr)
        return OutletCurrentSchedule(data, self._syspi)


class OutletCurrentSchedule(object):
    def __init__(self, data, sispy):
        self._data = data
        self._sispy = sispy

        self._timing_error = (data[0] & 0x80 == 0x80)
        self._next_schedule_nr = (data[0] & 0x7f)
        value = struct.unpack('<H', data[1:])[0]

        if self._next_schedule_nr == 0x10:
            # We're still waiting for the initial delay to finish
            self._next_schedule_nr = 0
            self._sequence_rampup = True
            self._minutes_to_next_schedule = value
        else:
            self._next_schedule_nr = (data[0] & 0x7f)
            self._sequence_rampup = False
            self._minutes_to_next_schedule = (value & 0x3FFF)

        self._switched_it_on = (value & 0x8000 == 0x8000)
        self._sequence_done = (self._minutes_to_next_schedule == 0)

    @property
    def timing_error(self):
        return self._timing_error

    @property
    def sequence_rampup(self):
        return self._sequence_rampup

    @property
    def next_schedule_nr(self):
        return self._next_schedule_nr

    @property
    def switched_it_on(self):
        return self._switched_it_on

    @property
    def minutes_to_next_schedule(self):
        return self._minutes_to_next_schedule

    @property
    def sequence_done(self):
        return self._sequence_done


class ScheduleItem(object):
    def __init__(self, data, schedule, item_nr):
        self._data = data
        self._schedule = schedule
        self._item_nr = item_nr

        self._parse_data(self._data)

    def _parse_data(self, data):
        value = struct.unpack('<H', data)[0]
        self._switch_on = (value & 0x8000 == 0x8000)
        self._minutes_to_next_schedule = (value & 0x3FFF)

    @property
    def switch_on(self):
        return self._switch_on

    @property
    def minutes_to_next_schedule(self):
        return self._minutes_to_next_schedule

    def _start_epoch(self):
        delay_minutes = self._schedule._add_schedule_minutes(self._schedule._entries[:self._item_nr])
        return self._schedule._start_epoch() + delay_minutes * 60

    @property
    def start_time(self):
        return self._schedule._epoch_to_time(self._start_epoch())

    @property
    def end_time(self):
        return self._schedule._epoch_to_time(self._start_epoch() + self._minutes_to_next_schedule * 60)


class Schedule(object):
    def __init__(self, data, sispy):
        self._data = data

        self._sispy = sispy
        self._parse_data(self._data)

    def _parse_data(self, data):
        self._entries = []
        self._periodic = True

        self._epoch_activated = struct.unpack('<L', data[0:4])[0]
        self._rampup_minutes = struct.unpack('<H', data[36:38])[0]

        for i in range(4, 36, 2):
            value = struct.unpack('<H', data[i:i + 2])[0]
            if value == 0x0:
                self._periodic = False
            elif value != 0x3FFF:
                self._entries.append(ScheduleItem(data[i:i + 2], self, (i - 4) / 2))

        if len(self._entries) == 0:
            self._periodic = False
            self._rampup_minutes = 0

    def _epoch_to_time(self, epoch):
        return time.gmtime(epoch)

    def _add_schedule_minutes(self, schedules):
        if len(schedules) > 0:
            return reduce(lambda x, y: x + y, [s._minutes_to_next_schedule for s in schedules])
        else:
            return 0

    @property
    def time_activated(self):
        return self._epoch_to_time(self._epoch_activated)

    @property
    def rampup_minutes(self):
        return self._rampup_minutes

    @property
    def periodic(self):
        return self._periodic

    @property
    def periodicity_minutes(self):
        if self.periodic is True:
            return self._add_schedule_minutes(self._entries)
        else:
            return None

    @property
    def schedule_minutes(self):
        if self.periodic is True:
            return None
        else:
            return self._add_schedule_minutes(self._entries)

    def _start_epoch(self):
        return self._epoch_activated + self._rampup_minutes * 60

    @property
    def start_time(self):
        return self._epoch_to_time(self._start_epoch())

    @property
    def end_time(self):
        if self.periodic is True:
            return time.strptime('2999-12-31 23:59:59 UTC', '%Y-%m-%d %H:%M:%S %Z')
        else:
            return self._epoch_to_time(self._start_epoch() + self.schedule_minutes * 60)

    @property
    def entries(self):
        return self._entries

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
