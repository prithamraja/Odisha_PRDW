"""Operator ruling 2026-09-14: the catalogue's caveats are removed. One-shot, reviewed.

    python tools/migrations/m4_drop_caveats.py
    python tools/derive_catalog.py        # the re-ranker lines quoted each caveat

Each template's caveat was appended to the echoed question as "Note: …". The
operator's finding: the notes confused officers and were almost never helpful.
This reverses D3 for the catalogue. The lossy-alias sentence (Swachh Bharat ->
Sanitation, WP-6 T5) is a separate ruling and stays — it is built in
entity_validator.lossy_caveat, not stored here.

Every `"caveat": <text>` becomes `"caveat": None`; the key stays so a caveat can
be put back on one template by hand. The file is edited through its syntax tree
rather than by pattern, and the script proves nothing else moved: before and
after are imported and compared field by field.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
CATALOG = BACKEND / "query_router" / "template_catalog.py"


def _caveat_spans(tree: ast.Module) -> list[ast.expr]:
    for node in tree.body:
        target = (node.target if isinstance(node, ast.AnnAssign)
                  else node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "TEMPLATE_CATALOG":
            spans = []
            for entry in node.value.values:
                for key, value in zip(entry.keys, entry.values):
                    if (isinstance(key, ast.Constant) and key.value == "caveat"
                            and not (isinstance(value, ast.Constant)
                                     and value.value is None)):
                        spans.append(value)
            return spans
    raise SystemExit("TEMPLATE_CATALOG not found")


def main() -> None:
    from query_router import template_catalog
    before = {qid: dict(t) for qid, t in template_catalog.TEMPLATE_CATALOG.items()}

    raw = CATALOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    spans = _caveat_spans(ast.parse(raw.decode("utf-8")))
    # Offsets are UTF-8 byte columns, so the edit works on bytes. Last first, so
    # an earlier span's offsets are not moved by a later replacement.
    for value in sorted(spans, key=lambda v: (v.lineno, v.col_offset), reverse=True):
        first, last = value.lineno - 1, value.end_lineno - 1
        head = lines[first][:value.col_offset]
        tail = lines[last][value.end_col_offset:]
        lines[first:last + 1] = [head + b"None" + tail]
    CATALOG.write_bytes(b"".join(lines))

    after = importlib.reload(template_catalog).TEMPLATE_CATALOG
    assert set(after) == set(before), "a template appeared or vanished"
    for qid, entry in after.items():
        assert entry.get("caveat") is None, qid
        assert ({k: v for k, v in entry.items() if k != "caveat"}
                == {k: v for k, v in before[qid].items() if k != "caveat"}), qid
    print(f"cleared {len(spans)} caveats across {len(after)} templates; "
          f"every other field unchanged")


if __name__ == "__main__":
    main()
