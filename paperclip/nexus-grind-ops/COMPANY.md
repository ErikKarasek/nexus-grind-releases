---
name: Nexus Grind Ops
description: Three agents that find what is broken around Nexus Grind, show it in one place and fix what code can fix
slug: nexus-grind-ops
schema: agentcompanies/v1
version: 0.1.0
license: MIT
authors:
  - name: Erik Karásek
goals:
  - Installed copies of Nexus Grind keep updating and syncing
  - Anything broken is visible within a week, with a named next step
---

Nexus Grind is a habit and task tracker with a Tauri desktop app, an Expo mobile
app and Supabase sync. The code lives in the private repository
`ErikKarasek/nexus-grind`; installers and the update manifest live in the public
repository `ErikKarasek/nexus-grind-releases`.

The Watcher sweeps both repositories once a week and files every problem it
finds as an issue for the Dispatcher. The Dispatcher decides what each one
needs, keeps the status board current, and hands code problems to the Fixer.
The Fixer opens pull requests. Nobody here merges, tags, publishes a release or
touches a secret: those stay with Erik.
