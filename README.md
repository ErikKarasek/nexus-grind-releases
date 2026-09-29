# Nexus Grind — downloads

Installers for [Nexus Grind](https://github.com/ErikKarasek/nexus-grind), and the
manifest the desktop app reads to find updates.

There is no source code here. The application is developed in a private
repository; this one exists because a private repository cannot hand out files
publicly — its release assets are private too, so an installed copy of the app
could never reach them.

## Download

Take the newest version from [Releases](../../releases/latest):

| File | For |
| --- | --- |
| `Nexus.Grind_<version>_x64-setup.exe` | Windows — the usual choice |
| `Nexus.Grind_<version>_x64_en-US.msi` | Windows, for managed installs |
| `Nexus-Grind-macos.zip` | macOS, Apple silicon |

The remaining files — `.app.tar.gz`, the `.sig` signatures and `latest.json` —
are what the app uses to update itself. You do not need to download them.

## What the warnings mean

The builds are not yet signed with a Developer ID certificate, so **macOS will
say the developer cannot be verified** and **Windows SmartScreen will warn about
an unrecognised app**. That is the state of the signing paperwork, not a
statement about the file.

On macOS: right-click the app → Open, then confirm. Opening it by double-click
the first time will only offer to move it to the Bin.

Updates are a different signature, and that one is already in place — the app
refuses any update not signed by the project's key, whatever this page says.

## Releases

Published by the build in the private repository. Nothing here is edited by hand.

## Release check

`.github/workflows/release-check.yml` runs when a release is published or
edited, every Monday, and on demand. It downloads `latest.json` from the URL the
app polls, fetches the file listed for each platform without credentials, and
verifies its signature against the updater key compiled into the shipped app.
It also checks that the installers named above are attached and that the
version is newer than the previous release.

While anything fails, one issue labelled `release-check` stays open with the
list of problems; the next passing run closes it. If the updater key ever
changes, set the repository variable `UPDATER_PUBKEY` to the new public key.

## Agents

`paperclip/nexus-grind-ops` is a Paperclip company package: a Watcher that
runs this check and reads CI in the private repository every week, a
Dispatcher that keeps a status board, and a Fixer that opens pull requests.
Its README has the setup.

## Download page

`site/` builds a one-page download site from the latest release, and
`.github/workflows/pages.yml` deploys it to GitHub Pages whenever a release is
published. It picks the installer for the visitor's system and shows the
release notes. Pages has to be enabled once under Settings, Pages, with
GitHub Actions as the source.
