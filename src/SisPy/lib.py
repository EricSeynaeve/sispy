#! /usr/bin/env python

import struct
import time
import usb


class SisPy(object):
    ID = 1
    OUTLET_STATUS = 3
    OUTLET_SCHEDULE = 4
    OUTLET_CURRENT_SCHEDULE_ITEM = 5

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
        if command == SisPy.OUTLET_SCHEDULE:
            data = self._dev.ctrl_transfer(request_type, request, 0x0304 + outlet_nr * 3, 0, 38, 500)
            return data
        if command == SisPy.OUTLET_CURRENT_SCHEDULE_ITEM:
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
    def __init__(self, nr, sispy):
        self._nr = nr
        self._sispy = sispy

    @property
    def switched_on(self):
        data = self._sispy._usb_read(SisPy.OUTLET_STATUS, self._nr)
        return data == 0x03

    @property
    def schedule(self):
        data = self._sispy._usb_read(SisPy.OUTLET_SCHEDULE, self._nr)
        return OutletSchedule(data)

    @property
    def current_schedule_item(self):
        data = self._sispy._usb_read(SisPy.OUTLET_CURRENT_SCHEDULE_ITEM, self._nr)
        return OutletCurrentScheduleItem(data)


class OutletCurrentScheduleItem(object):
    """Indicates where the outlet currently is in the execution of the schedule.
       This is continuously updated by the outlet. Also, this information is only informational, nothing can be set.

       It will indicate whether the outlet was switched on at the beginning of the current outlet schedule item,
       how long until the next outlet schedule item, where we are in the schedule list and whether a time error status is detected.

       The latter can happen when the power socket is set without current for a long time.
    """
    def __init__(self, data):
        self._data = data

        self._timing_error = (data[0] & 0x80 == 0x80)
        self._next_schedule_nr = (data[0] & 0x7f)
        value = struct.unpack('<H', data[1:])[0]

        if self._next_schedule_nr == 0x10:
            # We're still waiting for the initial delay to finish
            self._next_schedule_nr = 0
            self._sequence_rampup = True
            self._minutes_to_next_schedule_item = value
        else:
            self._next_schedule_nr = (data[0] & 0x7f)
            self._sequence_rampup = False
            self._minutes_to_next_schedule_item = (value & 0x3FFF)

        self._switched_it_on = (value & 0x8000 == 0x8000)
        self._sequence_done = (self._minutes_to_next_schedule_item == 0)

    @property
    def timing_error(self):
        """Indicate that the power socket is not sure about the current time anymore. This can happen when it's set without current for a long time.

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
    def next_schedule_nr(self):
        """Schedule number of the next schedule in the list to execute.

           An integer from 0 onwards.
        """
        return self._next_schedule_nr

    @property
    def switched_it_on(self):
        """Indicate whether the outlet was switched on at the start of the schedule or not.
           The current status of the outlet can be different due to other influences.

           True if the outlet was switched on.
        """
        return self._switched_it_on

    @property
    def minutes_to_next_schedule_item(self):
        """Number of minutes still to wait before starting the next schedule item.
           This is updated by the power socket itself.

           An integer with the number of minutes.
        """
        return self._minutes_to_next_schedule_item

    @property
    def sequence_done(self):
        """Indicate whether the sequence finished executing.
           This can only happen for non-periodic sequences.

           True if the sequence is finished.
        """
        return self._sequence_done


class OutletScheduleItem(object):
    """Represents an item in the schedule by it's status at the start and the time before the next item is executed.

       This can be read and manipulated in different ways:
       - (start time, wait time in minutes)
       - (end time, wait time in minutes)
       - (start time, end time)

       With a manipulation in one item, the remaining will be set accordingly.
       Manipulating the start time will also change the end time.
       Manipulating the wait time will also change the end time.
       Manipulating the end time will also adjust the wait time.

       E.g.
       - if the start time is 09:30 and the wait time is set at 15 minutes, the end time will be 09:45.
       - if the start time is 09:30 and the end time is set at 09:50, the wait time will be 20 minutes.
       - if the wait time is 15 minutes and the start time is set at 09:15, the end time will be 09:30.

       The start time will always take into account the wait times if the previous items (if any).
    """
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
        """True when the outlet was set on at the start of this schedule item. False other wise.

           Beware, the current status could be different due to other manipulations after that time.
        """
        return self._switch_on

    @property
    def minutes_to_next_schedule(self):
        """The set wait time in minutes after this schedule item was started to start the next one.

           This is always an int.
        """
        return self._minutes_to_next_schedule

    def _start_epoch(self):
        delay_minutes = self._schedule._add_schedule_minutes(self._schedule._entries[:self._item_nr])
        return self._schedule._start_epoch() + delay_minutes * 60

    @property
    def start_time(self):
        """Start time of this schedule item.

           This is a time UTC tuple.
        """
        return self._schedule._epoch_to_time(self._start_epoch())

    @property
    def end_time(self):
        """When this schedule item will end and the next one will start.

           This is a time UTC tuple.
        """
        return self._schedule._epoch_to_time(self._start_epoch() + self._minutes_to_next_schedule * 60)


class OutletSchedule(object):
    """Represents the hardware schedule for an outlet. It contains a list of (max 16) schedules, the time to wait before starting the
       schedule (rampup time) and when the schedule will start to run.

       A schedule can be executed once or periodically.
    """
    def __init__(self, data):
        self._data = data

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
                self._entries.append(OutletScheduleItem(data[i:i + 2], self, (i - 4) / 2))

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
        """The time the schedule was activated (stored on the hardware power socket).

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

           This is True for a periodic schedule and False otherwise.
        """
        return self._periodic

    @property
    def periodicity_minutes(self):
        """If a schedule is periodic, the number of minutes before it repeats itself.
           Otherise, None.

           This is an integer with the number of minutes.
        """
        if self.periodic is True:
            return self._add_schedule_minutes(self._entries)
        else:
            return None

    @property
    def schedule_minutes(self):
        """If a schedule is not periodic, the time the schedule start will run.
           If a schedule is periodic, None.

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
        """List of the OutletScheduleItem objects linked with the timer.
        """
        return self._entries

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
