# Scanner operations

Requires Python 3.11+ and the standard library; Git is optional. Resolve the
installed skill directory and invoke its script by absolute path. Quote paths
with spaces. Commands operate on the explicit `--root`; they never clone, install,
run a project, stage, commit, push, or contact GitHub.

```text
python <skill-directory>/scripts/amanuensis.py scan --root <project>
python <skill-directory>/scripts/amanuensis.py validate --root <project>
python <skill-directory>/scripts/amanuensis.py checkpoint --root <project>
```

`scan` hashes files and writes `.amanuensis/project-manifest.json`. It extracts
Node dependency/script names, Python project dependencies/script names, and
environment key names from `.env.example`, `.env.sample`, `.env.template`.
It intentionally omits command bodies and environment values from model-facing
facts. Exact commands must be inspected at their source before execution.

The manifest has source hashes, inventory, extracted facts, changes versus the
last documented baseline, Git revision when the root is an exact repository root,
coverage warnings, and suggested evidence reviews. Standard output is capped at
12,000 characters. Large inventories stay on disk; query only the paths, packages
or changes needed with a shell/JSON reader. A scanner summary is not the project
description or an architecture model. Other languages are inventoried but need
targeted agent investigation; route/schema detection is not implemented.

Default limits: 20,000 files and 128 MiB total bytes hashed. Increase using
`--max-files` / `--max-bytes` when warranted. Reaching a limit or failing a read
marks the scan incomplete and prevents checkpointing. Metadata extraction skips
files above 1 MiB. Large files can still be hashed by raising the byte limit.

Excluded: Git internals, common dependency/build/cache directories, symlinks and
junction directories, known credential filenames/private key extensions, real
`.env*` files, the generated root document, `.amanuensis/`, `docs/amanuensis/`.
These exclusions are heuristic, not a secret detector. Inspect the project scope
before scanning sensitive repositories. Hashes are not encryption. Do not put
credentials into state or documentation. The scanner does not interpret
`.gitignore`; ignored source can be relevant, and sensitive custom locations need
explicit exclusion with `.amanuensisignore` before scanning.

`.amanuensisignore` supports one project-relative glob per line, `#` comments,
directory names like `private/`, and patterns like `*.sqlite`. No negation or Git
ignore semantics. A simple directory name excludes matching directories at any
depth. Keep this file in Git to make the scan boundary reproducible.

`validate` checks required headings, evidence shape/coverage, and local targets
in inline/reference Markdown links and HTML src/href attributes outside fenced
code. It rejects links outside the project. It does not parse all Markdown syntax,
validate fragment anchors/remote links, prove evidence authenticity, or scan for
every possible secret. Check those during editorial/rendered review.

`checkpoint` validates, rescans using the stored limits, refuses changed or
incomplete inputs, and checks observed evidence fingerprints. Only then does it
write `.amanuensis/state.json`. Scan never advances this baseline. Checkpoints may
contain unresolved gaps; report them rather than claiming all behavior works.
Source hashes also capture dirty/untracked files, so Git SHA alone is insufficient.

Version the document, used media, evidence index, manifest, and state together for
incremental work across machines. Paths are relative; timestamps are UTC. Avoid
loading/staging unrelated changes. Confirm the actual Git root before Git writes:
an ancestor repository is intentionally ignored by the scanner. Use a real project
checkout for GitHub publication; do not stage into an unrelated ancestor repo.

Installation: place this skill folder (SKILL.md, agents/, scripts/, references/)
in your host's skill directory, conventionally `~/.codex/skills/amanuensis` for
Codex. Keep it separate from the project being documented, so its own script or
instruction changes do not affect that project's fingerprints. The skill needs
no server or API key; GitHub access and screenshot tools come from the host.
