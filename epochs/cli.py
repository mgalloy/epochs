# -*- coding: utf-8 -*-

import argparse
import configparser

import epochs


def main():
    name = f"Epochs utility (epochs {epochs.__version__})"
    parser = argparse.ArgumentParser(description=name)
    parser.add_argument("-v", "--version", action="version", version=name)
    parser.add_argument("filename", help="epochs config filename")
    parser.add_argument("-o", "--option", help="trace the change of an option value")
    parser.add_argument("--verbose", help="output warnings", action="store_true")
    args = parser.parse_args()

    cp = configparser.ConfigParser()
    cp.read(args.filename)

    options = args.option.split(",")

    first_section = True
    use_section = False
    for s in cp.sections():
        for o in options:
            if o in cp.options(s):
                use_section = True
        if use_section:
            if not first_section:
                print()
            else:
                first_section = False
            print(f"[{s}]")
            for o in options:
                if o in cp.options(s):
                    v = cp.get(s, o)
                    print(f"{o}: {v}")
        use_section = False
