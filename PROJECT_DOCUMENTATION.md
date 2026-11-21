# Amanuensis — project documentation

Amanuensis helps a coding agent investigate a project and maintain a complete
user/developer handoff in one Markdown document, supported by evidence files.

Reviewed **2026-11-21**, at **standard** depth, on Windows 11 with Python 3.13.5.
Repository: [JaiReyes45/amanuensis](https://github.com/JaiReyes45/amanuensis)
(private). Publication checkout: documentation branch `codex/project-documentation`,
based on source commit `95bfc2249d6557549e1fccbdcd1b015bead8c2c1` on `main`.
The root README also gains a documentation link in this change. The exact reviewed
working-tree fingerprint is recorded in the linked manifest and evidence index.
The original authoring directory resolves to an unrelated `C:/` Git ancestor;
publication uses a separate, verified checkout of this GitHub repository.

Verified: source inspection, all 13 automated tests, and a disposable
scan → validate → checkpoint → change → rescan demonstration. There is no product
web interface; actual CLI transcripts provide the walkthrough. Cross-platform
execution and token savings were not verified in this run. Source publication to
GitHub was verified; the documentation is delivered separately for PR review.

Contents: [Overview](#overview) · [Architecture](#architecture) ·
[Repository map](#repository-map) · [Setup](#setup-and-configuration) ·
[Operation](#operation-and-deployment) · [Workflows](#features-and-workflows) ·
[Walkthrough](#visual-walkthrough) · [Demo](#demo) ·
[User handoff](#user-handoff) · [Developer handoff](#developer-handoff) ·
[Troubleshooting](#troubleshooting-and-limitations) · [Evidence](#evidence-and-freshness)

## Overview

The original [concept note](<The scriber and clerk you are looking for..md>) asks
for architecture, screenshots, descriptions, instructions, demo, and handoff from
one invocation. The implemented first version combines reusable agent guidance
with a deterministic Python utility. The agent understands and explains the
project; the utility inventories files and enforces a documentation checkpoint.

Intended users are project owners requesting a handoff and maintainers keeping it
current. Apps, websites, workflows, and other inspectable projects can be covered.
Node/Python package metadata has dedicated extraction; other stacks require agent
inspection. Browser/computer access, authenticated GitHub access, and model
execution come from the host. There is no bundled server, GitHub App, hosted
service, continuous integration workflow, or model API client.

The implementation is an initial working skill with automated behavioral tests.
Its design reduces repeated discovery through bounded summaries and fingerprints;
equivalent-quality token savings have not been measured.

## Architecture

```text
User + host agent
  |
  +--> SKILL.md --> relevant reference guidance
  |
  +--> Python CLI --scan--> explicit project directory
  |         |                    |
  |         |              hashes + selected metadata
  |         v
  |    .amanuensis/project-manifest.json
  |         |
  +--> targeted investigation + host execution/capture tools
            |
            +--> PROJECT_DOCUMENTATION.md + docs/amanuensis/ assets
            +--> .amanuensis/evidence-index.json
                         |
                  validate + checkpoint
                         |
                  .amanuensis/state.json
```

This diagram describes code and instruction relationships observed in
[the CLI](scripts/amanuensis.py) and [the skill](SKILL.md); host actions are
instructions to an agent, not functions implemented by the CLI.

`main()` dispatches three commands. `collect()` walks only the resolved root,
applies exclusions, streams SHA-256 hashes, and extracts safe metadata.
`git_info()` accepts a commit only when Git's root exactly matches the supplied
directory. `scan()` compares hashes against the last checkpoint, writes a fresh
manifest, and suggests evidence needing review. Its JSON stdout is bounded to
12,000 characters; the full inventory remains on disk.

`validate()` checks the canonical headings, evidence coverage and fields, and
local link targets. `checkpoint()` validates, rescans, rejects changed/incomplete
inputs, requires the current fingerprint on observed evidence, and writes state.
Scanning alone never advances that baseline. State stores the source hashes,
Git metadata, timestamp, gap IDs, and document/evidence checksums. File writes use
a temporary state file followed by replacement; there is no transaction spanning
all outputs and no concurrent-run locking.

No application database or external API is involved. JSON and media persist in
the target project. The scanner invokes Git for local metadata only. A host agent
may use external tools when separately available and authorized.

## Repository map

| Path | Responsibility |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent entry point, depth selection, investigation and delivery workflow. |
| [README.md](README.md) | GitHub landing page linking to this handoff. |
| [agents/openai.yaml](agents/openai.yaml) | Codex display metadata and example invocation. |
| [scripts/amanuensis.py](scripts/amanuensis.py) | Standard-library scan, validation, and checkpoint commands. |
| [references/documentation.md](references/documentation.md) | Twelve-section output contract and editorial expectations. |
| [references/evidence.md](references/evidence.md) | Evidence status, provenance, and reuse rules. |
| [references/scanner.md](references/scanner.md) | Limits, exclusions, operation, and installation notes. |
| [tests/test_amanuensis.py](tests/test_amanuensis.py) | Disposable-fixture behavioral tests. |
| [CLI demo](docs/amanuensis/demos/cli-demo.py) | Repeatable demonstration of the utility's lifecycle. |
| [Evidence index](.amanuensis/evidence-index.json) | Claims, observations, checks, and limitations for this handoff. |

The root document, `.amanuensis/`, and `docs/amanuensis/` are excluded from source
fingerprinting. The latter contains documentation assets, not product source.

## Setup and configuration

Required: Python **3.11+** for the CLI, an agent supporting skills for autonomous
documentation, and a readable/writable explicit project directory. Git is
optional for scanning but required for Git publication and the full test suite.
The CLI uses only the Python standard library; there is no dependency installation
or environment variable required by Amanuensis itself.

From this project's directory, these commands were executed successfully:

```powershell
python scripts/amanuensis.py scan --root .
python -m unittest discover -s tests -v
python docs/amanuensis/demos/cli-demo.py
```

For another target, use the installed script's absolute path and quote paths
containing spaces. Install the skill by copying `SKILL.md`, `agents/`, `scripts/`,
and `references/` together to your host's skills directory. In this environment
the installed location is `%USERPROFILE%\.codex\skills\amanuensis`. Keep that
installation separate from the target being documented. Installation was already
performed in the preceding build task; this documentation run did not reinstall it.

Optional project configuration is `.amanuensisignore`, one relative glob per line:

```text
private/
*.sqlite
```

Comments start with `#`; negation and full Git-ignore semantics are unsupported.
`.gitignore` is not interpreted. Default scan limits are 20,000 files and 128 MiB
total hashed bytes; use `--max-files` and `--max-bytes` to increase them deliberately.
Metadata extraction is skipped above 1 MiB even when a file is hashed.

## Operation and deployment

The normal operational cycle is:

1. Scan the explicit project; review warnings and selected manifest facts.
2. Investigate source and runtime behavior; write/update the handoff and evidence.
3. Validate and review local links, rendered output, and media where available.
4. Checkpoint only after reconciling evidence with the current source fingerprint.

```powershell
python scripts/amanuensis.py validate --root .
python scripts/amanuensis.py checkpoint --root .
```

These operate on this project when run from its root. Scanning writes the manifest;
validation checks without advancing state; checkpoint writes the baseline. Expected
success is exit status 0. Failures print a diagnostic and return nonzero. A saved
checkpoint can contain explicit gaps, so it is not an assertion that all checks pass.

There is no build or deployment service. Distribution consists of the skill folder.
When editing the source copy, update and verify the installed copy separately.
For recovery, preserve or restore the document, evidence, assets, and state as a
consistent set, then rescan and reconcile. Restoring old JSON does not reverify a
changed runtime. Concurrent writers to one target are not supported.

The source [.gitignore](.gitignore) currently ignores `.amanuensis/`. Consequently
the index, manifest, and baseline will not be included by a normal Git add. A
maintainer must deliberately decide to version reviewed, nonsensitive state (or
accept rediscovery on another machine). This documentation PR explicitly includes
the reviewed evidence index, manifest, and baseline using exact forced-add paths;
ignore policy remains unchanged. No files from the unrelated ancestor repository
are included.

## Features and workflows

| Workflow | Input and behavior | Output or limitation |
| --- | --- | --- |
| First handoff | User invokes the skill; agent scans, traces architecture, exercises workflows, and writes twelve sections. | Root Markdown document, supporting assets, evidence, checkpoint. |
| Incremental update | Scanner compares current file hashes with checkpoint hashes, including additions/deletions. Agent traces dependent claims. | Suggested reviews and edited sections; no automatic prose generation inside the CLI. |
| Package inventory | Nested package.json and pyproject.toml files are examined. | Dependency and script names; command bodies and credential values are not emitted. |
| Configuration inventory | Safe `.env` templates are inspected. | Variable names only; actual `.env*` files excluded. |
| Evidence review | Source/runtime observations include provenance and current fingerprint. | Stale evidence is reviewed or explicitly marked unavailable. |
| GitHub delivery | Host resolves an appropriate checkout, remote, branch, and access. | Documentation branch/PR when requested and authorized; no built-in publisher. |

Depth is an agent instruction: `quick` omits runtime work explicitly, `standard`
covers representative workflows, and `release` asks for broader role/failure-path
coverage. These are not CLI flags. No background schedule or automatic retry loop
is implemented. Operational ownership remains with the invoking project maintainer.

## Visual walkthrough

The product's executable surface is a CLI. The [actual demo transcript](docs/amanuensis/evidence/cli-demo.txt)
provides execution evidence in place of screenshots of a nonexistent web UI.

1. **Inventory.** Initial scan of a disposable two-file JavaScript fixture reported
   `complete: true`, two added files, dependency `example-library`, and script name
   `start`. Its actual start command was never executed.
2. **Document contract.** The demo supplied all twelve headings and evidence records.
   Validation returned:

   ```text
   Documentation structure, evidence records, and local link targets passed. Content accuracy requires agent review.
   ```

3. **Baseline.** Checkpoint saved with eleven intentionally unavailable fixture
   sections. This demonstrates gap handling, not a complete project investigation.
4. **Change detection.** After editing `index.js`, rescan reported one modified file,
   an existing baseline, and the architecture evidence among the review IDs:

   ```text
   PASS: source modification detected and architecture evidence marked for review.
   Temporary fixture cleaned up; no project code was executed.
   ```

The [test transcript](docs/amanuensis/evidence/tests.txt) records all 13 tests
passing. These are text observations, not screenshots or video recordings.

## Demo

Run the [disposable CLI demo](docs/amanuensis/demos/cli-demo.py) from this directory:

```powershell
python docs/amanuensis/demos/cli-demo.py
```

Prerequisites are Python and readable project sources. The script creates a
temporary two-file fixture, scans it, writes an explicitly synthetic document and
evidence, validates, checkpoints, changes one source file, and rescans. Assertions
require `index.js` to be the sole modified path and its architecture evidence to
need review. It prints commands with the temporary root normalized to a placeholder.
`TemporaryDirectory` removes the fixture on exit, including ordinary exceptions;
no reset of the real project is needed.

This demo was executed successfully on 2026-11-21; the linked transcript contains
the real output. It demonstrates utility integration and does not claim that a
model autonomously documented another application or exercised a JavaScript app.
A video recording is inapplicable to this text-only demonstration and was not made.

## User handoff

In a skill-capable Codex session, select the target checkout and request:

```text
Use $amanuensis to document this repository at standard depth.
```

Provide an exact directory or verified repository link when the target is ambiguous.
Give the agent the access its investigation requires; secrets should remain in the
host's normal credential/configuration mechanism. Review the finished root document,
captured evidence, test outcomes, and gaps. A missing credential or unavailable
browser should result in a visible limitation rather than invented proof.

For subsequent changes, invoke the same skill and request an update. Retaining the
checkpoint and evidence across sessions enables comparisons. Before relying on an
old screenshot or test, review runtime changes outside Git as well as source changes.
No support service or named escalation owner is configured; the project maintainer
owns access, documentation review, and any decision to publish.

## Developer handoff

Start with `SECTIONS`, `collect()`, `scan()`, `validate()`, and `checkpoint()` in
[scripts/amanuensis.py](scripts/amanuensis.py). Agent instructions live separately
in the skill and references. Changing the document contract requires keeping the
heading list, reference contract, and fixtures consistent. New ecosystem parsers
belong in targeted extraction; architecture inference remains agent work.

The [unittest suite](tests/test_amanuensis.py) creates disposable fixtures and
launches the CLI. Its 13 tests cover scoped Git handling, exclusion of sensitive
files, compact summaries, custom exclusions, baseline preservation, add/modify/delete
tracking, stale-source rejection, evidence freshness, missing media/path escapes,
incomplete scans, symlinks, parenthesized Markdown links, reparse-point detection,
timestamp validation, and disappearing entries. Some checks share one test.

No application network service or project package command is executed by these
tests. Git init is used only in a temporary fixture. The successful run was on
Python 3.13.5/Windows 11; Python 3.11 and other operating systems were not executed.

Potential next work: benchmark comparable documentation runs; exercise a real
frontend/API repository; add stricter JSON schema checks and more Markdown cases;
evaluate concurrent writes and cross-platform behavior; decide how state should
be versioned; add a GitHub integration only when its requirements are established.
These are proposals, not implemented or verified capabilities.

## Troubleshooting and limitations

| Symptom | Cause or constraint | Action |
| --- | --- | --- |
| Git reports an ancestor | Target is not the actual repository root. | Use a verified checkout for publication; retain filesystem scanning meanwhile. |
| Scan is incomplete | Limit reached, read failure, or invalid inspected metadata. | Review manifest warnings, narrow scope/fix access or raise limits, and rescan. |
| Checkpoint says source changed | Inputs changed after scan. | Rescan, reconcile affected claims, and review evidence before checkpointing. |
| Observed evidence rejected | Missing/invalid timestamp, source, procedure, or current fingerprint. | Supply actual provenance; do not stamp unreviewed evidence as fresh. |
| Missing linked file | Deleted or incorrect asset/source target. | Restore/correct it or revise the documentation and gap record. |
| Runtime cannot launch | Host tools, service access, or credentials unavailable. | Finish accessible investigation and explain the remaining prerequisite. |
| State absent on another checkout | `.amanuensis/` ignored or not distributed. | Deliberately distribute reviewed state or perform a fresh investigation. |

Exclusions are heuristic, not a complete secret detector. The scanner hashes
included files and stores their paths; metadata exports dependency/script names
and environment names, not values. Review sensitive custom paths before scanning.
The utility does not parse full Markdown semantics, validate anchors/remote URLs,
prove prose truth, or build a complete dependency graph. Evidence fingerprints
are a review gate, not cryptographic proof that an action actually happened.

The initial sandbox process launcher failed during this session; execution resumed
with the permitted host process runner. That is an environment observation, not
a failure of the Amanuensis test suite. Source publication was later verified in
the dedicated GitHub checkout. Screenshots of a real application and measured
token savings remain outside the verified scope.

## Evidence and freshness

The machine-readable [evidence index](.amanuensis/evidence-index.json) maps each
section to source observations or runtime artifacts. The
[manifest](.amanuensis/project-manifest.json) contains the scoped input hashes.
After successful final validation, `.amanuensis/state.json` records the
documented baseline and explicit gaps. All review timestamps are UTC.

Observed evidence includes the two transcripts and the inspected implementation.
The publication scan contains ten source files, including GitHub's README;
documentation assets and generated state are excluded by design. The inspected
source commit is recorded above, with README edits included in the fingerprint. A future
source change requires review of dependent claims, not wholesale reuse based on
the date or filename alone.

Open verification gaps: Python 3.11/non-Windows execution; an external application
investigation; and measured token efficiency. Documentation delivery is via PR. A browser-rendered
preview was not available in this run; the Markdown structure, links, and text
transcripts were reviewed directly. No unsupported claim of rendered visual QA
or fabricated screenshot is made.
