# Nexus Grind Ops

A [Paperclip](https://github.com/paperclipai/paperclip) company package with
three agents that look after Nexus Grind between releases.

| Agent | Reports to | Wakes when | Does |
| --- | --- | --- | --- |
| Watcher | Dispatcher | Mondays 08:05 Europe/Prague, or run by hand | Runs the release check, reads CI, keep-alive and release runs, open `bug` issues. Files one Paperclip issue per problem. Read-only. |
| Dispatcher | nobody | A finding or a Fixer result is assigned to it | Sorts each finding into "Fixer", "only Erik" or "not a problem", and keeps the pinned status board issue in `nexus-grind` current. |
| Fixer | Dispatcher | The Dispatcher assigns it a problem | Reproduces, fixes, runs lint, tests and both typechecks, opens a PR against `nexus-grind`. Never merges. |

The shared skill `skills/nexus-grind-context` holds the repository facts and
the list of actions reserved for Erik (merging, tags, releases, secrets,
Supabase, repository settings). Every agent loads it.

## Setup

The quickest way is the start script next to this folder:
`paperclip/start-windows.bat` (double-click) or `paperclip/start-mac.command`
(run with `bash start-mac.command`). It installs Node.js and Claude Code when
they are missing, starts Paperclip, imports this package once and opens the
board. The manual steps below do the same.

1. Install and start Paperclip on the machine that will run the agents. It
   needs Node.js 24.11 or newer and a logged-in Claude Code CLI (`claude`).

   ```sh
   npx paperclipai onboard --yes
   ```

2. Import this folder, either in the UI (Company settings, Import) or:

   ```sh
   npx paperclipai company import ErikKarasek/nexus-grind-releases/paperclip/nexus-grind-ops --ref main
   ```

   The preview warns that the agents reference a `paperclip` skill missing
   from the package. That is Paperclip's own bundled skill; it resolves on
   import. Agents and the routine arrive paused.

3. Create three fine-grained GitHub tokens and set each as the agent's
   `GH_TOKEN` secret:

   - Watcher: `nexus-grind` and `nexus-grind-releases`, read-only Actions,
     Contents, Issues and Metadata.
   - Dispatcher: `nexus-grind` only, Issues read and write.
   - Fixer: `nexus-grind` only, Contents and Pull requests read and write,
     Actions read.

   A Contents write token can push to `main` directly. Protect `main` with a
   rule that requires a pull request before the Fixer runs, so its "never push
   to main" instruction is enforced by GitHub as well.

4. Open each agent, press Test Environment, then resume the agents and the
   `Weekly sweep` routine. Run the routine once by hand to see a first sweep.

## Where to look

The status board is the pinned issue `Status: what is broken right now` in
`nexus-grind`. Paperclip's own board shows the same findings with their
history. If Status Cards are enabled under Instance Settings, Experimental, a
card watching the `Nexus Grind health` project gives a short summary there as
well.

## Costs

Monthly budgets are set to $5 for the Watcher and Dispatcher (Sonnet) and $30
for the Fixer (Opus). Paperclip pauses an agent that reaches its budget.
Change them in `.paperclip.yaml` before import or in the UI afterwards.
