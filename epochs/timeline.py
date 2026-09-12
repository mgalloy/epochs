# -*- coding: utf-8 -*-

"""Module defining timeline generator, a command-line utility to convert a
yaml specification into a PDF timeline.
"""

import argparse
import datetime
import os
import re
import textwrap
import warnings

import dateutil.parser
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from . import __version__


named_colors = matplotlib.colors.get_named_colors_mapping()
hex_color_re = re.compile("^#[ABCDEFabcdef0-9]{6}$")

LINESTYLES = {
    "solid": "solid",
    "dotted": "dotted",
    "dashed": "dashed",
    "dashdot": "dashdot",
    "loosely dotted": (0, (1, 10)),
    "densely dotted": (0, (1, 1)),
    "long dash with offset": (5, (10, 3)),
    "loosely dashed": (0, (5, 10)),
    "densely dashed": (0, (5, 1)),
    "loosely dashdotted": (0, (3, 10, 1, 10)),
    "dashdotted": (0, (3, 5, 1, 5)),
    "densely dashdotted": (0, (3, 1, 1, 1)),
    "dashdotdotted": (0, (3, 5, 1, 5, 1, 5)),
    "loosely dashdotdotted": (0, (3, 10, 1, 10, 1, 10)),
    "densely dashdotdotted": (0, (3, 1, 1, 1, 1, 1)),
}

TIMEDELTA_UNITS = {
    "second": datetime.timedelta(seconds=1),
    "minute": datetime.timedelta(minutes=1),
    "hour": datetime.timedelta(hours=1),
    "day": datetime.timedelta(days=1),
    "week": datetime.timedelta(weeks=1),
    "month": datetime.timedelta(days=30),
    "year": datetime.timedelta(days=365),
}


class ParsingError(Exception):
    """Throw if there is any parsing error in the timeline specification."""


def load(filename: str):
    """Load a YAML specification given a filename, returning a combination of
    dicts and lists."""
    with open(filename, "r", encoding="utf-8") as f:
        y = yaml.load(f, Loader=Loader)
    return y


def loads(s: str):
    """Load a YAML specification as a string , returning a combination of dicts
    and lists."""
    return yaml.load(s, Loader=Loader)


def warn(msg: str):
    """Print a warning message to stdout."""
    print(f"WARNING: {msg}")


def _convert_duration(duration: str) -> datetime.timedelta:
    """Convert the duration of an event from a string to a `datetime.timedelta`.
    The duration must be a number followed by one more more spaces followed by
    the unit. The accepted units are in `TIMEDELTA_UNITS` and may be plural or
    not."""
    tokens = duration.split()
    number = int(tokens[0])
    units = tokens[1]
    if units[-1] == "s":
        units = units[0:-1]
    timedelta_units = TIMEDELTA_UNITS[units]
    return number * timedelta_units


def _get_type(timeline: dict, typename: str) -> list[dict]:
    """Get all the items of a particular type in the timeline."""
    return [item for item in timeline if timeline[item].get("type") == typename]


def _valid_hexcolor(color: str) -> bool:
    """Returns whether the given color is a valid color specified using hex,
    such as "#a0cfd8"."""
    return bool(hex_color_re.match(color))


def _encode_color(color: str) -> str:
    """If it is not already a valid hex color specification for a color, get the
    hex color specification for a color given a color name recognized by
    matplotlib."""
    if color in named_colors:
        color = named_colors[color]
    elif not _valid_hexcolor(color):
        warn(
            f'interval color "{color}" not a named color or 6-digit hex value, using black'
        )
        color = "#000000"
    return color


def _encode_linestyle(linestyle: str) -> str | tuple:
    """Convert a named linestyle to a valid matplotlib specification for a
    linestyle."""
    return LINESTYLES[linestyle]


def _encode_boolean(value):
    if isinstance(value, bool):
        return value
    return value.lower() in ["yes", "true"]


class TimelineCoords:
    """Class representing the coordinate system of a timeline, invcluding the
    sizes of fonts of various items, the dimensions of the timeline graphic,
    gaps between items, etc."""

    annotation_fontsize = 5  # pts
    ticklabel_fontsize = 7  # pts
    line_height = 1.5
    ax = None
    top_ax = None

    def __init__(self, timeline: dict, top_name: str):
        timelime_item = timeline[top_name]

        self.start_date = dateutil.parser.parse(timelime_item["start"])
        self.end_date = dateutil.parser.parse(timelime_item["end"])

        self.width = timelime_item.get("width", 8.0)
        self.height = timelime_item.get("height", 8.0)

        self.fontsizes = {  # in pts
            "interval_title": timelime_item.get("title_fontsize", 8),
            "band_title": timelime_item.get("title_fontsize", 8),
            "note_title": timelime_item.get("title_fontsize", 8),
            "note_text": timelime_item.get("note_fontsize", 6),
        }

        self.time_tick_display_cadence = timelime_item.get(
            "time_tick_display_cadence", 1
        )

        self.y_annotation_gap = self.calculate_ygap(self.fontsizes["interval_title"])
        self.note_gap = self.calculate_ygap(self.fontsizes["note_text"])

    def get_date_coord(self, date: datetime.datetime) -> float:
        """Converts a datetime into an x-coordinate of the timeline."""
        return (date - self.start_date) / (self.end_date - self.start_date)

    def calculate_ygap(self, fontsize: float) -> float:
        """Calculate the appropriate y-gap given the fontsize."""
        ppi = 72  # 72 pts/inch
        return 0.25 * self.line_height * fontsize / (self.height * ppi)


def order_timeline(timeline: dict, verbose: bool = True) -> None:
    """Define start/end date/times for relatively defined intervals, bands,
    lines, and events."""
    start_name = {"interval": "start", "band": "start", "line": "date", "event": "date"}

    # first find the items that have a defined start
    defined_items = []
    undefined_items = []
    n_items_to_order = 0
    for name in timeline:
        type_name = timeline[name].get("type").lower()

        # don't need to order numberings or values
        if type_name not in ["interval", "band", "line", "event"]:
            continue

        n_items_to_order += 1
        if timeline[name].get(start_name[type_name]) is None:
            undefined_items.append(name)
        else:
            defined_items.append(name)

    if len(undefined_items) > 0 and verbose:
        print("items to order: " + ", ".join(f'"{i}"' for i in undefined_items))

    # extremely naive algorithm to define start for all undefined items
    while len(defined_items) < n_items_to_order:
        for name in undefined_items:
            i = timeline[name]
            type_name = i.get("type").lower()

            start_after = i.get("start_after")
            if start_after is not None:
                if start_after not in timeline:
                    raise ParsingError(f"unknown item '{start_after}'")
                start_after_end = timeline[start_after].get("end")
                if start_after_end is None:
                    start_after_start = timeline[start_after].get("start")
                    if start_after_start is None:
                        continue
                    start_after_duration = timeline[start_after].get("duration")
                    start_after_end = dateutil.parser.parse(
                        start_after_start
                    ) + _convert_duration(start_after_duration)
                i[start_name[type_name]] = (
                    start_after_end
                    if isinstance(start_after_end, str)
                    else start_after_end.strftime("%Y-%m-%d")
                )
                defined_items.append(name)
            else:
                warn(f"undefined start for item {name}")

    # define "end" for items with duration
    for name in timeline:
        i = timeline[name]
        type_name = i.get("type").lower()

        # don't need to order events, lines, numberings, or values
        if type_name not in ["interval", "band"]:
            continue

        if i.get("end") is None:
            duration = i.get("duration")
            if verbose:
                print(name, duration)
            duration_timedelta = _convert_duration(duration)
            start = dateutil.parser.parse(i.get(start_name[type_name]))
            i["end"] = (start + duration_timedelta).strftime("%Y-%m-%d")


def get_locator(timeline: dict, top_name: str, ticks: str) -> tuple:
    """Get the tick format, major locator, and minor locator for the x-axis of
    the timeline, given the timeline specification and the name of the how the
    ticks should be given: "hours", "days", "weeks", "months", or "years"."""
    if ticks == "days":
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        major_locator = mdates.DayLocator(interval=1)
        minor_locator = None
    elif ticks == "weeks":
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        major_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    elif ticks == "months":
        tick_format = timeline[top_name].get("tick-format", "%b %y")
        major_locator = mdates.MonthLocator(interval=1)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    elif ticks == "years":
        tick_format = timeline[top_name].get("tick-format", "%y")
        major_locator = mdates.YearLocator(month=1)
        minor_locator = mdates.MonthLocator(interval=1)
    elif ticks == "hours":
        tick_format = timeline[top_name].get("tick-format", "%H")
        major_locator = mdates.HourLocator(interval=1)
        minor_locator = mdates.MinuteLocator(interval=15)
    else:
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        major_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
        minor_locator = None

    return tick_format, major_locator, minor_locator


def setup_plot(timeline: dict, coords: TimelineCoords, top_name: str) -> tuple:
    """Get the figure and axes of a matplotlib plot for the given timeline."""
    fig, ax = plt.subplots(figsize=(coords.width, coords.height))

    axes_name = timeline[top_name].get("axes", "").lower()

    plt.tick_params(labelsize=coords.ticklabel_fontsize)
    top_ax = ax.twiny()
    plt.tick_params(labelsize=coords.ticklabel_fontsize)

    ax.set_autoscale_on(False)

    coords.ax = ax
    coords.top_ax = top_ax

    ticks = timeline[top_name].get("ticks", "weeks").lower()

    tick_format, major_locator, minor_locator = get_locator(timeline, top_name, ticks)

    ax.get_xaxis().set_major_locator(major_locator)
    top_ax.get_xaxis().set_major_locator(major_locator)
    if minor_locator:
        ax.get_xaxis().set_minor_locator(minor_locator)
        top_ax.get_xaxis().set_minor_locator(minor_locator)
    ax.get_xaxis().set_major_formatter(mdates.DateFormatter(tick_format))
    top_ax.get_xaxis().set_major_formatter(mdates.DateFormatter(tick_format))

    ax.get_yaxis().set_visible(False)
    top_ax.get_yaxis().set_visible(False)
    for spine in ["left", "right"]:
        ax.spines[spine].set_visible(False)
        top_ax.spines[spine].set_visible(False)

    ax.get_xaxis().set_visible(axes_name in ["bottom", "both"])
    top_ax.get_xaxis().set_visible(axes_name in ["top", "both"])

    ax.set_xlim([coords.start_date, coords.end_date])
    top_ax.set_xlim(ax.get_xlim())

    ax.set_ylim([0.0, 1.0])
    top_ax.set_ylim([0.0, 1.0])

    grid_color = "#e8e8e8"
    ax.grid(which="major", axis="x", color=grid_color)

    # set title of timeline
    title = timeline[top_name].get("title", top_name)
    title = title.encode().decode("unicode_escape")
    plt.title(title, y=1.1)

    left_margin = (
        timeline[top_name].get("left-margin", 0.05 * coords.width) / coords.width
    )
    right_margin = (
        timeline[top_name].get("right-margin", 0.05 * coords.width) / coords.width
    )
    top_margin = (
        timeline[top_name].get("top-margin", 0.05 * coords.height) / coords.height
    )
    bottom_margin = (
        timeline[top_name].get("bottom-margin", 0.05 * coords.height) / coords.height
    )

    plt.subplots_adjust(
        left=left_margin,
        right=1.0 - right_margin,
        top=1.0 - top_margin,
        bottom=bottom_margin,
    )

    plt.setp(ax.get_xticklabels(), rotation=-25, ha="left")
    plt.setp(top_ax.get_xticklabels(), rotation=25, ha="left")

    for i, label in enumerate(ax.xaxis.get_ticklabels()):
        if i % coords.time_tick_display_cadence != 0:
            label.set_visible(False)

    for i, label in enumerate(top_ax.xaxis.get_ticklabels()):
        if i % coords.time_tick_display_cadence != 0:
            label.set_visible(False)

    return fig


def render_numbering(timeline, fig, coords, verbose: bool = False):
    """Render the numbering type items in the timeline."""
    numberings = _get_type(timeline, "numbering")
    for name in numberings:
        if verbose:
            print(f"numbering: {name}")

        n = timeline[name]

        margin = 0.005
        position = n["position"] if "position" in n else "top"
        if position == "top":
            va = "bottom"
            yloc = 1.0 + margin
            axis = coords.top_ax
        elif position == "bottom":
            va = "top"
            yloc = 0.0 - margin
            axis = coords.ax
        else:
            va = "bottom"
            yloc = 1.0 + margin
            axis = coords.top_ax

        interval = n["interval"] if "interval" in n else "days"
        fontsize = n["fontsize"] if "fontsize" in n else 5
        color = n["color"] if "color" in n else "#606060"

        # TODO: need to find a better way to specify these locations using the
        # value of interval
        top_name = _get_type(timeline, "timeline")[0]
        _, major_locator, _ = get_locator(timeline, top_name, interval)
        vmin, vmax = axis.get_xlim()
        tick_locations = major_locator.tick_values(
            mdates.num2date(vmin), mdates.num2date(vmax)
        )

        ha = n["alignment"] if "alignment" in n else "center"
        if ha == "center":
            xlocs = 0.5 * (tick_locations[1:] + tick_locations[0:-1])
        elif ha == "left":
            xlocs = tick_locations[0:-1]
        elif ha == "right":
            xlocs = tick_locations[1:]
        else:
            xlocs = 0.5 * (tick_locations[1:] + tick_locations[0:-1])

        value = int(n["initial_value"]) if "initial_value" in n else 1
        for t, x in zip(tick_locations, xlocs):
            if interval == "weeks" and "initial_value" not in n:
                d = matplotlib.dates.num2date(t)
                value = int(d.strftime("%W"))
            plt.text(x, yloc, f"{value}", ha=ha, va=va, fontsize=fontsize, color=color)
            value += 1


def render_values(timeline, fig, coords, verbose=False):
    """Render the value type items in the timeline."""
    values = _get_type(timeline, "value")
    for name in values:
        if verbose:
            print(f"value: {name}")

        v = timeline[name]
        interval = v["interval"]
        interval_values = v["value"].split()
        yloc = v["location"]
        rotation = v["rotation"] if "rotation" in v else "horizontal"
        fontsize = v["fontsize"] if "fontsize" in v else 4

        top_name = _get_type(timeline, "timeline")[0]
        _, major_locator, _ = get_locator(timeline, top_name, interval)
        vmin, vmax = coords.ax.get_xlim()
        tick_locations = major_locator.tick_values(
            mdates.num2date(vmin), mdates.num2date(vmax)
        )
        xlocs = 0.5 * (tick_locations[1:] + tick_locations[0:-1])
        start_week = v["start_week"] if "start_week" in v else 1
        tick_locations = tick_locations[start_week - 1 :]
        xlocs = xlocs[start_week - 1 :]
        for x, interval_value in zip(xlocs, interval_values):
            coords.ax.text(
                x,
                yloc,
                f"{interval_value}",
                ha="center",
                va="bottom",
                rotation=rotation,
                fontsize=fontsize,
                color="#606060",
            )


def render_lines(timeline, fig, coords, verbose=False):
    """Render the vertical line type items in the timeline."""
    vlines = _get_type(timeline, "vertical line")
    for name in vlines:
        if verbose:
            print(f"vertical line: {name}")
        v = timeline[name]

        start_name = v.get("date")
        if start_name == "now":
            start = datetime.datetime.now()
        else:
            start = dateutil.parser.parse(start_name)

        color = _encode_color(str(v.get("color", "black")))
        linewidth = float(v.get("linewidth", 1.0))
        linestyle = _encode_linestyle(v.get("linestyle", "solid"))

        coords.ax.axvline(
            x=start,
            ymin=0.0,
            ymax=1.0,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
        )

        title = v.get("title")
        if title is not None:
            coords.ax.text(
                start,
                0.02,
                title,
                rotation="vertical",
                fontsize=coords.fontsizes["note_title"],
                ha="right",
                va="bottom",
            )


def render_events(timeline, fig, coords, verbose=False):
    """Render the event type items in the timeline."""
    events = _get_type(timeline, "event")
    for name in events:
        if verbose:
            print(f"event: {name}")
        start_dt = timeline[name]["date"]
        if isinstance(start_dt, datetime.datetime):
            start_date = start_dt
        else:
            start_date = dateutil.parser.parse(timeline[name]["date"])
        end_date = (
            dateutil.parser.parse(timeline[name]["end"])
            if "end" in timeline[name]
            else None
        )
        color = _encode_color(str(timeline[name].get("color", "black")))
        title_color = _encode_color(str(timeline[name].get("title_color", "black")))
        note_color = _encode_color(str(timeline[name].get("note_color", "black")))
        linewidth = float(timeline[name].get("linewidth", 6.0))
        x = coords.get_date_coord(start_date)
        y = float(timeline[name].get("location", 0.90))
        wrap = timeline[name].get("wrap", None)
        if end_date is not None:
            coords.ax.axhline(
                y=1.0,
                xmin=x,
                xmax=coords.get_date_coord(end_date),
                color=color,
                linewidth=linewidth,
            )
        coords.ax.axvline(x=start_date, ymin=y, ymax=1.0, color=color, linewidth=0.5)
        title = timeline[name].get("title")
        title_text = plt.text(
            start_date,
            y - coords.y_annotation_gap,
            (title if title is not None else name).encode().decode("unicode_escape"),
            verticalalignment="top",
            color=title_color,
            fontsize=coords.fontsizes["interval_title"],
        )

        r = fig.canvas.get_renderer()
        bb = title_text.get_window_extent(renderer=r)
        point = coords.ax.transData.inverted().transform(
            (min(bb.intervalx), min(bb.intervaly))
        )
        lower_left = point[1]

        note = timeline[name].get("note")
        if note is not None:
            note_text = note.encode().decode("unicode_escape")
            if wrap is not None:
                note_text = "\n".join(
                    textwrap.wrap(note_text, wrap, replace_whitespace=False)
                )

            coords.ax.text(
                start_date,
                lower_left - coords.note_gap,
                note_text,
                verticalalignment="top",
                color=note_color,
                fontsize=coords.fontsizes["note_text"],
                fontstyle="italic",
                horizontalalignment="left",
            )


def render_intervals(timeline, fig, coords, verbose=False):
    """Render the interval type items in the timeline."""
    intervals = _get_type(timeline, "interval")
    for name in intervals:
        i = timeline[name]
        start = dateutil.parser.parse(i.get("start"))
        end = dateutil.parser.parse(i.get("end"))
        if verbose:
            print(f"interval {name}: {start:%Y-%m-%d} - {end:%Y-%m-%d}")
        color = _encode_color(str(i.get("color", "black")))
        title_color = _encode_color(str(timeline[name].get("title_color", "black")))
        note_color = _encode_color(str(timeline[name].get("note_color", "black")))
        linewidth = float(i.get("linewidth", 3.0))
        linestyle = _encode_linestyle(i.get("linestyle", "solid"))

        xmin = coords.get_date_coord(start)
        xmax = coords.get_date_coord(end)
        y = i.get("location", 0.5)
        coords.ax.axhline(
            y=y,
            xmin=xmin,
            xmax=xmax,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
        )

        annotation_value = i.get("annotation", "")
        if annotation_value.find("start") >= 0:
            annotation_format = i.get("annotation_format", "%Y-%m-%d")
            coords.ax.text(
                start,
                y + coords.y_annotation_gap,
                "⇤" + start.strftime(annotation_format),
                fontsize=coords.annotation_fontsize,
                color="grey",
            )
        if annotation_value.find("end") >= 0:
            annotation_format = i.get("annotation_format", "%Y-%m-%d")
            coords.ax.text(
                end,
                y + coords.y_annotation_gap,
                end.strftime(annotation_format) + "⇥",
                fontsize=coords.annotation_fontsize,
                horizontalalignment="right",
                color="grey",
            )

        title = i.get("title")
        title_text = coords.ax.text(
            start + 0.5 * (end - start),
            y - 2 * coords.y_annotation_gap,
            (title if title is not None else name).encode().decode("unicode_escape"),
            fontsize=coords.fontsizes["interval_title"],
            verticalalignment="top",
            horizontalalignment="center",
            color=title_color,
        )

        r = fig.canvas.get_renderer()
        bb = title_text.get_window_extent(renderer=r)
        point = coords.ax.transData.inverted().transform(
            (min(bb.intervalx), min(bb.intervaly))
        )
        lower_left = point[1]

        note = i.get("note")
        if note is not None:
            coords.ax.text(
                start + 0.5 * (end - start),
                lower_left - coords.note_gap,
                note.encode().decode("unicode_escape"),
                verticalalignment="top",
                color=note_color,
                fontsize=coords.fontsizes["note_text"],
                fontstyle="italic",
                horizontalalignment="center",
            )


def render_bands(timeline, fig, coords, verbose=False):
    """Render the band type items in the timeline."""
    bands = _get_type(timeline, "band")
    for name in bands:
        i = timeline[name]
        start = dateutil.parser.parse(i.get("start"))
        end = dateutil.parser.parse(i.get("end"))
        if verbose:
            print(f"band {name}: {start:%Y-%m-%d} - {end:%Y-%m-%d}")
        fillcolor = _encode_color(str(i.get("fillcolor", "#c0c0c0")))
        edgecolor = _encode_color(str(i.get("edgecolor", "black")))
        hatchcolor = _encode_color(str(i.get("hatchcolor", "#a0a0a0")))
        title_color = _encode_color(str(i.get("title_color", "black")))
        note_color = _encode_color(str(i.get("note_color", "black")))
        linewidth = float(i.get("linewidth", 3.0))
        linestyle = _encode_linestyle(i.get("linestyle", "solid"))

        y = i.get("location", 0.5)
        coords.ax.axvline(
            x=start,
            ymin=0.0,
            ymax=1.0,
            color=edgecolor,
            linewidth=linewidth,
            linestyle=linestyle,
        )
        coords.ax.axvline(
            x=end,
            ymin=0.0,
            ymax=1.0,
            color=edgecolor,
            linewidth=linewidth,
            linestyle=linestyle,
        )
        xcoords = [start, end, end, start, start]
        ycoords = [1.0, 1.0, 0.0, 0.0, 1.0]
        coords.ax.fill(
            xcoords,
            ycoords,
            hatch="////",
            facecolor=fillcolor,
            edgecolor=hatchcolor,
        )

        annotation_value = i.get("annotation", "")
        if annotation_value.find("start") >= 0:
            annotation_format = i.get("annotation_format", "%Y-%m-%d")
            coords.ax.text(
                start,
                y + coords.y_annotation_gap,
                "⇤" + start.strftime(annotation_format),
                fontsize=coords.annotation_fontsize,
                color=i.get("annotation_color", "grey"),
            )
        if annotation_value.find("end") >= 0:
            annotation_format = i.get("annotation_format", "%Y-%m-%d")
            coords.ax.text(
                end,
                y + coords.y_annotation_gap,
                end.strftime(annotation_format) + "⇥",
                fontsize=coords.annotation_fontsize,
                horizontalalignment="right",
                color=i.get("annotation_color", "grey"),
            )

        title = i.get("title")
        title_text = coords.ax.text(
            start + 0.5 * (end - start),
            y - 2 * coords.y_annotation_gap,
            (title if title is not None else name).encode().decode("unicode_escape"),
            fontsize=coords.band_title_fontsize,
            verticalalignment="top",
            horizontalalignment="center",
            color=title_color,
        )

        r = fig.canvas.get_renderer()
        bb = title_text.get_window_extent(renderer=r)
        point = coords.ax.transData.inverted().transform(
            (min(bb.intervalx), min(bb.intervaly))
        )
        lower_left = point[1]

        note = i.get("note")
        if note is not None:
            coords.ax.text(
                start + 0.5 * (end - start),
                lower_left - coords.note_gap,
                note.encode().decode("unicode_escape"),
                verticalalignment="top",
                color=note_color,
                fontsize=coords.fontsizes["note_text"],
                fontstyle="italic",
                horizontalalignment="center",
            )


def generate(timeline, filename: str, args, parser) -> None:
    """Generate the PDF of the timeline."""
    top_names = _get_type(timeline, "timeline")

    # check to make sure top_name is unique
    if len(top_names) == 0:
        parser.error("No top-level timeline")
    elif len(top_names) > 1:
        parser.error("Top-level timeline not unique")
    top_name = top_names[0]

    coords = TimelineCoords(timeline, top_name)

    fig = setup_plot(timeline, coords, top_name)

    render_intervals(timeline, fig, coords, verbose=args.verbose)
    render_bands(timeline, fig, coords, verbose=args.verbose)
    render_events(timeline, fig, coords, verbose=args.verbose)
    render_lines(timeline, fig, coords, verbose=args.verbose)
    render_numbering(timeline, fig, coords, verbose=args.verbose)
    render_values(timeline, fig, coords, verbose=args.verbose)

    # write timeline output
    plt.savefig(filename)


def main():
    """Entry point for timeline CLI defined for project. Define arguments, parse
    them, read the YAML specification of the timline, and generate the PDF."""
    name = f"Timeline generator (epochs {__version__})"
    parser = argparse.ArgumentParser(description=name)
    parser.add_argument("-v", "--version", action="version", version=name)
    parser.add_argument("filename", help="YAML input filename")
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("--verbose", help="output warnings", action="store_true")
    args = parser.parse_args()

    try:
        timeline = load(args.filename)
    except FileNotFoundError:
        parser.error(f"file not found: {args.filename}")

    if args.output is None:
        output_filename = os.path.splitext(args.filename)[0] + ".pdf"
    else:
        output_filename = args.output

    if not args.verbose:
        warnings.filterwarnings("ignore")

    order_timeline(timeline, verbose=args.verbose)

    try:
        generate(timeline, output_filename, args, parser)
    except ParsingError as e:
        print(f"exiting with fatal error: {e}")


if __name__ == "__main__":
    main()
