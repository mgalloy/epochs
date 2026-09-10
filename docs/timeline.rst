========
Timeline
========

special "timeline" item

All items in the timeline have a type:

- ``type`` -- one of the types described below: "interval", "band", "line",
  "event", "numbering", or "value"

There are other common fields with the same format for allowable values:

- date fields -- [TODO]: specify format
- ``duration`` -- specified as "X unit" where "X" must be an integer value and
  "unit" must be one of "second", "minute", "hour", "day", "week", "month",
  "year", or plural version of one of these
- color fields -- such as ``color``, ``title_color``, ``note_color``, etc,
  [TODO]: specify format


Intervals
=========

The allowable fields of an interval are:

- ``start`` -- start date of the interval, must have either ``start`` or
  ``start_after``
- ``start_after`` -- name of another item in the timeline where this item will
  start immediately after the other item ends, must have either ``start`` or
  ``start_after``
- ``end`` -- end date of the interval, must have either ``end`` or ``duration``
- ``duration`` -- duration of the interval
- ``color`` -- color of the interval line
- ``title_color`` -- color field that controls the color of the interval title
- ``note_color`` -- color field that controls the color of the note text
- ``linewidth`` -- floating point value
- ``linestyle`` -- one of "solid", "dotted", "dashed", "dashdot", "loosely
  dotted", "dotted", "densely dotted", "long dash with offset", "loosely
  dashed", "dashed", "densely dashed", "loosely dashdotted", "dashdotted",
  "densely dashdotted", "dashdotdotted", "loosely dashdotdotted", or
  "densely dashdotdotted"
- ``location`` -- a floating point value in the range 0.0-1.0 where 0.0
  represents the bottom of the timeline and 1.0 represents the top
- ``annotation`` -- if "start" is in ``annotation`` the date of the start of the
  interval will be displayed, if "end" is in ``annotation`` the end of the
  interval will be displayed
- ``annotation_format``
- ``note`` -- note text
- ``title`` -- title text


Bands
=====

Fields:

- ``start``
- ``start_after``
- ``end``
- ``duration``
- ``fillcolor``
- ``edgecolor``
- ``hatchcolor``
- ``title_color``
- ``note_color``
- ``linewidth``
- ``linestyle``
- ``location``
- ``annotation``
- ``annotation_format``
- ``title``
- ``note``

Lines
=====

Fields:

- ``date``
- ``color``
- ``title``


Events
======

Fields:

- ``date``
- ``end``
- ``color``
- ``title_color``
- ``note_color``
- ``location``
- ``wrap``
- ``title``
- ``note``


Numberings
==========

Fields:

- ``position``
- ``interval``
- ``fontsize``
- ``alignment``
- ``initial_value``


Values
======

- ``interval``
- ``value``
- ``location``
- ``rotation``
- ``fontsize``
- ``start_week``
