# Evidence and freshness

Maintain `.amanuensis/evidence-index.json` with an `items` array. Each item has a
unique `id`, a `section` matching a document level-two heading, `status`, and
`summary`. Include at least one meaningful item per section. Add separate items
for distinct claims/checks, especially when one section mixes outcomes.

Statuses:

- `observed`: actually read in source, or actually executed/captured with a result.
- `inferred`: a reasoned interpretation not directly established. State its basis.
- `unavailable`: omitted, blocked, stale, or inapplicable. Explain why and, for a
  gap, the prerequisite or next action. These records remain gaps at checkpoint.

An observed item requires `kind` (`source` or `runtime`), `observed_at` (ISO 8601),
and `input_fingerprint` copied from the current scanner manifest after review.
Source observations require project-relative `sources`. Runtime observations
require `procedure` including command/action, working directory, environment,
actual result and exit status where available. `sources` and `assets` are arrays
of project-relative paths (optional `#L` source fragments).

Example of one item, not a complete index:

```json
{
  "items": [
    {
      "id": "api-entry",
      "section": "Architecture",
      "status": "observed",
      "kind": "source",
      "summary": "The HTTP application is created in api/main.py.",
      "sources": ["api/main.py"],
      "assets": [],
      "observed_at": "2026-11-21T02:00:00+00:00",
      "input_fingerprint": "COPY_CURRENT_MANIFEST_FINGERPRINT"
    }
  ]
}
```

For screenshots/video additionally record the workflow, URL/route or app state,
viewport, role, capture time, relevant fixture data, and expected/actual outcome
in `procedure` or extra fields. Capture the running project using available
browser/computer tools, never an AI-generated substitute. Use synthetic test data;
exclude credentials, customer data and private account details from captures.
Open each asset before delivering it. Record failure as an observed failed check,
with the failure clearly stated; `observed` does not mean a test passed.

On update, the scanner suggests `review_evidence_ids` using source dependencies
and conservative runtime/config invalidation. This is a triage hint, not a full
dependency graph. Trace downstream consumers; additions/deletions may invalidate
other source claims. External service/data changes can invalidate runtime checks
even with an unchanged source fingerprint.

Review all observed records before assigning the current fingerprint. If the
claim remains supported by unchanged sources, retain its original observation
time and record `reviewed_at` and `reused_from_fingerprint`. Rerun affected runtime
checks or mark them unavailable/stale. Preserve old capture provenance when
reusing assets and explain why they remain representative. Never bulk-stamp old
evidence as newly verified. Checkpoint rejects observed records without the
current fingerprint, but human/agent review establishes truth, not that field.

Runtime failure or unavailable access must not trigger repairs to the product
unless the user also authorized fixing it. Complete the accessible documentation
and name the remaining gap. Publish neither environment values nor raw logs that
could contain secrets. Inspect sanitized results rather than loading full logs.
