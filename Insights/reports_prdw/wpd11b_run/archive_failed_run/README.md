# WP-D11b — the failed prose build, set aside

`calls_20260911T102953Z.jsonl` is the WP-D11b insight-prose build started
2026-09-11 10:29:53Z (run stamp of stage A). It made **30 calls** (1 budget
check, 4 writer batches, 1 verifier budget check, 19 verifier, 5 regenerate)
and wrote renderings for ranks 1–13 of 46 before OpenAI returned HTTP 500
("The server had an error while processing your request") on the rank-14
regeneration, after the client's own two retries. No sidecar was written.

**Moved here on the operator's ruling (2026-09-11, "set aside and rerun all")**
so that `MAX_CALLS_TOTAL = 150`, which counts every `calls_*.jsonl` directly in
`wpd11b_run/`, covers the re-run alone. These 30 calls were spent and bought
nothing; they are counted in WPD11b_REPORT §5, not hidden. Same procedure as
WP-D11's `wpd4c_run/archive_pre_wpd11/`.

A 1-call probe to each model after the failure (not a prose call, not logged
here) returned normally, so the 500 was transient.
