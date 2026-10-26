# Accent Theme Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `ezku100/accent-theme` as the single KDE AccentColor/Matugen engine and make `caparazon-shell/install.sh` install it, register the Quickshell template, and leave a validated live palette.

**Architecture:** A dependency-free Python package reads KDE's accent, builds a Matugen config from per-app descriptors, invokes Matugen, parses its JSON, and runs isolated legacy hooks. The engine installs under `~/.local/share/accent-theme/source`, exposes `~/.local/bin/accent-theme`, stores registrations under `~/.config/accent-theme/templates.d`, and runs as `accent-theme.service`; Caparazón owns and registers only its own Quickshell template.

**Tech Stack:** Python 3.11+ standard library, Bash, TOML, JSON, systemd user units, Matugen 4.x, pytest, Ruff, basedpyright.

**Spec:** `docs/superpowers/specs/2026-10-25-accent-theme-design.md`

## Global Constraints

- Respond and document user-facing text in Spanish.
- Do not overwrite `~/.config/matugen/config.toml`; use `~/.config/accent-theme/matugen.toml` via Matugen `-c`.
- Every registered integration has exactly one descriptor in `~/.config/accent-theme/templates.d/`.
- `caparazon-shell` owns `integration/theme/quickshell-matugen.json`; `accent-theme` does not duplicate it.
- Installation must not delete legacy files; migration must leave `kitty-theme-watch.service` disabled but restorable.
- Missing required dependencies or an invalid generated palette must fail visibly.
- All Git commands use `GIT_MASTER=1`; commits are atomic and pushed only after verification.

## Review Focus

- Duplicate app/template names across descriptors must be rejected before Matugen runs.
- A descriptor with a missing template or unsafe output path must not enter the generated config.
- Repeated installation/register must be idempotent and must not duplicate config sections.
- Matugen stdout can contain more than JSON; parsing must isolate the JSON payload safely.
- A changed KDE accent must produce a new palette and must not leave the previous lock held.
- Rollback must work even after the new service is active.

---

### Task 1: Package skeleton and pure color primitives

**Files:**
- Create: `pyproject.toml`
- Create: `src/accent_theme/__init__.py`
- Create: `src/accent_theme/paths.py`
- Create: `src/accent_theme/accent.py`
- Create: `tests/test_accent.py`
- Create: `tests/test_paths.py`

**Interfaces:**
- Produces: `Accent`, `ThemePaths.from_environment(mapping)`, `read_accent(path)`, `accent_to_hex(accent)`, `hsv_to_hex(h,s,v)`, `build_palette(h,s,v)`.

- [ ] Write failing tests for `AccentColor`, selection-background fallback, hexadecimal conversion, and XDG/override paths.
- [ ] Run `uv run pytest tests/test_accent.py tests/test_paths.py -v`; expect import failure.
- [ ] Implement immutable typed dataclasses and pure functions.
- [ ] Run the same tests; expect PASS.

### Task 2: Descriptor registry and generated Matugen config

**Files:**
- Create: `src/accent_theme/registry.py`
- Create: `tests/test_registry.py`

**Interfaces:**
- Consumes: `ThemePaths`.
- Produces: `TemplateRegistration`, `load_registrations(paths)`, `render_matugen_config(registrations)`, `rebuild_config(paths)`.

- [ ] Write failing tests for valid descriptor parsing, duplicate rejection, missing input rejection, generated TOML sections, and idempotent rewrites.
- [ ] Run `uv run pytest tests/test_registry.py -v`; expect import failure.
- [ ] Implement strict descriptor parsing, deterministic TOML rendering, and atomic writes.
- [ ] Run registry tests; expect PASS.

### Task 3: Matugen invocation, JSON parsing, and CLI

**Files:**
- Create: `src/accent_theme/matugen.py`
- Create: `src/accent_theme/cli.py`
- Create: `src/accent_theme/__main__.py`
- Create: `tests/test_matugen.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces: `MatugenTokens`, `find_matugen(environ)`, `parse_matugen_json(text)`, `invoke_matugen(...)`, and CLI commands `generate`, `rebuild-config`, `register`, `doctor`.

- [ ] Write failing tests for Matugen 4.2 role-first JSON, malformed JSON, missing binary, required Quickshell tokens, and registration through the CLI.
- [ ] Run `uv run pytest tests/test_matugen.py tests/test_cli.py -v`; expect import failure.
- [ ] Implement subprocess invocation with timeout and a JSON-object parser that validates required roles.
- [ ] Implement CLI commands with nonzero exit status and actionable Spanish errors.
- [ ] Run task tests; expect PASS.

### Task 4: Hooks, watcher, and live integrations

**Files:**
- Create: `src/accent_theme/hooks.py`
- Create: `src/accent_theme/watcher.py`
- Create: `hooks/active/*.py` migrated from the current legacy hooks.
- Create: `hooks/support/generate_pacman_assets.py`
- Create: `hooks/support/derive_waywallen_accent.py`
- Create: `tests/test_hooks.py`
- Create: `tests/test_watcher.py`

**Interfaces:**
- Consumes: `MatugenTokens` and `MATUGEN_*` environment variables.
- Produces: isolated hook execution, Waywallen fallback handling, and `watch` command for systemd.

- [x] Write failing tests for hook timeout/failure isolation, token environment, and watcher change detection.
- [x] Run hook/watcher tests; expect import failure.
- [x] Migrate active legacy hooks, patch imports away from Kitty-owned modules, and move pacman/Waywallen support files.
- [x] Implement watcher using `inotifywait`, `flock`, and the last-accent cache.
- [x] Run hook/watcher tests; expect PASS.

### Task 5: Templates, descriptors, service, and standalone installer

**Files:**
- Create: `templates/<app>/*` for kitty, ghostty, konsole, kate, cava, heroic, zen, steam.
- Create: `templates.d/*.toml` for the same apps.
- Create: `systemd/accent-theme.service`
- Create: `install.sh`
- Create: `README.md`
- Create: `LICENSE`
- Create: `tests/test_install_contract.py`

**Interfaces:**
- Produces: `install.sh [instalar|desinstalar]`, `~/.local/bin/accent-theme`, `accent-theme.service`, base registrations, and legacy rollback.

- [ ] Write failing contract tests for service name/path, base descriptors, template parity, and install/uninstall actions.
- [ ] Run the contract test; expect missing files.
- [ ] Copy and validate the eight Matugen templates; create one descriptor per template.
- [ ] Implement idempotent installation, dependency detection, service migration, generation, and uninstall rollback.
- [ ] Run contract tests; expect PASS.

### Task 6: Caparazón template and bootstrap installer

**Files:**
- Create in `../caparazon-shell`: `integration/theme/quickshell-matugen.json`
- Create in `../caparazon-shell`: `integration/theme/accent-theme.toml`
- Modify in `../caparazon-shell`: `install.sh`
- Modify in `../caparazon-shell`: `theme/MatugenPalette.qml`
- Modify in `../caparazon-shell`: `README.md`
- Create in `../caparazon-shell`: `tests/test_theme_install_contract.py`

**Interfaces:**
- Consumes: `accent-theme register --app caparazon-shell --descriptor <path>`.
- Produces: a complete Caparazón install with validated `~/.cache/caparazon/colors.json`.

- [ ] Write failing contract tests for the owned template, descriptor, bootstrap URL, validation keys, and visible file-read errors.
- [ ] Run the contract test; expect missing integration files.
- [ ] Add the Quickshell template/descriptor and wire clone/pull, dependency checks, registration, generation, and validation into `install.sh`.
- [ ] Change `printErrors` to `true` while retaining the fallback palette.
- [ ] Run the contract test; expect PASS.

### Task 7: Verification, migration, and publication

**Files:**
- Modify: `docs/superpowers/plans/2026-10-25-accent-theme.md` (mark completed steps).
- Modify: `README.md` and `install.sh` if verification reveals defects.

**Interfaces:**
- Produces: clean Git histories, a public `accent-theme` repository, updated Caparazón remote, and a running migrated service.

- [ ] Run `uv run ruff check .`, `uv run basedpyright`, and `uv run pytest`; expect all green.
- [ ] Run shell syntax checks and isolated smoke installs under temporary HOME directories.
- [ ] Back up active theme config/service files with timestamps.
- [ ] Install the local engine, register Caparazón, disable the legacy service, enable/start `accent-theme.service`, and regenerate the palette.
- [ ] Verify `systemctl --user is-active/is-enabled accent-theme.service`, `accent-theme doctor`, `colors.json`, `systemctl --failed`, and a deliberate accent-change smoke test with rollback of the accent value.
- [ ] Inspect Git status/diff/log in both repos; create atomic commits and push them.
- [ ] Create the public `ezku100/accent-theme` GitHub repository and verify both remote URLs and default branches.
