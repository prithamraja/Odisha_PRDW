"""WP-6 T0, one-shot: mark the derived part of every paraphrase list.

    python tools/migrations/m0_mark_derived.py

Run ONCE, against the last workbook-built `template_catalog.py` and
`unanswerable_catalog.py`, at the moment the catalogue file became the source of
truth. Each paraphrase list is split at the point where "the lines above +
derive(entry, lines above)" reproduces it exactly, and the two markers are
written in: lines above the first marker are hand-owned from then on, lines
between the markers belong to `tools/derive_catalog.py`.

WHAT IT CHANGES, AND WHAT IT PROVES IT DID NOT. Only comment lines are added.
The script executes each file before and after and asserts the catalogue DICT is
identical — so the embedded texts, the retrieval index signature and every
statement are unchanged, and the recall and row-count baselines carry across the
switch untouched. It refuses to finish if any list cannot be split.

Kept in the tree as the record of how the markers got there; re-running it is a
no-op (lists that already carry markers are skipped).
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402


def main() -> int:
    for path, name, derive in (
        (dc.TEMPLATE_PATH, "TEMPLATE_CATALOG", dc.derived_template_paraphrases),
        (dc.UNANSWERABLE_PATH, "UNANSWERABLE_CATALOG", dc.derived_unanswerable_paraphrases),
    ):
        source = path.read_text(encoding="utf-8")
        before = dc.load_catalog(source, name)
        marked, unsplit = dc.adopt_markers(source, before, derive)
        if unsplit:
            print(f"{path.name}: no derived split reproduces {unsplit}; nothing written",
                  file=sys.stderr)
            return 1
        after = dc.load_catalog(marked, name)
        if after != before:
            print(f"{path.name}: the catalogue dict changed — refusing", file=sys.stderr)
            return 1
        derived = sum(1 for line in marked.split("\n")
                      if line.startswith(" " * 12 + "'") or line.startswith(" " * 12 + '"'))
        path.write_text(marked, encoding="utf-8")
        print(f"{path.name}: {len(before)} entries marked; dict unchanged "
              f"({derived} paraphrase lines in total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
