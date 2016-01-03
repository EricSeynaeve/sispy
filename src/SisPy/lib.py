#! /usr/bin/env python


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

# vim: set ai tabstop=2 shiftwidth=2 expandtab :
