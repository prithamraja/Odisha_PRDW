# WP-D3b report — closeout fixes + edition regeneration

**Workstream:** Discover. **Ran:** 2026-08-17. **Brief:** `handoffs/WPD3b_closeout.md`.
**Candidate set:** `a7f991c1df3771f9` (pinned, verified, **not** re-mined).
**Run stamp:** `2026-08-17T10:26:15Z`. **Local-mirror execution throughout.**
**No git operation of any kind** — `status` and `log` only, both read-only.

---

## §0 Gate table

| # | Gate item | Verdict | Evidence |
|---|---|---|---|
| 1 | Four fixes in, with evidence | **PASS** | §1 |
| 1a | Executive ranked output byte-identical after the relocation | **PASS** | §1.3. All three `*_ranked.json` hashes unchanged |
| 1b | 0 twin pairs in all five editions | **PASS** | §2. 13 → **0**, measured |
| 2 | Suite + feed + report regenerated from the pinned set, one stamp | **PASS** | §3. Eight artefacts, all `10:26:15Z`, all set `a7f991c1df3771f9` |
| 2a | No stale file; the in-code deletion rule ran | **PASS** | §3.3. Five "removed the previous gamma N edition" lines in the log; repo scan returns exactly eight artefacts |
| 3 | Config gate **176/176** | **PASS** | `wpd3b_run/verify_configs_output.txt` |
| 3 | Regression gate | **PASS** — 15/15, 0 failures | `wpd3b_run/regression_output.txt` |
| 3 | Report checks | **PASS** — 13/13, 0 failures | `wpd3b_run/check_report_output.txt` |
| 3 | Feed contract | **PASS** — both methods | `wpd3b_run/contract_output.txt`; also replayed on the Drive copy |
| 3 | Editions gate, with (f) tightened | **PASS** — **97/97**, 0 failures | `wpd3b_run/editions_output.txt` |
| 4 | No out-of-scope file | **PASS** | §5. `git status` is the allowlist exactly |
| — | Preconditions | **PASS, clean tree** | §5.1. First run in four with nothing to disclose |

---

## §1 The four fixes

### 1.1 `phase4b_engine.py` — the view1 budget (WPD3 §4.2)

`BUDGETS["view1"]` 3,600 → **36,000**. The comment block above it argued for
3,600 from D25's depth-1 drain of 262.5 s; that argument died with D29 and the
comment now carries the depth-2 arithmetic instead — 2,438 subspaces, 809,554
data scopes, 5,208.9 s measured, so 36,000 s is ~6.9× the drain. A plain
`python Insights/src/phase4b_engine.py` no longer truncates the queue.

Not re-run: the brief pins the candidate set and forbids a re-mine, so this fix
is verified by reading, not by mining. What the number has to clear is a
published measurement (5,208.9 s, WPD3 §1.1) and it clears it by 6.9×.

### 1.2 `verify_configs_prdw.py` — the stale D25 assertion (WPD3 §4.1)

```python
check(sample["view1"]["depth"] == state["view1"]["depth"] == 2,
      "view1 depth 2 both (D29)")
```

The D25 comment above it is replaced by one recording that D29 supersedes it and
why, so the next reader does not re-derive the reversal. Gate result: **176 PASS
/ 0 FAIL**, up from 175/1. The three depth lines now read:

```
[PASS] view3 depth 1 sample / 2 statewide
[PASS] view1 depth 2 both (D29)
[PASS] view2 depth 1 both
```

### 1.3 `phase5_ranking.py` — the A2 twin merge relocated (WPD3 §4.3)

The three steps — twin merge, pre-filter, greedy rank — were assembled twice, in
two files, and the two assemblies disagreed. They are now one function,
`merge_prefilter_rank`, and both prose paths call it:

| caller | before | after |
|---|---|---|
| `phase5_ranking.__main__` (executive) | merge → prefilter → rank, spelled out | `merge_prefilter_rank` |
| `phase5c_gamma_reports.py` (editions) | **prefilter → rank** — no merge | `merge_prefilter_rank` |
| `check_editions_prdw.py` re-derivation | prefilter → rank, spelled out | `merge_prefilter_rank` |

The third row matters as much as the second: the gate's replay of "what was each
section written from" reassembled the steps by hand too, so it would have gone
on agreeing with an unmerged generator. All three now share one path, and a
fourth caller cannot repeat the omission without deliberately taking the
function apart.

**Two things were deliberate.** *Order:* A2 runs **before** the pre-filter, which
is why this is a function and not a call moved inside `rank_metainsights` — a
twin merged after the cut could displace a real finding from the 5,000 slots and
then be discarded, costing the top-k a slot for nothing. *Rescored input:* the
gamma path merges its **rescored** candidates. `merge_twin_candidates` keeps the
higher-scored twin, and at a given gamma "higher-scored" has to mean higher at
*that* gamma; the penalty falls on findings with no exceptions, so which twin
survives is exactly the actionability trade-off the knob exists to express.

**The done-check — the executive path's output is byte-identical:**

| file | before | after |
|---|---|---|
| `view1_ranked.json` | `182ff833849488cad3a15c0cec614f903a9ee68bff3175ffe824f8e3262476e1` | **same** |
| `view2_ranked.json` | `44c9638c450d29af03e2981855757c1a603db98272763c695133047d7cf3cd62` | **same** |
| `view3_ranked.json` | `a5fa0a1f5f2fa659f52d89bff2f7d11dc12beb52aa97afccb92b882effd17ecb` | **same** |

Console figures reproduce WPD3 §1.1 line for line: view1 15 from 4,116 after 884
merges, TotalUse 11.3770; view2 15 from 121, TotalUse 3.9987; view3 2 from 2,
TotalUse 0.2967. The candidate-set id is therefore unchanged at
`a7f991c1df3771f9`, which is what let the suite regenerate without a re-mine.

### 1.4 `check_editions_prdw.py` — check (f) tightened

WPD3 §3 flagged its own honest limit: (f) asserted that **at least one** earmark
carrier's figures reach the prose, by testing `carriers[0]` alone. It now tests
**every** carrier — strictly, every distinct `(share, amount-outside)` pair, so
two findings measuring the same scope produce one assertion rather than a
duplicate. Each assertion names the ranks it covers.

The tightening is not cosmetic. At gamma 0.7 and 0.9 the first carrier is the
general-public slice (**95.0% / Rs 39.06 lakh**) and the second is the whole view
(**97.6% / Rs 42.61 lakh**); the old check tested the first and said nothing
about the second. The gate grew from **95** assertions to **97** — exactly the
two added at those two gammas — and all 97 pass. The docstring gains an (f) entry
it never had.

---

## §2 Twin pairs, before and after

Twin pairs surviving into an edition's top-30, per view, measured by replaying
the generator's own step 1 (`wpd3b_run/twin_merge_delta.txt`):

| view | | γ 0.1 | γ 0.3 | γ 0.5 | γ 0.7 | γ 0.9 | total |
|---|---|---:|---:|---:|---:|---:|---:|
| view1 | before | 3 | 3 | 3 | 2 | 2 | **13** |
| view1 | **after** | **0** | **0** | **0** | **0** | **0** | **0** |
| view2 | before / after | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 |
| view3 | before / after | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 |

The "before" row reproduces WPD3 §4.3's table exactly (3/3/3/2/2), which is the
check that this measurement is measuring the right thing. Merges now performed
per edition: **884** view1, **1** view2, 0 view3 — the same counts the executive
path has always run.

**What it cost the rankings.** 16 of the 460 top-30 slots across all fifteen
(gamma, view) lists changed, all of them in view1, and each displaced slot was a
duplicate replaced by a distinct finding:

| gamma | view1 slots changed | view2 | view3 |
|---|---:|---:|---:|
| 0.1 / 0.3 / 0.5 | 4 each | 0 | 0 |
| 0.7 / 0.9 | 2 each | 0 | 0 |

The gamma knob still does what it did. view1's exception-carrying findings climb
**0 → 6 → 19 → 30 → 30** across the five editions (WP-D3 measured 0 → 4 → 20 →
30 → 30 on the unmerged pool), so the five editions remain five genuinely
different rankings and not five renderings of one list.

---

## §3 The regenerated suite

### 3.1 Order and stamp

`DISCOVER_RUN_STAMP=2026-08-17T10:26:15Z` exported once across all three
processes, in WPD3 §5.3's order — **feed → executive report → five editions** —
because `phase5b_report` opens the executive report with a section written from
`global_feed.json`.

### 3.2 What shipped

| artefact | bytes (was) | sha256 (first 16) |
|---|---:|---|
| `Insights/metainsights/global_feed.json` | 53,709 (53,709) | `3da40edae324f917` |
| `Insights/metainsights/global_feed_source_set.json` | 1,474 (1,474) | `6c7b62e62f728849` |
| `Insights/reports_prdw/global_feed.md` | 11,387 (11,387) | `e97bb557df388070` |
| `Insights/reports_prdw/executive_metainsight_report.md` | 22,163 (22,709) | `93d5c8fd1a43574e` |
| `Insights/reports_prdw/executive_metainsight_report.pdf` | 20,672 (21,334) | — |
| `Insights/reports_prdw/gamma_0.1_report.md` | 26,754 (32,426) | `782ebef1a30b329a` |
| `Insights/reports_prdw/gamma_0.3_report.md` | 30,149 (29,793) | `ede3e19b55620750` |
| `Insights/reports_prdw/gamma_0.5_report.md` | 30,144 (32,160) | `883b778a6ba90c83` |
| `Insights/reports_prdw/gamma_0.7_report.md` | 28,509 (32,152) | `8f22efd9e4a00cba` |
| `Insights/reports_prdw/gamma_0.9_report.md` | 29,276 (30,994) | `4a0ae14e5e78911b` |

**`global_feed.json` did not change by a single byte.** It is not in `git status`
at all. The feed is built from the `*_ranked.json` this WP proved byte-identical,
and the stamp lives in the sidecar rather than in the JSON (D16 freezes the
fields), so the relocation is provably invisible to the frontend contract.
`global_feed.md` and the sidecar differ from the committed versions in **one
line each** — the stamp — and nothing else. Full diffs:

```
global_feed.md:3            08:56:36Z -> 10:26:15Z
global_feed_source_set.json:9  "generated_at" 08:56:36Z -> 10:26:15Z
```

The five editions differ substantively, which is the point. The executive report
differs as regenerated prose over an identical ranked list — its 13/13 report
checks and 112/112 traced figures pass.

### 3.3 No stale file

The full-suite run took its own in-code deletion path: five `removed the previous
gamma N edition` lines head `wpd3b_run/gamma_log.txt`, before anything was
written. A scan of the repo for `gamma_*_report.md` and `global_feed*` returns
exactly the eight artefacts above and nothing else; `Insights/reports/` — the
AP-era output path — still does not exist.

---

## §4 Verification of the pinned candidate set (T2 STOP check)

SHA-256 of the six files in `Insights/metainsights/`, against WPD3 §1.2, before
anything was run. **All six match; no STOP condition.**

| file | sha256 | bytes | vs §1.2 |
|---|---|---:|---|
| `view1_candidates.json` | `890767085988a6c7b61b1694a51e544d977932b1f567c89cae0e017b3643359b` | 5,868,996 | match |
| `view1_ranked.json` | `182ff833849488cad3a15c0cec614f903a9ee68bff3175ffe824f8e3262476e1` | 18,430 | match |
| `view2_candidates.json` | `5796d3c8029c5f06efe71fa59ce84c3e9c847335b52b89c0078eb82f0ad2358c` | 143,100 | match |
| `view2_ranked.json` | `44c9638c450d29af03e2981855757c1a603db98272763c695133047d7cf3cd62` | 16,544 | match |
| `view3_candidates.json` | `a5fa0a1f5f2fa659f52d89bff2f7d11dc12beb52aa97afccb92b882effd17ecb` | 3,613 | match |
| `view3_ranked.json` | `a5fa0a1f5f2fa659f52d89bff2f7d11dc12beb52aa97afccb92b882effd17ecb` | 3,613 | match |

All six are byte-identical **after** the run as well: the ranking rewrote the
three `*_ranked.json` to the same bytes and nothing touched the candidates.

---

## §5 Self-audit

### 5.1 Preconditions

**The tree was clean** at HEAD `08275b9` — the first of four consecutive Discover
runs with nothing to disclose here, and the commit the WP-D3 report asked for.
Local mirror built fresh in this session's scratchpad; views rebuilt from `Data/`
+ the pack (README recipe step 1, 0 failed checks, 12,704 / 1,440 / 120 rows).
`Insights/.env` present and used, never read out or written. No re-mine.

### 5.2 Files written — exactly the allowlist

```
Insights/src/phase4b_engine.py             one number + its comment (T1, WPD3 §4.2)
Insights/src/phase5_ranking.py             merge_prefilter_rank + __main__ call site
Insights/src/phase5c_gamma_reports.py      the call-site change (import + step 1)
Insights/reports_prdw/check_editions_prdw.py  (f) tightened; re-derivation on the shared path
Insights/reports_prdw/{global_feed.md, executive_metainsight_report.md/.pdf,
                       gamma_0.{1,3,5,7,9}_report.md, wpd3b_run/}
Insights/metainsights/{global_feed.json, global_feed_source_set.json}
handoffs/WPD2_calibration/verify_configs_prdw.py   one assertion + its comment (D29)
handoffs/WPD3b_REPORT.md                   this file
```

`git status` lists these and nothing else. **No git operation ran** beyond
`status` and `log`.

### 5.3 Three things deliberately not done

- **`validation_report.txt` was not copied back.** Rebuilding the views in a new
  scratchpad regenerates it, and it differs from the committed copy in exactly
  two ways: the generation timestamp and the absolute scratchpad paths of a
  different agent's temp directory. Every row count and every check is identical.
  Copying it back would have added a diff that says nothing. `view_summaries.txt`
  rebuilt byte-identical and is untouched either way.
- **`Insights/reports/` was not copied back.** `phase5_ranking.__main__` writes
  layer 2P/3P there — the AP-era path. It exists in the mirror and must not
  appear in the repo; WPD3 §1.4's "no stale edition can hide there" depends on
  the directory not existing.
- **The `--depth2` flag was left alone.** It now sets `max_subspace_depth = 2`
  (already the D29 default) and `BUDGETS["view1"] = 36000` (now also the
  default), so the flag is a no-op. Harmless, and retiring it is a decision about
  D15's sample/statewide split rather than a closeout fix — flagged, not touched.

### 5.4 What I would not claim

- **The budget fix is verified by argument, not by a mining run** (§1.1). The
  brief pins the candidate set; re-mining to watch 36,000 s not truncate would
  have destroyed the thing the gate is checking. The number clears the published
  measurement by 6.9×.
- **The editions gate still cannot replay on the Drive.** It re-derives the
  enrichment and needs `Insights/views_prdw/*.parquet`, which correctly do not
  live on the Drive mount (D6). Replay from a local mirror after README step 1.
  The feed contract check has no such dependency and was replayed on the Drive
  copy of the shipped artefacts, passing.
- **The five editions' prose is regenerated LLM output.** The rankings behind
  them are deterministic and measured above; the sentences are not, so the
  editions differ from WP-D3's in wording as well as in content. Every
  deterministic assertion about them — 97 of them — is green.
- **Gate item 5 of WP-D3 (frontend acknowledgement) is still the operator's**,
  and is untouched by this WP. The Facts-7 handover path and `global_feed.json`
  are byte-for-byte what WP-D3 delivered.

### 5.5 Open PM items from WP-D3, after this run

| # | WPD3 §6 item | Status |
|---|---|---|
| 1 | `phase4b_engine.py` view1 budget | **closed** (§1.1) |
| 2 | The stale config-gate assertion | **closed** (§1.2) |
| 3 | Twin merging in the gamma path | **closed** (§1.3, §2) |
| 4 | A `provenance` block in the feed contract (D-12) | **still open** — operator decision; the sidecar carries it meanwhile |
| 5 | Whether `metainsights/*_candidates.json` (5.6 MB) belongs in the repo | **still open** — they are what lets the gate holder re-derive the candidate-set id |

Also still open and not this WP's to do: deleting the two reference packs
(`Insights/domain_pack/`, `Insights/domain_pack_rtgs/`) as a separate approved
commit, and the `summary`-strings glossary note for the frontend (WPD3 §6).

**Replay recipe:**

```
# from a LOCAL mirror, views built (README recipe step 1):
python handoffs/WPD2_calibration/verify_configs_prdw.py      --base Insights   # 176/176
python handoffs/WPD2_calibration/check_calibration_regression.py --base Insights
python handoffs/WPD2_calibration/check_report_prdw.py        --base Insights
python Insights/reports_prdw/check_feed_contract.py          --base Insights   # also works on Drive
python Insights/reports_prdw/check_editions_prdw.py          --base Insights   # needs views_prdw/
```
