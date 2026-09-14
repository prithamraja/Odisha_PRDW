"""WP-D11b T1 proof -- the split vector files are the unsplit arrays, byte for byte.

Run in the WP-D11b mirror after the split rebuild, with the WP-D11 mirror
(`C:\\dev\\odisha-d11`) still holding the unsplit `.npy` files it shipped:

    python handoffs/WPD11b_calibration/t1_split_proof.py \
        --split Insights/metainsights --unsplit C:/dev/odisha-d11/Insights/metainsights

Asserts, for BOTH corpora:
  1. the parts the stamp names, loaded in order and concatenated, hash to
     exactly the bytes of the unsplit fp16 array (sha256 of `.tobytes()`), with
     the same dtype and shape -- and to the stamp's own `matrix_sha256`;
  2. every part is under 100 MB and within the 95 MB part budget;
  3. the loader refuses a missing part and an altered part (on a scratch copy);
  4. `semantic_pin()` is the pin the WP-D11 build recorded, storage fields aside,
     so the cache and every vector's meaning are unchanged;
  5. the split build made zero embedding calls.
Exits non-zero on any failure.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "Insights", "src"))

import phase5d_retrieval_corpus as p5d            # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, help="metainsights dir of the split build")
    ap.add_argument("--unsplit", required=True, help="metainsights dir of the WP-D11 build")
    args = ap.parse_args()

    for name in ("retrieval_corpus", "decompose_corpus"):
        print(f"\n=== {name} ===")
        stamp = json.load(open(os.path.join(args.split, f"{name}_stamp.json"), encoding="utf-8"))
        old_stamp = json.load(open(os.path.join(args.unsplit, f"{name}_stamp.json"), encoding="utf-8"))
        manifest = stamp["vector_storage"]
        vectors_path = os.path.join(args.split, f"{name}.npy")

        unsplit = np.load(os.path.join(args.unsplit, f"{name}.npy"))
        parts = [np.load(os.path.join(args.split, p["file"])) for p in manifest["parts"]]
        joined = np.concatenate(parts, axis=0) if len(parts) > 1 else parts[0]
        h_unsplit = hashlib.sha256(np.ascontiguousarray(unsplit).tobytes()).hexdigest()
        h_joined = hashlib.sha256(np.ascontiguousarray(joined).tobytes()).hexdigest()
        check(unsplit.dtype == joined.dtype == np.float16,
              "both are float16", f"{unsplit.dtype} / {joined.dtype}")
        check(unsplit.shape == joined.shape, "same shape", f"{unsplit.shape} / {joined.shape}")
        check(h_unsplit == h_joined, "concatenated parts are byte-identical to the unsplit array",
              f"sha256 {h_joined[:16]} vs {h_unsplit[:16]}")
        check(manifest["matrix_sha256"] == h_joined, "the stamp's matrix_sha256 is those bytes")
        loaded = p5d.load_vectors(vectors_path, manifest)
        check(loaded.dtype == np.float32 and np.array_equal(loaded, unsplit.astype(np.float32)),
              "the loader returns exactly the unsplit array, upcast to fp32")

        for p in manifest["parts"]:
            size = os.path.getsize(os.path.join(args.split, p["file"]))
            check(size < 100_000_000 and size <= p5d.PART_MAX_BYTES,
                  f"{p['file']} is {size / 1e6:.1f} MB (< 100 MB, <= 95 MB budget)")

        # The refusals, on a scratch copy so the real files are never touched.
        scratch = tempfile.mkdtemp(prefix="wpd11b_t1_")
        try:
            for p in manifest["parts"]:
                shutil.copy(os.path.join(args.split, p["file"]), scratch)
            spath = os.path.join(scratch, f"{name}.npy")
            first = os.path.join(scratch, manifest["parts"][0]["file"])
            with open(first, "r+b") as fh:                     # alter one byte
                fh.seek(-1, os.SEEK_END)
                last = fh.read(1)
                fh.seek(-1, os.SEEK_END)
                fh.write(bytes([last[0] ^ 1]))
            try:
                p5d.load_vectors(spath, manifest)
                check(False, "an altered part is refused")
            except p5d.VectorPartsError as exc:
                check("sha256" in str(exc), "an altered part is refused", str(exc)[:90])
            os.remove(first)
            try:
                p5d.load_vectors(spath, manifest)
                check(False, "a missing part is refused")
            except p5d.VectorPartsError as exc:
                check("missing" in str(exc), "a missing part is refused", str(exc)[:90])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        old_pin = {k: v for k, v in old_stamp["embedding_pin"].items()
                   if k not in p5d.NON_SEMANTIC_PIN_FIELDS}
        check(old_pin == p5d.semantic_pin(), "semantic_pin() is the pin WP-D11 embedded under")
        check(stamp["embedding_pin"]["storage_layout"] == p5d.STORAGE_LAYOUT,
              "the full pin records the part layout", stamp["embedding_pin_fingerprint"])
        check(stamp["embedding_calls"] == 0 and stamp["texts_embedded"] == 0,
              "the split build made zero embedding calls",
              f"calls={stamp['embedding_calls']} texts={stamp['texts_embedded']}")

    print(f"\n{len(fails)} failure(s)" + (": " + "; ".join(fails) if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
