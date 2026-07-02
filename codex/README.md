# Codex Version Setup

This folder contains the OpenAI Codex version of Theorist Toolbox.

Copy this folder's hidden configuration directories into a repository where you want to use the toolbox:

```bash
cp -R .agents /path/to/repo/
cp -R .codex /path/to/repo/
```

Then start Codex from that repository. If skills or agents do not appear immediately, restart the Codex session.

## First Run

To start a project, ask:

```text
Use $co-math-init to initialize a strict co-math project for: <research question>
```

To check status later, ask:

```text
Use $co-math-status.
```

To use the team workflow, ask Codex explicitly to spawn or use one of the custom agents, for example:

```text
Use the co-math-project-coordinator agent to resume this project and propose the next workstreams.
```

Codex only spawns subagents when explicitly asked, so the coordinator skill and agent files are written to work in both single-agent and multi-agent settings.
