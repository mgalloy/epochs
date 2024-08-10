# -*- coding: utf-8 -*-

"""Module defining timeline generator.
"""

import argparse
import datetime
import os
import re
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

import epochs


named_colors = matplotlib.colors.get_named_colors_mapping()
hex_color_re = re.compile("^#[abcdef0-9]{6}$")

LINESTYLES = {
    "solid": "solid",
    "dotted": "dotted",
    "dashed": "dashed",
    "dashdot": "dashdot",
    "loosely dotted": (0, (1, 10)),
    "dotted": (0, (1, 1)),
    "densely dotted": (0, (1, 1)),
    "long dash with offset": (5, (10, 3)),
    "loosely dashed": (0, (5, 10)),
    "dashed": (0, (5, 5)),
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


def warn(msg):
    print(f"WARNING: {msg}")


def load(filename):
    with open(filename, "r") as f:
        y = yaml.load(f, Loader=Loader)
    return y


def loads(s):
    return yaml.load(s, Loader=Loader)


def _get_type(timeline, typename):
    return [item for item in timeline if timeline[item].get("type") == typename]


def _valid_hexcolor(color):
    return bool(hex_color_re.match(color))


def _encode_color(color):
    if color in named_colors:
        color = named_colors[color]
    elif not _valid_hexcolor(color):
        warn(
            f'{name} interval color "{color}" not a named color or 6-digit hex value, using black'
        )
        color = "#000000"
    return color


def _encode_linestyle(linestyle):
    return LINESTYLES[linestyle]


class timeline_coords(object):
    annotation_fontsize = 8  # pts
    note_fontsize = 6  # pts
    ticklabel_fontsize = 7  # pts
    line_height = 1.5
    ax = None
    top_ax = None

    def __init__(self, timeline, top_name):
        self.start_date = dateutil.parser.parse(timeline[top_name]["start"])
        self.end_date = dateutil.parser.parse(timeline[top_name]["end"])

        self.width = timeline[top_name].get("width", 8.0)
        self.height = timeline[top_name].get("height", 8.0)

        self.y_annotation_gap = (
            0.25 * self.line_height * self.annotation_fontsize / (self.height * 72)
        )  # 72 pts/inch
        self.note_gap = (
            0.25 * self.line_height * self.note_fontsize / (self.height * 72)
        )

    def get_date_coord(self, date):
        return (date - self.start_date) / (self.end_date - self.start_date)


def setup_plot(timeline, coords, top_name):
    fig, ax = plt.subplots(figsize=(coords.width, coords.height))

    plt.tick_params(labelsize=coords.ticklabel_fontsize)
    top_ax = ax.twiny()
    plt.tick_params(labelsize=coords.ticklabel_fontsize)

    coords.ax = ax
    coords.top_ax = top_ax

    ticks = timeline[top_name].get("ticks", "weeks").lower()

    if ticks == "days":
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        major_locator = mdates.DayLocator(interval=1)
        minor_locator = None
    elif ticks == "weeks":
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        major_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=4)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    elif ticks == "months":
        tick_format = timeline[top_name].get("tick-format", "%b %y")
        major_locator = mdates.MonthLocator(interval=1)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    else:
        tick_format = timeline[top_name].get("tick-format", "%d %b %y")
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
        minor_locator = None

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

    ax.set_xlim([coords.start_date, coords.end_date])
    top_ax.set_xlim(ax.get_xlim())

    grid_color = "#e8e8e8"
    plt.grid(which="minor", axis="x", linestyle=":", color=grid_color)
    plt.grid(which="major", axis="x", color=grid_color)

    # set title of timeline
    plt.title(top_name, y=1.1)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.1)

    plt.setp(ax.get_xticklabels(), rotation=-25, ha="left")
    plt.setp(top_ax.get_xticklabels(), rotation=25, ha="left")

    return fig, ax


def render_numbering(timeline, fig, coords, ax, verbose=False):
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

        tick_locations = axis.get_xaxis().get_minor_locator()()

        ha = n["alignment"] if "alignment" in n else "center"
        if ha == "center":
            xlocs = 0.5 * (tick_locations[1:] + tick_locations[0:-1])
        elif ha == "left":
            xlocs = tick_locations[0:-1]
        elif ha == "right":
            xlocs = tick_locations[1:]
        else:
            xlocs = 0.5 * (tick_locations[1:] + tick_locations[0:-1])

        interval = n["interval"] if "interval" in n else "day"
        value = int(n["initial_value"]) if "initial_value" in n else 1
        for t, x in zip(tick_locations, xlocs):
            if interval == "week" and "initial_value" not in n:
                d = matplotlib.dates.num2date(t)
                value = int(d.strftime("%W"))
            plt.text(x, yloc, f"{value}", ha=ha, va=va, fontsize=5, color="#606060")
            value += 1


def render_events(timeline, fig, coords, ax, verbose=False):
    events = _get_type(timeline, "event")
    for name in events:
        if verbose:
            print(f"event: {name}")
        start_date = dateutil.parser.parse(timeline[name]["date"])
        end_date = (
            dateutil.parser.parse(timeline[name]["end"])
            if "end" in timeline[name]
            else None
        )
        color = _encode_color(str(timeline[name].get("color", "black")))
        text_color = _encode_color(str(timeline[name].get("text_color", "black")))
        x = coords.get_date_coord(start_date)
        y = float(timeline[name].get("location", 0.90))
        if end_date is not None:
            ax.axhline(
                y=1.0,
                xmin=x,
                xmax=coords.get_date_coord(end_date),
                color=color,
                linewidth=6.0,
            )
        ax.axvline(x=start_date, ymin=y, ymax=1.0, color=color, linewidth=0.5)
        title_text = plt.text(
            start_date,
            y - coords.y_annotation_gap,
            name.encode().decode("unicode_escape"),
            verticalalignment="top",
            color=text_color,
            fontsize=coords.annotation_fontsize,
        )

        r = fig.canvas.get_renderer()
        bb = title_text.get_window_extent(renderer=r)
        point = ax.transData.inverted().transform(
            (min(bb.intervalx), min(bb.intervaly))
        )
        lower_left = point[1]

        note = timeline[name].get("note")
        if note is not None:
            plt.text(
                start_date,
                lower_left - coords.note_gap,
                note.encode().decode("unicode_escape"),
                verticalalignment="top",
                fontsize=coords.note_fontsize,
                fontstyle="italic",
                horizontalalignment="left",
            )
        # print(f"{name}: {start_date} to {end_date}, at {x:0.3f}, {y} in {color}")


def _calculation_duration(duration: str) -> datetime.timedelta:
    tokens = duration.split()
    number = int(tokens[0])
    units = tokens[1]
    if units[-1] == "s":
        units = units[0:-1]
    timedelta_units = TIMEDELTA_UNITS[units]
    return number * timedelta_units


def render_intervals(timeline, fig, coords, ax, verbose=False):
    intervals = _get_type(timeline, "interval")

    # define "start" for relatively define intervals
    defined_intervals = []
    undefined_intervals = []
    for name in intervals:
        if timeline[name].get("start") is None:
            undefined_intervals.append(name)
        else:
            defined_intervals.append(name)

    # extremely naive algorithm to define start for all undefined intervals
    while len(defined_intervals) < len(intervals):
        for name in undefined_intervals:
            i = timeline[name]
            start_after = i.get("start_after")
            if start_after is not None:
                start_after_end = timeline[start_after].get("end")
                if start_after_end is None:
                    start_after_start = timeline[start_after].get("start")
                    if start_after_start is None:
                        continue
                    start_after_duration = timeline[start_after].get("duration")
                    start_after_end = dateutil.parser.parse(
                        start_after_start
                    ) + _calculation_duration(start_after_duration)
                i["start"] = start_after_end.strftime("%Y-%m-%d")
                defined_intervals.append(name)
            else:
                print(f"undefined start for interval {name}")

    # define "end" for intervals with duration
    for name in intervals:
        i = timeline[name]
        if i.get("end") is None:
            duration = i.get("duration")
            duration_timedelta = _calculation_duration(duration)
            start = dateutil.parser.parse(i.get("start"))
            i["end"] = (start + duration_timedelta).strftime("%Y-%m-%d")

    for name in intervals:
        if verbose:
            print(f"interval: {name}")
        i = timeline[name]
        start = dateutil.parser.parse(i.get("start"))
        end = dateutil.parser.parse(i.get("end"))

        color = _encode_color(str(i.get("color", "black")))
        linewidth = i.get("linewidth", 3.0)
        linestyle = _encode_linestyle(i.get("linestyle", "solid"))

        xmin = coords.get_date_coord(start)
        xmax = coords.get_date_coord(end)
        y = i.get("location", 0.5)
        # print(f"{name}: {xmin} to {xmax} at y={y}")
        ax.axhline(
            y=y,
            xmin=xmin,
            xmax=xmax,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
        )
        title_text = plt.text(
            start + 0.5 * (end - start),
            y - 2 * coords.y_annotation_gap,
            name.encode().decode("unicode_escape"),
            fontsize=coords.annotation_fontsize,
            verticalalignment="top",
            horizontalalignment="center",
        )

        r = fig.canvas.get_renderer()
        bb = title_text.get_window_extent(renderer=r)
        point = ax.transData.inverted().transform(
            (min(bb.intervalx), min(bb.intervaly))
        )
        lower_left = point[1]

        note = i.get("note")
        if note is not None:
            plt.text(
                start + 0.5 * (end - start),
                lower_left - coords.note_gap,
                note.encode().decode("unicode_escape"),
                verticalalignment="top",
                fontsize=coords.note_fontsize,
                fontstyle="italic",
                horizontalalignment="center",
            )


def render_lines(timeline, fig, coords, ax, verbose=False):
    vlines = _get_type(timeline, "vertical line")
    for name in vlines:
        if verbose:
            print(f"line: {name}")
        v = timeline[name]

        start_name = v.get("date")
        if start_name == "now":
            start = datetime.datetime.now()
        else:
            start = dateutil.parser.parse(start_name)

        color = _encode_color(str(v.get("color", "black")))
        ax.axvline(x=start, ymin=0.0, ymax=1.0, color=color, linewidth=1.0)


def generate(timeline, filename, args, parser):
    top_names = _get_type(timeline, "timeline")

    # check to make sure top_name is unique
    if len(top_names) == 0:
        parser.error("No top-level timeline")
    elif len(top_names) > 1:
        parser.error("Top-level timeline not unique")
    top_name = top_names[0]

    coords = timeline_coords(timeline, top_name)

    fig, ax = setup_plot(timeline, coords, top_name)

    render_events(timeline, fig, coords, ax, verbose=args.verbose)
    render_intervals(timeline, fig, coords, ax, verbose=args.verbose)
    render_lines(timeline, fig, coords, ax, verbose=args.verbose)
    render_numbering(timeline, fig, coords, ax, verbose=args.verbose)

    # write timeline output
    plt.savefig(filename)


def main():
    name = f"Timeline generator (epochs {epochs.__version__})"
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

    generate(timeline, output_filename, args, parser)


if __name__ == "__main__":
    main()
