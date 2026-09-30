#!/usr/bin/env python3
"""Build the download page from the latest release.

Writes a single static index.html (plus the icon) into --out. The page is
regenerated whenever a release is published, so its links always point at the
files of the newest release and nothing has to call the GitHub API at view
time.
"""

import argparse
import datetime
import html
import json
import os
import shutil
import urllib.request

from markdown_it import MarkdownIt

REPO = os.environ.get("GITHUB_REPOSITORY", "ErikKarasek/nexus-grind-releases")
HERE = os.path.dirname(os.path.abspath(__file__))

MONTHS = ["ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince"]


def latest_release():
    req = urllib.request.Request(
        "https://api.github.com/repos/%s/releases/latest" % REPO,
        headers={"Accept": "application/vnd.github+json"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def find(assets, suffix):
    for a in assets:
        if a["name"].endswith(suffix):
            return a
    raise SystemExit("latest release has no asset ending in %s" % suffix)


def size(n):
    return ("%.1f MB" % (n / 1_000_000)).replace(".", ",")


def czech_date(iso):
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    return "%d. %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def render(release):
    assets = release["assets"]
    files = {
        "win": find(assets, "_x64-setup.exe"),
        "msi": find(assets, "_x64_en-US.msi"),
        "mac": find(assets, "-macos.zip"),
    }
    version = release["tag_name"].lstrip("v")
    # Release notes come from our own build, but render them without raw HTML
    # all the same.
    notes = MarkdownIt("commonmark", {"html": False}).render(release.get("body") or "")

    def link(key):
        a = files[key]
        return html.escape(a["browser_download_url"], quote=True)

    def meta(key):
        a = files[key]
        return "%s &middot; %s" % (html.escape(a["name"]), size(a["size"]))

    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as fh:
        page = fh.read()
    values = {
        "VERSION": html.escape(version),
        "DATE": czech_date(release["published_at"]),
        "WIN_URL": link("win"), "WIN_META": meta("win"),
        "MSI_URL": link("msi"), "MSI_META": meta("msi"),
        "MAC_URL": link("mac"), "MAC_META": meta("mac"),
        "NOTES": notes,
        "RELEASE_URL": html.escape(release["html_url"], quote=True),
        "ALL_URL": "https://github.com/%s/releases" % REPO,
    }
    for key, value in values.items():
        page = page.replace("{{%s}}" % key, value)
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_site")
    parser.add_argument("--release-json", help="use this release JSON instead of the API")
    args = parser.parse_args()

    if args.release_json:
        with open(args.release_json, encoding="utf-8") as fh:
            release = json.load(fh)
    else:
        release = latest_release()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render(release))
    shutil.copy(os.path.join(HERE, "icon.png"), os.path.join(args.out, "icon.png"))
    print("built %s for %s" % (os.path.join(args.out, "index.html"), release["tag_name"]))


if __name__ == "__main__":
    main()
