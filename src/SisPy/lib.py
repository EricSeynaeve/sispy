#! /usr/bin/env python

import struct


class SisPy(object):
    def __init__(self):
        self._nr_outlets = 4
        self._count_outlets_from_1 = True
        self._time_in_GMT = True

    @property
    def nr_outlets(self):
        return self._nr_outlets

    @property
    def count_outlets_from_1(self):
        return self._count_outlets_from_1

    @count_outlets_from_1.setter
    def count_outlets_from_1(self, b):
        self._count_outlets_from_1 = b

    @property
    def time_in_GMT(self):
        return self._time_in_GMT

    @time_in_GMT.setter
    def time_in_GMT(self, b):
        self._time_in_GMT = b


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
            self._time_to_next_schedule = value
        else:
            self._next_schedule_nr = (data[0] & 0x7f)
            self._sequence_rampup = False
            self._time_to_next_schedule = (value & 0x3FFF)

        self._switched_it_on = (value & 0x8000 == 0x8000)
        self._sequence_done = (self._time_to_next_schedule == 0)

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
    def time_to_next_schedule(self):
        return self._time_to_next_schedule

    @property
    def sequence_done(self):
        return self._sequence_done

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
