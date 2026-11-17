#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update the SearXNG installed by searxng_setup.py, by hand, right now.

    python3 searxng_update.py            update if GitHub has a newer commit
    python3 searxng_update.py --force    reinstall the latest version even if it is the same
    python3 searxng_update.py --check    only say whether an update is available
    python3 searxng_update.py --dir PATH a SearXNG installed into another folder (searxng_setup.py --dir)

The update is the same safe one the daily scheduled job runs: the new version is downloaded while the old one
keeps serving, gets a fresh venv, and must start and answer a test search; otherwise the old version comes back.
Unlike the scheduled job it does not wait a week since the last check.

It also refreshes the copy of searxng_setup.py that the scheduled job runs from the SearXNG folder, so fixes in
this project reach the automatic updates too.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import searxng_setup as setup  # noqa: E402 — next to this script


def main():
    ap = argparse.ArgumentParser(prog="searxng_update.py", description="Update SearXNG for srchplex now.")
    ap.add_argument("--dir", default=setup.default_dir(), help="SearXNG folder (default: %(default)s)")
    ap.add_argument("--force", action="store_true", help="reinstall even if there is no newer commit")
    ap.add_argument("--check", action="store_true", help="only check whether an update is available")
    a = ap.parse_args()
    paths = setup.Paths(a.dir)
    if not paths.installed():
        setup.fail("SearXNG is not installed in %s; install it with: python3 searxng_setup.py" % paths.root)
    if a.check:
        current, latest = setup.installed_commit(paths), setup.latest_commit()
        print("installed: %s" % setup.read_version(paths))
        if latest is None:
            print("cannot reach the GitHub API")
            return 1
        print("update available" if not setup.same_commit(latest, current) else "up to date")
        return 0
    if os.path.exists(paths.setup):  # the scheduled job runs this copy: keep it as new as the project
        setup.install_self(paths)
    return setup.cmd_update(paths, force=a.force)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except setup.SetupError:  # fail() has already printed the error
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
