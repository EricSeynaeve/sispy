#! /usr/bin/env python

import time

from SisPy.lib import SisPy

sispy = SisPy()

my_outlet = sispy.outlets[0]
# make sure the outlet is switched on
my_outlet.switched_on = True

my_schedule = my_outlet.schedule

# start a period schedule from scratch
my_schedule.reset()
my_schedule.periodic = True
my_schedule.add_entry()
# adjust this time to your own liking
my_schedule.entries[0].start_time = time.strptime('2016-01-17 20:30:00 UTC', '%Y-%m-%d %H:%M:%S %Z')
# switch the outlet off for 14 hours
my_schedule.entries[0].switch_on = False
my_schedule.entries[0].minutes_to_next_schedule_entry = 14 * 60
my_schedule.add_entry()
# then switch it on for 10 hours
my_schedule.entries[1].switch_on = True
my_schedule.entries[1].minutes_to_next_schedule_entry = 10 * 60

# make sure the periodicity is 24 hours
assert my_schedule.periodicity_minutes == 24 * 60

# store the schedule on the power strip
my_schedule.apply()
