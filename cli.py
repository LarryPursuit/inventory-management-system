"""Entry point: ``pipenv run python cli.py <command>`` (see ``--help``)."""

import sys

from inventory_cli.main import main

if __name__ == "__main__":
    sys.exit(main())
