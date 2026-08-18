"""Dump every template id -> abstract question (+ datasets) for audit."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from query_router import template_catalog as tc

candidates = [v for k, v in vars(tc).items()
              if isinstance(v, dict) and v and not k.startswith("_")]
catalog = max(candidates, key=len)

out = []
for qid, spec in catalog.items():
    if not isinstance(spec, dict) or "abstract_question" not in spec:
        continue
    out.append(f"{qid}\t{spec.get('datasets', '')}\t{spec['abstract_question']}")

print(f"{len(out)} templates")
Path(__file__).with_name("catalog_dump.txt").write_text(
    "\n".join(out) + "\n", encoding="utf-8")
print("wrote catalog_dump.txt")
