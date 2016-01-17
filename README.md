# sispy

Python library for working with the Gembird Energenie PMS2 power switch, including programming the hardware schedules.

After receiving the EG-PMS2, I found out wine does not support USB drivers. The apps I found (didn't find egpms_ctl till much later) didn't support the hardware schedule.

When contacting the distributor, they provided me with some information on programming the hardware schedules. Using information + some reverse engineering (the doc obtained contained some errors), I managed to come up with a, IMHO, intuitive python library.

## Dependencies

Requires the pyusb library for working with the power switch through USB. The advantage of pyusb is that you don't have to worry which particular USB library is installed (libusb 0.1, libusb 1.0, libusbx, libusb-win32 or OpenUSB).

## Usage example

Before running this example, make sure the power switch is connected to the computer.

```python
from SisPy import SisPy

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
my_schedule.entries[0].minutes_to_next_schedule_item = 14 * 60
my_schedule.add_entry()
# then switch it on for 10 hours
my_schedule.entries[1].switch_on = True
my_schedule.entries[1].minutes_to_next_schedule_item = 10 * 60

# make sure the periodicity is 24 hours
assert my_schedule.periodicity_minutes == 24 * 60

# store the schedule on the power strip
my_schedule.apply()
```

## Limitations

- only tested on the USB version EG-PMS2
- all times are entered and received in UTC !
- will only take the first power switch found in the USB devices walk through.

## See also:

- http://sispmctl.sourceforge.net/ The project which seems to have started it all. C-application to control the power of the outlets and supports several (especially older) types of power strips. No possibility to set the hardware schedule though.
- https://github.com/zdazzy/eg-pyms-lan for setting the LAN version. Only controls the state of the power buttons.
- https://github.com/scosu/egpms_ctl for a kernel driver to set the USB version. I believe setting with the python app is more intuitive.
