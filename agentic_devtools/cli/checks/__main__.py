"""Allow running checks via: python -m agentic_devtools.cli.checks [--format-fix]"""

import sys

from agentic_devtools.cli.checks.commands import main

if __name__ == "__main__":
    sys.exit(main())
