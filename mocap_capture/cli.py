"""`mocap-capture` command line."""

import argparse
import sys

from mocap_contracts import TakeType

from mocap_capture import __version__
from mocap_capture.config import ConfigError, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mocap-capture", description=__doc__)
    parser.add_argument("--version", action="version", version=f"mocap-capture {__version__}")
    commands = parser.add_subparsers(dest="command")

    take = commands.add_parser("take", help="record one take from every configured camera")
    take.add_argument("--config", default="config.yaml", help="default: ./config.yaml")
    take.add_argument("--session", required=True)
    take.add_argument("--name", required=True, help="the take id, also its folder name")
    take.add_argument("--type", required=True, choices=["PERFORMANCE", "CALIBRATION"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "take":
        return _take(args)
    parser.print_help()
    return 0


def _take(args: argparse.Namespace) -> int:
    from mocap_capture.take import TakeError, run_take

    try:
        config = load_config(args.config)
        run_take(
            config,
            args.session,
            args.name,
            TakeType.Value(f"TAKE_TYPE_{args.type}"),
            wait_for_end=lambda: input("Recording. Press Enter (or Ctrl+C) to end the take.\n"),
        )
    except (ConfigError, TakeError) as e:
        print(f"mocap-capture take: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("mocap-capture take: interrupted before START, nothing recorded", file=sys.stderr)
        return 130
    return 0
