#! /usr/bin/env python

import time
import calendar


from SisPy.lib import SisPy
from SisPy.lib import _min2human as m2h

sispy = SisPy()

print("ID: " + str(sispy.id))
for i in range(4):
    outlet = sispy.outlets[i]
    print("Outlet", i, ":")
    print("  Switched on: " + str(outlet.switched_on))
    current_entry = outlet.current_schedule_entry
    print("  # schedule entries: " + str(len(outlet.schedule.entries)))
    print("  Schedule set at:    " + time.strftime("%Y-%m-%d %H:%M:%S UTC", outlet.schedule.time_activated))
    if len(outlet.schedule.entries) > 0:
        print("  Periodic schedule: " + str(outlet.schedule.periodic))
        print("  Current schedule entry:")
        schedule_nr = current_entry.current_schedule_nr
        if schedule_nr is not None:
            if current_entry.timing_error is True:
                print("      SCHEDULE ERROR DETECTED !!")
            print("      Switched on at start:   " + str(current_entry.switched_it_on))
            print("      # of current entry:     " + str(current_entry.current_schedule_nr))
            print("      Start of current entry: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", outlet.schedule.entries[current_entry.current_schedule_nr].start_time))
        print("      Minutes to next entry:  " + str(current_entry.minutes_to_next_schedule_entry))
        print("      Start of next entry:    " + time.strftime("%Y-%m-%d %H:%M UTC +/- 1 min", time.gmtime(time.time() + current_entry.minutes_to_next_schedule_entry * 60)))
    for e in range(len(outlet.schedule.entries)):
        schedule_entry = outlet.schedule.entries[e]
        print("  Entry #%-2i:" % (e,), end=' ')
        print("Switch on at start:  %-5s |" % (str(schedule_entry.switch_on),), end=' ')
        print("Start time: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", schedule_entry.start_time),"|", end=' ')
        print("Minutes active: " + m2h(schedule_entry.minutes_to_next_schedule_entry))
    print()

# vim: set ai tabstop=4 shiftwidth=4 expandtab :
