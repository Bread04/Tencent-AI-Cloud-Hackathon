# Restored BMad workflow loader

This directory restores the loader required by the installed `bmad-build` and `bmad-build-auto` skills, plus the configuration, customization and memory-log helpers used by `bmad-brainstorming`. It prepares skill instructions and session records; the ride-hailing prototype runs independently.

## Source and compatibility

`scripts/render_skill.py`, `scripts/config_utils.py`, `scripts/resolve_config.py`, `scripts/resolve_customization.py` and `scripts/memlog.py` are unmodified copies from the official [BMAD-METHOD v6.12.0 release](https://github.com/bmad-code-org/BMAD-METHOD/tree/05bfbd46d00766ec88eb9b42e76be2c575d64d7b), commit `05bfbd46d00766ec88eb9b42e76be2c575d64d7b`. The installed build workflow matched that release's workflow exactly after normalizing line endings. Original source URLs and file SHA-256 hashes, including the upstream tests for the three restored helpers, are recorded in [upstream.json](upstream.json); the upstream MIT license is preserved in [LICENSE](LICENSE).

Python 3.11 or newer is required. These scripts use only the standard library. Installed skills remain in their existing directory; the loader reads them without editing them.

## Settings

- [config.toml](config.toml) contains shared project paths and usable defaults: English, intermediate development experience, and the fallback display name BMad.
- `config.user.toml` contains the approved local settings: Kyven, English, and intermediate development experience. This personal file is ignored by Git. On another checkout, the shared defaults work immediately; create this optional file to personalize them:

```toml
[core]
user_name = "Kyven"
communication_language = "English"

[modules.bmm]
user_skill_level = "intermediate"
```

Generated planning and implementation artifacts go under `_bmad-output/planning-artifacts` and `_bmad-output/implementation-artifacts`. Existing project knowledge remains in `docs`. These artifact directories are created when a workflow writes to them.

The renderer merges central configuration in this order: `config.toml`, `config.user.toml`, `custom/config.toml`, `custom/config.user.toml`. Skill customization merges installed `customize.toml`, then `custom/<skill-name>.toml`, then `custom/<skill-name>.user.toml`. Later scalars override; tables merge; ordinary arrays append; table arrays with `code` or `id` replace matching entries and append new ones.

## Run

From the repository root in PowerShell:

```powershell
uv run --no-cache "_bmad/scripts/render_skill.py" --project-root "." --skill "$env:USERPROFILE/.agents/skills/bmad-build"
```

To check the other rendered workflow, replace the final skill name with `bmad-build-auto`. For a different installation location, pass its actual skill directory.

Success prints one `read and follow <absolute path>/workflow.md` instruction. Rendering alone does not execute that workflow. The calling assistant reads the generated entry and follows it when the user invokes the skill.

The loader resolves configuration/customization tokens and cross-file snapshot references. It writes an immutable generation under `_bmad/render/`, with a manifest of source, configuration and output hashes. Repeated identical inputs reuse a verified generation; changed inputs create a new one. Generated snapshots are ignored by Git.

Missing or malformed configuration, missing workflow files, invalid references, and modified snapshots produce `HALT:` with a nonzero exit code. Configure each short key such as `communication_language` in only one namespace: this upstream version rejects ambiguous keys across modules. If a snapshot is reported as corrupt, inspect the exact generation named in the error and remove only that generated directory before rendering again.

The brainstorming helpers can also be called directly from the repository root:

```powershell
uv run _bmad/scripts/resolve_config.py --project-root . --key core
uv run _bmad/scripts/resolve_customization.py --skill "$env:USERPROFILE/.agents/skills/bmad-brainstorming" --key workflow
uv run _bmad/scripts/memlog.py init --workspace _bmad-output/brainstorming/example --field topic="Example"
```

The resolvers print JSON and share the renderer's existing TOML merge rules. The memory log supports `init`, `append` and `set`; writes replace the file atomically. Initialization refuses to overwrite an existing log. Use a new workspace for each session.

This remains a scoped setup, not a complete BMad installation. Skills that require `_bmad/bmm/config.yaml` still need their own setup files. The installed brainstorming skill is read from the supplied skill path and is not copied or modified here.

## Verification

```powershell
python -B -m unittest discover -s "_bmad/scripts/tests" -v
uv run --locked pytest -q tests _bmad/scripts/tests
```

The unittest command covers the renderer and configuration resolvers. The pytest command additionally includes memory-log checks and the backend suite. Tests use isolated fixtures and cover rendering, customization precedence, snapshot reuse, source changes, corruption detection, missing/invalid/ambiguous configuration, invalid file references, Windows Unicode output, append-only session entries and command-line execution from another working directory. Once project dependencies are installed, the tests require no installed BMad skill or network access.
