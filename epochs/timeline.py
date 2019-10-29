# -*- coding: utf-8 -*-

"""Module defining timeline generator.
"""

import argparse
import os

import dateutil.parser
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import yaml


colors = matplotlib.colors.get_named_colors_mapping()


def load(filename):
    with open(filename, "r") as f:
        y = yaml.load(f)
    return(y)


def loads(s):
    return(yaml.load(s))


def _get_type(timeline, typename):
    return [item for item in timeline if timeline[item].get("type") == typename]


def generate(timeline, filename):
    top_name = _get_type(timeline, "timeline")[0]

    annotation_fontsize = 8   # pts
    line_height = 1.5

    start_date = dateutil.parser.parse(timeline[top_name]["start"])
    end_date = dateutil.parser.parse(timeline[top_name]["end"])

    # set up coordinate system
    width = timeline[top_name].get("width", 8.0)
    height = timeline[top_name].get("height", 8.0)
    fig, ax = plt.subplots(figsize=(width, height), constrained_layout=True)

    vgap = line_height * annotation_fontsize / (height * 72)   # 72 pts/inch

    plt.tick_params(labelsize=annotation_fontsize)
    top_ax = ax.twiny()
    plt.tick_params(labelsize=annotation_fontsize)

    ticks = timeline[top_name].get("ticks", "weeks").lower()
    tick_format = timeline[top_name].get("tick-format", "%b %y")

    if ticks == "days":
        major_locator = mdates.DayLocator(interval=1)
        minor_locator = None
    elif ticks == "weeks":
        major_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=4)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    elif ticks == "months":
        major_locator = mdates.MonthLocator(interval=1)
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MONDAY, interval=1)
    else:
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

    ax.set_xlim([start_date, end_date])
    top_ax.set_xlim(ax.get_xlim())

    plt.grid(which="minor", axis="x", linestyle=":")
    plt.grid(which="major", axis="x")

    # set title of timeline
    plt.title(top_name, y=1.05)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)

    # handle events
    events = _get_type(timeline, "event")


    # handle intervals
    events = _get_type(timeline, "interval")
    for name in events:
        e = timeline[name]
        start = dateutil.parser.parse(e.get("start"))
        end = dateutil.parser.parse(e.get("end"))
        color = e.get("color", "black")
        xmin = (start - start_date) / (end_date - start_date)
        xmax = (end - start_date) / (end_date - start_date)
        y = e.get("location", 0.5)
        ax.axhline(y=y, color=colors[color], xmin=xmin, xmax=xmax, linewidth=2.0)
        plt.text(start + 0.5 * (end - start),
                 y - vgap,
                 name,
                 fontsize=annotation_fontsize,
                 #weight="bold",
                 horizontalalignment="center")
        note = e.get("note")
        if note is not None:
            plt.text(start + 0.5 * (end - start),
                     y - 2 * vgap,
                     note,
                     fontsize=annotation_fontsize,
                     fontstyle="italic",
                     horizontalalignment="center")

    # write timeline output
    plt.savefig(filename)


def main():
    name = "Timeline generator"
    parser = argparse.ArgumentParser(description=name)
    parser.add_argument("-v", "--version",
                        action="version",
                        version=name)
    parser.add_argument("filename", help="YAML input filename")
    parser.add_argument("-o", "--output", help="output filename")
    args = parser.parse_args()

    timeline = load(args.filename)
    if args.output is None:
        output_filename = os.path.splitext(args.filename)[0] + ".pdf"
    else:
        output_filename = args.output

    generate(timeline, output_filename)


if __name__ == "__main__":
    main()
