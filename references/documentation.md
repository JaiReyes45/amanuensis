# Documentation contract

Write `PROJECT_DOCUMENTATION.md` for a reader who has never seen the chat. Lead
with the project's actual purpose, audience, and implemented capabilities. Include
a relative-link table of contents and a GitHub repository link when known. Record
the inspected branch/commit (or explicitly no project Git boundary), UTC review
time, selected depth, and scope of verification. Fingerprints include dirty and
untracked project files; identify uncommitted source when publishing docs.

Use these exact level-two headings, retaining existing useful prose and adding
subheadings appropriate to the project:

| Section | Required substance |
| --- | --- |
| Overview | Purpose, audience, implemented scope, current maturity, significant constraints. |
| Architecture | Components, responsibilities, connections, persistence, integrations and data flow. Include a small Mermaid diagram when it clarifies relationships, with source links and explicit inferred edges. |
| Repository map | Important directories and entry points with their roles; avoid full generated file trees. |
| Setup and configuration | Prerequisites, working directories, installation, safe configuration names, services, startup, expected success. Distinguish commands inspected from commands executed. |
| Operation and deployment | Routine operation, build/test commands, deployment path, maintenance, recovery and rollback when applicable. Separate inferred deployment advice from tested procedures. |
| Features and workflows | Main user roles, inputs, steps, outputs, state changes, failure paths and important limitations. For automation, cover triggers, schedules, retries and ownership. |
| Visual walkthrough | Captioned real screenshots linked relatively, describing the action and result. For a CLI/workflow, use actual sanitized output or execution traces. Explain unavailable evidence. |
| Demo | A reproducible scenario with prerequisites, sample data, steps, expected results and reset instructions. Link a recording when captured; explicitly mark an unexecuted script. |
| User handoff | How a nondeveloper accesses and uses it, permissions, routine tasks, common errors and support ownership if known. |
| Developer handoff | Entry points, extension seams, test strategy, operational responsibilities, known debt and next actions grounded in the project. |
| Troubleshooting and limitations | Symptom, likely cause, recovery steps, known gaps, unavailable prerequisites and unsupported cases. |
| Evidence and freshness | What was checked, actual outcomes, source revision/fingerprint, reused/stale evidence and unresolved gaps. Link the evidence index. |

Use source links such as `[API entry](api/main.py#L12)`; stable GitHub commit
permalinks are useful when the remote and revision are verified. Never invent a
repository address, line number, test outcome, screenshot, feature, or owner.

Store images under `docs/amanuensis/screenshots/`, diagram exports/sources under
`docs/amanuensis/diagrams/`, and small demo artifacts under `docs/amanuensis/demos/`.
Inline Mermaid is sufficient when it renders correctly. Create only used folders.
For large recordings, prefer an authorized release attachment or approved hosting
and link it; avoid adding large binaries or configuring Git LFS without a need.

On subsequent runs, preserve human edits. Reconcile contradictions with code and
explicit user knowledge rather than treating the old document as authoritative.
If an existing PROJECT_DOCUMENTATION.md has a different structure, adapt its content
carefully to these headings without removing useful material. Keep existing guides
as authoritative references where duplicating instructions would create drift.

For projects without runnable software, adapt architecture to stages, actors,
inputs/outputs and dependencies; setup to prerequisites; deployment to release or
distribution. Mark a truly irrelevant section inapplicable with an explanation.

Completion means applicable sections are written, local links/assets resolve,
media was visually reviewed, and evidence states match actual observations. Report
any runtime/demo gaps prominently even when a documentation checkpoint is saved.
