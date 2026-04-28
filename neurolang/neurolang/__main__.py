"""Allow `python -m neurolang ...` as well as the `neurolang` CLI entry."""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
