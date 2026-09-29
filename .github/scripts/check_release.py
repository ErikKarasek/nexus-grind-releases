#!/usr/bin/env python3
"""Check that a release here can actually update installed copies of Nexus Grind.

The desktop app asks for
https://github.com/ErikKarasek/nexus-grind-releases/releases/latest/download/latest.json,
follows the URL listed for its platform and refuses the file unless the
signature verifies against the public key compiled into it. Any of those steps
failing leaves every installed copy on its current version without a word, so
this script walks them the way the app does, without credentials.

Writes a Markdown report to --report and a JSON summary to --result. Exits 0
when every check passes, 1 when a check fails, and lets any other error
propagate so that an unreachable API is not reported as a broken release.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REPO = os.environ.get("GITHUB_REPOSITORY", "ErikKarasek/nexus-grind-releases")
API = "https://api.github.com"

# The updater key compiled into the shipped app (read out of the v1.2.0 macOS
# binary). It is public by design; override with UPDATER_PUBKEY if it rotates.
DEFAULT_PUBKEY = (
    "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDI3RjMxQzdBODFBM0Q1RjYK"
    "UldUMjFhT0JlaHp6SjA5S3NUbnBHdDcvbi8vZFpvcDdRNnVGN2JsSFQ5TDdjYjBxVWxheTA5dDIK"
)
DEFAULT_PLATFORMS = "darwin-aarch64,windows-x86_64"

# What the README tells people to download. {v} is the version without the "v".
INSTALLERS = [
    "Nexus.Grind_{v}_x64-setup.exe",
    "Nexus.Grind_{v}_x64_en-US.msi",
    "Nexus-Grind-macos.zip",
]


class Report:
    def __init__(self):
        self.failures = []
        self.passes = []

    def ok(self, text):
        self.passes.append(text)

    def fail(self, check, text, fix):
        self.failures.append({"check": check, "problem": text, "fix": fix})


def api_get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch(url, byte_range=None):
    """Download the way the app does: no credentials, redirects followed.

    Returns (status, body) and never raises on an HTTP error status.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "nexus-grind-release-check"})
    if byte_range:
        req.add_header("Range", "bytes=" + byte_range)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, b""


def parse_version(text):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", text)
    return tuple(int(x) for x in m.groups()) if m else None


def minisign_lines(b64_text):
    return base64.b64decode(b64_text).decode("utf-8").splitlines()


def load_pubkey(b64_text):
    raw = base64.b64decode(minisign_lines(b64_text)[1])
    if len(raw) != 42 or raw[:2] != b"Ed":
        raise ValueError("not a minisign Ed25519 public key")
    return raw[2:10], Ed25519PublicKey.from_public_bytes(raw[10:])


def verify_signature(sig_b64, data, key_id, pubkey):
    """Verify a Tauri updater signature. Returns (error or None, signed file name)."""
    try:
        lines = minisign_lines(sig_b64)
        raw = base64.b64decode(lines[1])
        trusted = lines[2]
        global_sig = base64.b64decode(lines[3])
    except (ValueError, IndexError, UnicodeDecodeError):
        return "the signature is not a base64 minisign signature", None
    if len(raw) != 74 or raw[:2] not in (b"Ed", b"ED"):
        return "the signature has an unknown minisign algorithm", None
    if not trusted.startswith("trusted comment: "):
        return "the signature has no trusted comment", None
    comment = trusted[len("trusted comment: "):]
    signed_name = None
    m = re.search(r"(?:^|\t)file:(.+?)(?:\t|$)", comment)
    if m:
        signed_name = m.group(1)
    if raw[2:10] != key_id:
        return ("signed with key %s, the app trusts %s"
                % (raw[2:10][::-1].hex().upper(), key_id[::-1].hex().upper())), signed_name
    message = hashlib.blake2b(data).digest() if raw[:2] == b"ED" else data
    try:
        pubkey.verify(raw[10:], message)
    except InvalidSignature:
        return "the signature does not match the file", signed_name
    try:
        pubkey.verify(global_sig, raw[10:] + comment.encode("utf-8"))
    except InvalidSignature:
        return "the trusted comment was altered after signing", signed_name
    return None, signed_name


def check(tag, report):
    if tag:
        release = api_get("/repos/%s/releases/tags/%s" % (REPO, tag))
    else:
        release = api_get("/repos/%s/releases/latest" % REPO)
        tag = release["tag_name"]
    version = tag[1:] if tag.startswith("v") else tag
    assets = {a["name"]: a for a in release["assets"]}
    download_base = "https://github.com/%s/releases/download/%s/" % (REPO, tag)

    if release["draft"] or release["prerelease"]:
        report.fail("release-state",
                    "%s is a draft or pre-release; /releases/latest never serves it." % tag,
                    "Publish it as a full release once the assets are in place.")

    if parse_version(version) is None:
        report.fail("tag-format", "Tag %s is not vMAJOR.MINOR.PATCH." % tag,
                    "Tag releases as v1.2.3; the updater compares versions as semver.")

    # The version has to beat the previous release, or installed copies
    # consider themselves current and never ask for this one.
    previous = None
    for r in api_get("/repos/%s/releases?per_page=30" % REPO):
        if r["draft"] or r["prerelease"] or r["tag_name"] == tag:
            continue
        if r["published_at"] and release["published_at"] and r["published_at"] < release["published_at"]:
            previous = r
            break
    if previous:
        prev_v = parse_version(previous["tag_name"].lstrip("v"))
        this_v = parse_version(version)
        if prev_v and this_v and this_v <= prev_v:
            report.fail("version-order",
                        "%s is not newer than the previous release %s." % (tag, previous["tag_name"]),
                        "Bump the version in the private repo before building.")
        else:
            report.ok("Version %s is newer than %s." % (version, previous["tag_name"]))

    for pattern in INSTALLERS:
        name = pattern.format(v=version)
        if name not in assets:
            report.fail("installer-missing", "`%s` is not attached to %s." % (name, tag),
                        "The README links people to this file; upload it or update the README.")
            continue
        status, _ = fetch(download_base + name, byte_range="0-0")
        if status not in (200, 206):
            report.fail("installer-unreachable",
                        "`%s` answers HTTP %d without credentials." % (name, status),
                        "Check that this repository is public and the asset finished uploading.")
        else:
            report.ok("`%s` downloads." % name)

    if "latest.json" not in assets:
        report.fail("manifest-missing", "%s has no `latest.json`." % tag,
                    "Upload the latest.json the build generates; without it no copy updates.")
        return tag

    status, body = fetch(download_base + "latest.json")
    if status != 200:
        report.fail("manifest-unreachable", "`latest.json` answers HTTP %d." % status,
                    "Check that this repository is public.")
        return tag
    try:
        manifest = json.loads(body)
    except ValueError:
        report.fail("manifest-json", "`latest.json` is not valid JSON.",
                    "Regenerate it with the build instead of editing it by hand.")
        return tag

    if manifest.get("version", "").lstrip("v") != version:
        report.fail("manifest-version",
                    "`latest.json` says version %r, the tag is %s." % (manifest.get("version"), tag),
                    "The manifest was generated for another build; regenerate it for this tag.")
    else:
        report.ok("`latest.json` version matches the tag.")

    try:
        datetime.datetime.fromisoformat(manifest.get("pub_date", "").replace("Z", "+00:00"))
    except ValueError:
        report.fail("manifest-date", "`pub_date` %r is not RFC 3339." % manifest.get("pub_date"),
                    "Tauri rejects the whole manifest over a bad pub_date.")

    # This is the exact URL the app polls. It must serve the newest release.
    if not release["prerelease"] and not release["draft"]:
        latest = api_get("/repos/%s/releases/latest" % REPO)
        if latest["tag_name"] == tag:
            status, polled = fetch("https://github.com/%s/releases/latest/download/latest.json" % REPO)
            if status != 200 or polled != body:
                report.fail("endpoint",
                            "The URL the app polls does not serve this release's `latest.json` (HTTP %d)." % status,
                            "Make sure this release is marked Latest.")
            else:
                report.ok("The endpoint the app polls serves this manifest.")

    key_id, pubkey = load_pubkey(os.environ.get("UPDATER_PUBKEY") or DEFAULT_PUBKEY)
    platforms = manifest.get("platforms") or {}
    expected = [p for p in (os.environ.get("EXPECTED_PLATFORMS") or DEFAULT_PLATFORMS).split(",") if p]
    for name in expected:
        if name not in platforms:
            report.fail("platform-missing", "`latest.json` has no `%s` entry." % name,
                        "Copies on %s will never update; add the platform to the build matrix." % name)

    for name, entry in sorted(platforms.items()):
        url = entry.get("url", "")
        sig = entry.get("signature", "")
        if not url.startswith(download_base):
            report.fail("platform-url",
                        "`%s` points to %s, not to this release." % (name, url or "nothing"),
                        "Point it at %s<asset>; other hosts may be private or stale." % download_base)
            continue
        asset_name = url[len(download_base):]
        asset = assets.get(asset_name)
        if not asset:
            report.fail("platform-asset", "`%s` points to `%s`, which is not attached." % (name, asset_name),
                        "Upload the file or regenerate the manifest.")
            continue
        status, data = fetch(url)
        if status != 200:
            report.fail("platform-unreachable", "`%s` answers HTTP %d." % (asset_name, status),
                        "Check that this repository is public.")
            continue
        if len(data) != asset["size"]:
            report.fail("platform-size", "`%s` downloaded as %d bytes, GitHub lists %d."
                        % (asset_name, len(data), asset["size"]),
                        "Re-upload the file.")
            continue
        digest = asset.get("digest") or ""
        if digest.startswith("sha256:") and hashlib.sha256(data).hexdigest() != digest[7:]:
            report.fail("platform-digest", "`%s` does not match GitHub's sha256." % asset_name,
                        "Re-upload the file.")
            continue
        if not sig:
            report.fail("platform-signature", "`%s` has no signature." % name,
                        "The app refuses unsigned updates; sign with the updater key.")
            continue
        error, signed_name = verify_signature(sig, data, key_id, pubkey)
        if error:
            report.fail("platform-signature", "`%s`: %s." % (asset_name, error),
                        "Rebuild with TAURI_SIGNING_PRIVATE_KEY set to the key the app was shipped with.")
            continue
        if signed_name and signed_name.replace(" ", ".") != asset_name:
            report.fail("platform-signature",
                        "`%s` carries a signature made for `%s`." % (asset_name, signed_name),
                        "The manifest pairs a file with another file's signature; regenerate it.")
            continue
        sig_asset = asset_name + ".sig"
        if sig_asset in assets:
            status, sig_body = fetch(download_base + sig_asset)
            if status == 200 and sig_body.decode("utf-8", "replace").strip() != sig.strip():
                report.fail("platform-sigfile",
                            "`%s` differs from the signature in `latest.json`." % sig_asset,
                            "Both come from the same build; one of them is stale.")
                continue
        report.ok("`%s`: `%s` downloads and its signature verifies." % (name, asset_name))

    return tag


def render(tag, report):
    lines = []
    if report.failures:
        lines.append("Release check failed for **%s**: %d problem(s). "
                     "Until they are fixed, installed copies may not update." % (tag, len(report.failures)))
        lines.append("")
        lines.append("## Problems")
        lines.append("")
        for f in report.failures:
            lines.append("- [ ] `%s` %s  " % (f["check"], f["problem"]))
            lines.append("  Fix: %s" % f["fix"])
    else:
        lines.append("Release check passed for **%s**." % tag)
    if report.passes:
        lines.append("")
        lines.append("## Passed")
        lines.append("")
        lines.extend("- %s" % p for p in report.passes)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="release tag to check (default: the latest release)")
    parser.add_argument("--report", help="write the Markdown report here")
    parser.add_argument("--result", help="write a JSON summary here")
    args = parser.parse_args()

    report = Report()
    tag = check(args.tag, report)
    text = render(tag, report)
    sys.stdout.write(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text)
    if args.result:
        with open(args.result, "w", encoding="utf-8") as fh:
            json.dump({"tag": tag, "ok": not report.failures, "failures": report.failures}, fh, indent=2)
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
