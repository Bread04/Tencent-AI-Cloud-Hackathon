"""Rehearse the Demo Day walkthrough: run every step of `docs/demo-script.md` in order and check how each ends.

    uv run python -m scripts.rehearse

It always runs on the scripted replies, whatever `.env` says: the script's stated outcomes are the scripted ones, and
a rehearsal must not depend on the network. The exit code is 0 when every step ends as scripted and 1 otherwise.
"""

import sys

from src.api.demo import ReplayModel
from src.api.walkthrough import rehearse, render
from src.intake import load_catalog


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # the Windows console codepage cannot print every character
    results = rehearse(catalog=load_catalog(), model_for=ReplayModel)
    print(render(results))
    return 1 if any(result.problems for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
