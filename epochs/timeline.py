# -*- coding: utf-8 -*-

"""Module defining timeline generator.
"""

import argparse
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


def warn(msg):
    print(f"WARNING: {msg}")


def load(filename):
    with open(filename, "r") as f:
        y = yaml.load(f, Loader=Loader)
    return(y)


def loads(s):
    return(yaml.load(s, Loader=Loader))


def _get_type(timeline, typename):
    return [item for item in timeline if timeline[item].get("type") == typename]


def _valid_hexcolor(color):
    return bool(hex_color_re.match(color))


class timeline_coords(object):
    annotation_fontsize = 8   # pts
    note_fontsize = 6   # pts
    ticklabel_fontsize = 7   # pts
    line_height = 1.5

    def __init__(self, timeline, top_name):
        self.start_date = dateutil.parser.parse(timeline[top_name]["start"])
        self.end_date = dateutil.parser.parse(timeline[top_name]["end"])

        self.width = timeline[top_name].get("width", 8.0)
        self.height = timeline[top_name].get("height", 8.0)

        self.annotation_gap = self.line_height * self.annotation_fontsize / (self.height * 72)   # 72 pts/inch
        self.note_gap = self.line_height * self.note_fontsize / (self.height * 72)


def setup_plot(timeline, coords, top_name):
    fig, ax = plt.subplots(figsize=(coords.width, coords.height))

    plt.tick_params(labelsize=coords.ticklabel_fontsize)
    top_ax = ax.twiny()
    plt.tick_params(labelsize=coords.ticklabel_fontsize)

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
    plt.title(top_name, y=1.05)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)

    return fig, ax


def render_numbering(timeline, coords, ax):
    numberings = _get_type(timeline, "numbering")
    for name in numberings:
        n = timeline[name]
        #print(n)


def render_events(timeline, coords, ax):
    events = _get_type(timeline, "event")
    # TODO: implement
    for name in events:
        pass
        #print(timeline[name])


def render_intervals(timeline, coords, ax):
    intervals = _get_type(timeline, "interval")
    for name in intervals:
        i = timeline[name]
        start = dateutil.parser.parse(i.get("start"))
        end = dateutil.parser.parse(i.get("end"))

        color = str(i.get("color", "black"))
        if color in named_colors:
            color = named_colors[color]
        elif not _valid_hexcolor(color):
            warn(f"{name} interval color \"{color}\" not a named color or 6-digit hex value, using black")
            color = "#000000"

        xmin = (start - coords.start_date) / (coords.end_date - coords.start_date)
        xmax = (end - coords.start_date) / (coords.end_date - coords.start_date)
        y = i.get("location", 0.5)
        ax.axhline(y=y, color=color, xmin=xmin, xmax=xmax, linewidth=2.0)
        plt.text(start + 0.5 * (end - start),
                 y - coords.annotation_gap,
                 name,
                 fontsize=coords.annotation_fontsize,
                 #weight="bold",
                 horizontalalignment="center")
        note = i.get("note")
        if note is not None:
            plt.text(start + 0.5 * (end - start),
                     y - coords.annotation_gap - coords.note_gap,
                     note,
                     fontsize=coords.note_fontsize,
                     fontstyle="italic",
                     horizontalalignment="center")


def generate(timeline, filename, args):
    top_name = _get_type(timeline, "timeline")[0]
    # check to make sure top_name is unique

    coords = timeline_coords(timeline, top_name)

    fig, ax = setup_plot(timeline, coords, top_name)

    render_numbering(timeline, coords, ax)
    render_events(timeline, coords, ax)
    render_intervals(timeline, coords, ax)

    # write timeline output
    plt.savefig(filename)


def main():
    name = f"Timeline generator (epochs {epochs.__version__})"
    parser = argparse.ArgumentParser(description=name)
    parser.add_argument("-v", "--version",
                        action="version",
                        version=name)
    parser.add_argument("filename", help="YAML input filename")
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("--verbose", help="output warnings", action="store_true")
    args = parser.parse_args()

    timeline = load(args.filename)
    if args.output is None:
        output_filename = os.path.splitext(args.filename)[0] + ".pdf"
    else:
        output_filename = args.output

    if not args.verbose:
        warnings.filterwarnings("ignore")

    generate(timeline, output_filename, args)


if __name__ == "__main__":
    main()
