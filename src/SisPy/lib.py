#! /usr/bin/env python
"""Library functions to work with the Energenie EG-PMS series of programmable power switches.

   At the moment, only tested on an EG-PMS2.
"""

# Python library for controlling the Energenie power switch.
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

import struct
import time
import calendar
import usb


def _min2human(minutes):
    days = int(minutes / (60 * 24))
    minutes = minutes - days * 60 * 24
    hours = int(minutes / 60)
    minutes = minutes - hours * 60

    string = str(minutes) + "m"
    if hours > 0 or days > 0:
        string = str(hours) + "h" + string
    if days > 0:
        string = str(days) + "d" + string
    return string


class SisPy(object):
    """Represent the power supply.

       Currently, on the first USB power supply is detected.
    """
    _ID = 1
    _OUTLET_STATUS = 3
    _OUTLET_SCHEDULE = 4
    _OUTLET_CURRENT_SCHEDULE_ENTRY = 5

    def __init__(self):
        self._dev = self._get_device()
        self._id = self._usb_read(SisPy._ID)
        self._outlets = []
        for i in range(4):
            self._outlets.append(Outlet(i, self))

    def _get_device(self):  # pragma: no cover
        devs = usb.core.find(find_all=True, idVendor=0x04b4)
        if devs is None:
            print("No Energenie products found")
            sys.exit(0)
        return next(devs)

    def _usb_read(self, command, outlet_nr=None):
        request_type = 0xa1
        request = 0x01
        report_nr = None
        if command == SisPy._ID:
            report_nr = 0x01
            data = self._dev.ctrl_transfer(request_type, request, 0x0300 + report_nr, 0, 4 + 1, 500)
        if command == SisPy._OUTLET_STATUS:
            report_nr = 0x03 + outlet_nr * 3
            data = self._dev.ctrl_transfer(request_type, request, 0x0300 + report_nr, 0, 1 + 1, 500)
        if command == SisPy._OUTLET_SCHEDULE:
            report_nr = 0x04 + outlet_nr * 3
            data = self._dev.ctrl_transfer(request_type, request, 0x0300 + report_nr, 0, 38 + 1, 500)
        if command == SisPy._OUTLET_CURRENT_SCHEDULE_ENTRY:
            report_nr = 0x05 + outlet_nr * 3
            data = self._dev.ctrl_transfer(request_type, request, 0x0300 + report_nr, 0, 3 + 1, 500)
        assert data[0] == report_nr
        return data[1:]

    def _usb_write(self, command, outlet_nr, data):
        request_type = 0x21
        request = 0x09
        report_nr = None
        if command == SisPy._OUTLET_STATUS:
            assert len(data) == 1
            report_nr = 0x03 + outlet_nr * 3
        if command == SisPy._OUTLET_SCHEDULE:
            assert len(data) == 38
            report_nr = 0x04 + outlet_nr * 3
        data.insert(0, report_nr)
        bytes_written = self._dev.ctrl_transfer(request_type, request, 0x0300 + report_nr, 0, data, 500)
        assert bytes_written == len(data)
        return bytes_written - 1

    @property
    def id(self):
        """The internal identifier of the power strip.

           A (large) integer.
        """
        data = self._usb_read(SisPy._ID)
        self._id = struct.unpack('<L', data)[0]
        return self._id

    @property
    def nr_outlets(self):
        """The number of programmable outlets.
           It's possible that the power strip containes more outlets, but these are then non-programmable.

           An integer.
        """
        return len(self._outlets)

    @property
    def outlets(self):
        """List of Outlet objects that repesent the state of each programmable outlet.
        """
        return self._outlets


class Outlet(object):
    """Represent the state of single outlet.

       With this classe, you can check where the outlet is in executing a hardware schedule,
       examine or set the mentioned hardware schedule, check the power state of the outlet.
    """
    def __init__(self, nr, sispy):
        self._nr = nr
        self._sispy = sispy
        self._schedule = None

    @property
    def switched_on(self):
        """Read or assign the status of the outlet.

           If read, indicate whether the outlet is switched on. True if the outlet is switched on. False otherwise.

           If assigned, set the outlet on (True) or off (False).
        """
        data = self._sispy._usb_read(SisPy._OUTLET_STATUS, self._nr)
        return data[0] == 0x03

    @switched_on.setter
    def switched_on(self, value):
        if value is True:
            self._sispy._usb_write(SisPy._OUTLET_STATUS, self._nr, bytearray([1]))
            return
        if value is False:
            self._sispy._usb_write(SisPy._OUTLET_STATUS, self._nr, bytearray([0]))
            return
        raise TypeError("Can't assign a " + value.__class__.__name__ + " to a boolean property.")

    @property
    def schedule(self):
        """Represent the hardware schedule of the outlet.
        """
        if self._schedule is None:
            data = self._sispy._usb_read(SisPy._OUTLET_SCHEDULE, self._nr)
            self._schedule = OutletSchedule(data, self._sispy, self._nr)
        return self._schedule

    @property
    def current_schedule_entry(self):
        """Represent the current schedule entry that's being executed.
        """
        data = self._sispy._usb_read(SisPy._OUTLET_CURRENT_SCHEDULE_ENTRY, self._nr)
        return OutletCurrentScheduleEntry(data)


class OutletCurrentScheduleEntry(object):
    """Indicates where the outlet currently is in the execution of the schedule.
       This is continuously updated by the outlet. Also, this information is only informational, nothing can be set.

       It will indicate whether the outlet was switched on at the beginning of the current outlet schedule entry,
       how long until the next outlet schedule entry, where we are in the schedule list and whether a time error status is detected.

       The latter can happen when the power strip is set without current for a long time.
    """
    def __init__(self, data):
        self._data = data

        self._timing_error = (data[0] & 0x80 == 0x80)
        self._current_schedule_nr = (data[0] & 0x7f)
        value = struct.unpack('<H', data[1:])[0]

        if self._current_schedule_nr == 0x10:
            # We're still waiting for the initial delay to finish
            self._current_schedule_nr = None
            self._sequence_rampup = True
            self._minutes_to_next_schedule_entry = value
        else:
            self._current_schedule_nr = (data[0] & 0x7f)
            self._sequence_rampup = False
            self._minutes_to_next_schedule_entry = (value & 0x3FFF)

        self._switched_it_on = (value & 0x8000 == 0x8000)
        self._sequence_done = (self._minutes_to_next_schedule_entry == 0)

    @property
    def timing_error(self):
        """Indicate that the power strip is not sure about the current time anymore. This can happen when it's set without current for a long time.

           True for a detected error, False otherwise.
        """
        return self._timing_error

    @property
    def sequence_rampup(self):
        """Indicate if the outlet is still in rampup state.

           True if this is the case, False otherwise.
        """
        return self._sequence_rampup

    @property
    def current_schedule_nr(self):
        """Schedule number of the current schedule in the list to execute.

           An integer from 0 onwards.
           None if we're still in rampup state.
        """
        return self._current_schedule_nr

    @property
    def switched_it_on(self):
        """Indicate whether the outlet was switched on at the start of the schedule or not.
           The current status of the outlet can be different due to other influences.

           True if the outlet was switched on.
        """
        return self._switched_it_on

    @property
    def minutes_to_next_schedule_entry(self):
        """Number of minutes still to wait before starting the next schedule entry.
           This is updated by the power strip itself.

           An integer with the number of minutes.
        """
        return self._minutes_to_next_schedule_entry

    @property
    def sequence_done(self):
        """Indicate whether the sequence finished executing.
           This can only happen for non-periodic sequences.

           True if the sequence is finished.
        """
        return self._sequence_done


class OutletScheduleEntry(object):
    """Represents an entry in the schedule by it's status at the start and the time before the next entry is executed.

       This can be read and manipulated in different ways:
       - (start time, wait time in minutes)
       - (end time, wait time in minutes)
       - (start time, end time)

       With a manipulation in one entry, the remaining will be set accordingly.
       Manipulating the start time will also change the end time.
       Manipulating the wait time will also change the end time.
       Manipulating the end time will also adjust the wait time.

       E.g.
       - if the start time is 09:30 and the wait time is set at 15 minutes, the end time will be 09:45.
       - if the start time is 09:30 and the end time is set at 09:50, the wait time will be 20 minutes.
       - if the wait time is 15 minutes and the start time is set at 09:15, the end time will be 09:30.

       The start time will always take into account the wait times if the previous entries (if any).
    """
    def __init__(self, data, schedule, entry_nr):
        self._data = data
        self._schedule = schedule
        self._entry_nr = entry_nr

        self._parse_data(self._data)

    def _parse_data(self, data):
        value = struct.unpack('<H', data)[0]
        self._switch_on = (value & 0x8000 == 0x8000)
        self._minutes_to_next_schedule_entry = (value & 0x3FFF)

    def _construct_data(self):
        value = self._minutes_to_next_schedule_entry
        if self._switch_on is True:
            value |= 0x8000
        data = bytearray([0, 0])
        struct.pack_into('<H', data, 0, value)
        return data

    @property
    def switch_on(self):
        """True when the outlet was set on at the start of this schedule entry. False other wise.

           Beware, the current status could be different due to other manipulations after that time.
        """
        return self._switch_on

    @switch_on.setter
    def switch_on(self, new_setting):
        if isinstance(new_setting, bool):
            self._switch_on = new_setting
        else:
            raise TypeError("Can't set the switch status in schedule entry with a " + new_setting.__class__.__name__)

    @property
    def minutes_to_next_schedule_entry(self):
        """The set wait time in minutes after this schedule entry was started to start the next one.

           When set, this will adjust the end time of this schedule.

           This is always an int indicating the number of minutes.
        """
        return self._minutes_to_next_schedule_entry

    @minutes_to_next_schedule_entry.setter
    def minutes_to_next_schedule_entry(self, new_minutes):
        if isinstance(new_minutes, int):
            if new_minutes < 0:
                raise ValueError("Can't set a number of minutes < 0")
            if new_minutes > 0x3FFF:
                raise ValueError("Number of minutes to set too big (> 16383 (~ 273+ hours or ~ 11+ days))")

            self._minutes_to_next_schedule_entry = new_minutes
        else:
            raise TypeError("Can't use a " + new_minutes.__class__.__name__ + " to set the number of minutes.")

    def _start_epoch(self):
        delay_minutes = self._schedule._add_schedule_minutes(self._schedule._entries[:self._entry_nr])
        return self._schedule._start_epoch() + delay_minutes * 60

    @property
    def start_time(self):
        """Start time of this schedule entry.

           If set, this will automatically also adjust the end_time.

           This is a time UTC tuple.
        """
        return self._schedule._epoch_to_time(self._start_epoch())

    @start_time.setter
    def start_time(self, new_time):
        """Set the new start time. This also shifts the end time with as much time.
        """
        if isinstance(new_time, time.struct_time):
            new_start_epoch = calendar.timegm(new_time)
        else:
            raise TypeError("Can't us a " + new_time.__class__.__name__ + " type to set the time.")

        if self._entry_nr == 0:
            if new_start_epoch < self._schedule._epoch_activated:
                raise ValueError("Start time of first schedule entry needs to be after the start time of the outlet schedule.")
            self._schedule._rampup_minutes = int((new_start_epoch - self._schedule._start_epoch()) / 60)
            # ensure there is always a whole number of minutes between the times.
            self._schedule._epoch_activated = new_start_epoch - self._schedule._rampup_minutes * 60
        else:
            prev_entry = self._schedule.entries[self._entry_nr - 1]
            if new_start_epoch < prev_entry._start_epoch():
                raise ValueError("Start time of a schedule entry needs to be after the start time of the previous schedule entry.")
            prev_entry._minutes_to_next_schedule_entry = int((new_start_epoch - prev_entry._start_epoch()) / 60)

    @property
    def end_time(self):
        """When this schedule entry will end and the next one will start.

           On setting, you can't set it to a value smaller than the start time.
           On setting, the wait time is adjusted automatically.

           This is a time UTC tuple.
        """
        return self._schedule._epoch_to_time(self._start_epoch() + self._minutes_to_next_schedule_entry * 60)

    @end_time.setter
    def end_time(self, new_time):
        """Set the new end time. This time cannot be smaller than the start time.
        """
        end_epoch = None
        if isinstance(new_time, time.struct_time):
            end_epoch = calendar.timegm(new_time)
        else:
            raise TypeError("Can't us a " + new_time.__class__.__name__ + " type to set the time.")

        if end_epoch < self._start_epoch():
            raise ValueError("End time needs to be after start time")

        self.minutes_to_next_schedule_entry = int((end_epoch - self._start_epoch()) / 60)

    def __str__(self):
        return "switch on: " + str(self.switch_on) + \
               ", start time: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", self.start_time) + \
               ", time to next schedule entry: " + _min2human(self.minutes_to_next_schedule_entry) + \
               ", end time: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", self.end_time)


class OutletSchedule(object):
    """Represents the hardware schedule for an outlet. It contains a list of (max 16) schedules, the time to wait before starting the
       schedule (rampup time) and when the schedule will start to run.

       A schedule can be executed once or periodically.
    """
    def __init__(self, data, sispy, outlet_nr=0):
        self._data = data
        self._sispy = sispy
        self._nr = outlet_nr

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
                self._entries.append(OutletScheduleEntry(data[i:i + 2], self, int((i - 4) / 2)))

        if len(self._entries) == 0:
            self._periodic = False
            self._rampup_minutes = 0

    def _construct_data(self, activation_time):
        new_epoch_activated = calendar.timegm(activation_time)
        if len(self._entries) > 0:
            start_epoch = self._entries[0]._start_epoch()
            self._rampup_minutes = int((start_epoch - new_epoch_activated) / 60)
            self._epoch_activated = new_epoch_activated
        else:
            self._rampup_minutes = 0

        data = bytearray(range(38))
        struct.pack_into('<L', data, 0, int(self._epoch_activated))
        struct.pack_into('<H', data, 36, self._rampup_minutes)

        # write out the schedule entries
        i = 0
        while i < 15 and i < len(self._entries):
            data[4 + i * 2] = self._entries[i]._construct_data()[0]
            data[5 + i * 2] = self._entries[i]._construct_data()[1]
            i += 1
        if self.periodic is False:
            data[4 + i * 2] = 0
            data[5 + i * 2] = 0
            i += 1
        while i < 16:
            data[4 + i * 2] = 0xff
            data[5 + i * 2] = 0x3f
            i += 1
        return data

    def _get_current_time(self):  # pragma no cover
        return time.gmtime()

    def apply(self):
        data = self._construct_data(self._get_current_time())
        self._sispy._usb_write(SisPy._OUTLET_SCHEDULE, self._nr, data)

    def reset(self):
        self._entries = []
        self._periodic = True

    def _epoch_to_time(self, epoch):
        return time.gmtime(epoch)

    def _add_schedule_minutes(self, schedules):
        if len(schedules) > 0:
            min_to_next_schedule = 0
            for s in schedules:
                min_to_next_schedule = min_to_next_schedule + s._minutes_to_next_schedule_entry

            return min_to_next_schedule
        else:
            return 0

    @property
    def time_activated(self):
        """The time the schedule was activated (stored on the power strip).

           The time is given by a time UTC tuple.
        """
        return self._epoch_to_time(self._epoch_activated)

    @property
    def rampup_minutes(self):
        """Time to wait before starting the schedule.

           This is given in minutes (an int).
        """
        return self._rampup_minutes

    @property
    def periodic(self):
        """Indicates whether the schedule is period or not.

           Change this to toggle between a periodic timer or not.

           This is True for a periodic schedule and False otherwise.
        """
        return self._periodic

    @periodic.setter
    def periodic(self, value):
        if not isinstance(value, bool):
            raise TypeError("Peridioc flag should be a boolean, not a " + value.__class__.__name__)
        self._periodic = value

    @property
    def periodicity_minutes(self):
        """If a schedule is periodic, the number of minutes before the schedule repeats itself.
           Otherise, None.

           This is an integer with the number of minutes.
        """
        if self.periodic is True:
            return self._add_schedule_minutes(self._entries)
        else:
            return None

    @property
    def schedule_minutes(self):
        """If a schedule is not periodic, the number of minutes the schedule will run, excluding the rampup time.
           Otherwise, None.

           This is an integer with the number of minutes.
        """
        if self.periodic is True:
            return None
        else:
            return self._add_schedule_minutes(self._entries)

    def _start_epoch(self):
        return self._epoch_activated + self._rampup_minutes * 60

    @property
    def start_time(self):
        """The time that the schedule will start. This is the actual time after the rampup is finished.

           This is a time UTC tuple.
        """
        return self._epoch_to_time(self._start_epoch())

    @property
    def end_time(self):
        """For periodic schedules,some silly date long, long time in the future.
           For non-periodic schedules, time when the schedule will finish.

           This is a time UTC tuple.
        """
        if self.periodic is True:
            return time.strptime('2999-12-31 23:59:59 UTC', '%Y-%m-%d %H:%M:%S %Z')
        else:
            return self._epoch_to_time(self._start_epoch() + self.schedule_minutes * 60)

    @property
    def entries(self):
        """List of the OutletScheduleEntry objects linked with the timer.

           Do not manipulate the list itself directly (e.g. adding or removing entries) because this will lead to unpredictable results.
           Use the add_entry() and remove_entry() methods for this.
        """
        return self._entries

    def add_entry(self):
        """Add an extra OutletScheduleEntry object to the list at the last position.

           This entry will have a length of 0 minutes.
           This entry will set the outlet off.
        """
        new_entry = OutletScheduleEntry(bytearray([0, 0]), self, len(self._entries))
        self._entries.append(new_entry)

    def remove_entry(self):
        """Removes the last entry from the list.
        """
        self._entries.pop()

    def __str__(self):
        string = "Time activated: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", self.time_activated) + \
            ", rampup time: " + _min2human(self.rampup_minutes) + \
            ", periodic: " + str(self.periodic)
        if self.periodic is True:
            string += ", periodicity: " + _min2human(self.periodicity_minutes) + " min."
        else:
            string += ", total time: " + _min2human(self.schedule_minutes) + " min." + \
                ", end time: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", self.end_time)
        for i in range(len(self.entries)):
            string += ", Entry " + str(i) + ": [" + str(self.entries[i]) + "]"
        return string

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
