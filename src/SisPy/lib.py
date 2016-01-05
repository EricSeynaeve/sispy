#! /usr/bin/env python

import struct
import time

time.tzset()


class SisPy(object):
    def __init__(self):
        self._nr_outlets = 4
        self._count_outlets_from_1 = True

    @property
    def nr_outlets(self):
        return self._nr_outlets

    @property
    def count_outlets_from_1(self):
        return self._count_outlets_from_1

    @count_outlets_from_1.setter
    def count_outlets_from_1(self, b):
        self._count_outlets_from_1 = b


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
        if self._sispy.count_outlets_from_1 is True:
            return self._next_schedule_nr + 1
        else:
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
        if self._rampup_minutes == 0x3FFF:
            self._rampup_minutes = 0

        for i in range(4, 36, 2):
            value = struct.unpack('<H', data[i:i + 2])[0]
            if value == 0x0:
                self._periodic = False
            elif value != 0x3FFF:
                self._entries.append(ScheduleItem(data[i:i + 2], self, (i - 4) / 2))

        if len(self._entries) == 0:
            self._periodic = False

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
