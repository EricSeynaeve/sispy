#! /usr/bin/env python

import time

from SisPy.lib import SisPy

def main():
    sispy = SisPy()

    # not used
    outlet = sispy.outlets[0]
    outlet.switched_on = False

    # not used
    outlet = sispy.outlets[1]
    outlet.switched_on = False

    # white light
    outlet = sispy.outlets[2]
    on_off_one_day_sun_schedule( (7,30,0), (18,30,0), outlet)

    # red light
    outlet = sispy.outlets[3]
    on_off_one_day_sun_schedule( (7,00,0), (19,00,0), outlet)

def on_off_one_day_sun_schedule(sun_time_on, sun_time_off, outlet):
    # offset from UTC to sun time
    hours_from_sun   = 0
    minutes_from_sun = 20

    current_epoch = time.time()

    # first assume local time is given
    today_on_time = list(time.localtime(current_epoch))
    today_on_time[3] = sun_time_on[0]
    today_on_time[4] = sun_time_on[1]
    today_on_time[5] = sun_time_on[2]
    # convert to epoch and adjust from local time to UTC
    if time.daylight == 1:
        today_on_epoch = time.mktime(today_on_time) - time.altzone
    else:
        today_on_epoch = time.mktime(today_on_time) - time.timezone
    # adjust to sun time
    today_on_epoch = today_on_epoch - (hours_from_sun * 3600 + minutes_from_sun * 60)
    # convert sun epoch to UTC tuple
    today_on_time = time.gmtime(today_on_epoch)

    # first assume local time is given
    today_off_time = list(time.localtime(current_epoch))
    today_off_time[3] = sun_time_off[0]
    today_off_time[4] = sun_time_off[1]
    today_off_time[5] = sun_time_off[2]
    # convert to epoch and adjust from local time to UTC
    if time.daylight == 1:
        today_off_epoch = time.mktime(today_off_time) - time.altzone
    else:
        today_off_epoch = time.mktime(today_off_time) - time.timezone
    # adjust to sun time
    today_off_epoch = today_off_epoch - (hours_from_sun * 3600 + minutes_from_sun * 60)
    # convert sun epoch to UTC tuple
    today_off_time = time.gmtime(today_off_epoch)

    minutes_from_on_to_off = int( (today_off_epoch-today_on_epoch)/60 )
    minutes_from_off_to_on = 24*60 - minutes_from_on_to_off

    # start a period schedule from scratch
    my_schedule = outlet.schedule
    my_schedule.reset()
    my_schedule.periodic = True
    my_schedule.add_entry()
    if current_epoch < today_on_epoch:
        # the switch still needs to be switched on
        outlet.switched_on = False
        my_schedule.entries[0].start_time = today_on_time
        my_schedule.entries[0].switch_on = True
        my_schedule.entries[0].minutes_to_next_schedule_entry = minutes_from_on_to_off
        my_schedule.add_entry()
        my_schedule.entries[1].switch_on = False
        my_schedule.entries[1].minutes_to_next_schedule_entry = minutes_from_off_to_on
    elif current_epoch < today_off_epoch:
        # the switch is switched on
        outlet.switched_on = True
        my_schedule.entries[0].start_time = today_off_time
        my_schedule.entries[0].switch_on = False
        my_schedule.entries[0].minutes_to_next_schedule_entry = minutes_from_off_to_on
        my_schedule.add_entry()
        my_schedule.entries[1].switch_on = True
        my_schedule.entries[1].minutes_to_next_schedule_entry = minutes_from_on_to_off
    else:
        # the switch is already switched off
        outlet.switched_on = False
        my_schedule.entries[0].start_time = time.gmtime(today_on_epoch+24*60*60) # switch on tomorrow
        my_schedule.entries[0].switch_on = True
        my_schedule.entries[0].minutes_to_next_schedule_entry = minutes_from_on_to_off
        my_schedule.add_entry()
        my_schedule.entries[1].switch_on = False
        my_schedule.entries[1].minutes_to_next_schedule_entry = minutes_from_off_to_on

    # make sure the periodicity is 24 hours
    assert my_schedule.periodicity_minutes == 24 * 60

    # store the schedule on the power strip
    my_schedule.apply()

main()
