#!/usr/bin/env python3
"""
__main__.py
=====================================
The main-file of testbedimage
"""

import sys
import logging
from rich.logging import RichHandler
from .cli import cli

FORMAT = "%(message)s"
logging.basicConfig(
    level="CRITICAL", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


def main():
    args = cli.parse_args()
    if args.subcommand is None:
        cli.print_help()
    else:
        args.func(args)

    sys.exit(1)


if __name__ == '__main__':
    main()
