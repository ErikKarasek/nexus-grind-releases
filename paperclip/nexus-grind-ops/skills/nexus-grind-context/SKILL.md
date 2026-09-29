---
name: nexus-grind-context
description: Facts about the Nexus Grind repositories, workflows and release path, and which actions are reserved for the human owner. Load before touching either repository.
---

# Nexus Grind context

## Repositories

- `ErikKarasek/nexus-grind` (private): all source. pnpm workspace, Node 22.
  `apps/desktop` is the Tauri app, `apps/mobile` the Expo app,
  `packages/domain` the shared logic, `supabase/` the migrations.
- `ErikKarasek/nexus-grind-releases` (public): installers, `latest.json`, and
  `.github/scripts/check_release.py`. No source code. Anything written here is
  public, so never put details from the private repository in it.

## Workflows in nexus-grind

- `ci.yml` on every push to `main` and every PR. The `test` job runs, in order:
  `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm test`,
  `pnpm --filter @nexus-grind/desktop exec tsc --noEmit`,
  `pnpm --filter @nexus-grind/mobile exec tsc --noEmit`.
  The Windows, macOS, Android and iOS build jobs run only on `main`; iOS is
  `continue-on-error` and its failure alone is not a finding.
- `keepalive.yml` twice a day (06:17 and 18:43 UTC) runs
  `node scripts/supabase-keepalive.mjs`. A failed run usually means the free
  Supabase project is paused, and every shipped build then fails to sync. No
  run for more than 36 hours means GitHub disabled the schedule (it does that
  after 60 days without commits).
- `release.yml` on a `v*` tag builds, signs and uploads a **draft** release to
  the releases repository together with `latest.json`. Erik publishes the draft
  by hand.

## The update path

Installed desktop copies poll
`https://github.com/ErikKarasek/nexus-grind-releases/releases/latest/download/latest.json`
and refuse any file whose minisign signature does not verify against the key
compiled into the app. `check_release.py` walks exactly that path:

```sh
pip install cryptography
python .github/scripts/check_release.py            # latest release
python .github/scripts/check_release.py --tag v1.2.0
```

Exit 0 is healthy, 1 lists problems, anything else is the script or GitHub
failing and is not a finding. In the releases repository the
`Release check` workflow keeps one issue labelled `release-check` open while
the check fails.

## Reserved for Erik

Never do these, and never ask an agent to. File them as blocked with exact
steps for Erik instead:

- merging a PR, pushing to `main`, creating or deleting a tag
- publishing, editing or deleting a release or a release asset
- anything involving secrets: `TAURI_SIGNING_PRIVATE_KEY`, `RELEASES_TOKEN`,
  Apple credentials, Supabase keys
- the Supabase dashboard: restoring a paused project, running migrations
- re-enabling a disabled workflow, changing repository settings or visibility
- App Store, Play Console, EAS
