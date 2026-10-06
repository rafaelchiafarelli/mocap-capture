"""`mocap-capture` command line."""

import argparse

from mocap_capture import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mocap-capture", description=__doc__)
    parser.add_argument("--version", action="version", version=f"mocap-capture {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
