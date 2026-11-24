"""Place profile sheets: the reader (WP-D14, spec handoffs/PROFILE_SHEET_SPEC.md).

Returns one place's sheet by level and code. Nothing in the service imports
this module yet; WP-D15 wires it into /chat. Its contract:

    available() -> bool              the store is present and passes every check
    stamp() -> dict
    get(level, code) -> dict | None  one sheet: the place, its parents, the main
                                     rows, the lists
    sentences(level, code) -> list   in the hand-over order; each item is
                                     {"id", "row", "sentence", "note"}
    sentence(id) -> dict | None      one sentence by its id
    place(level, code) -> dict | None {"level", "code", "name", "label",
                                     "parents"}, from the index alone
    find(level, name) -> list        the codes at that level whose name equals
                                     `name`, ignoring case and outer spaces;
                                     [] when none, several when a name repeats

The store is written by `Insights/src/phase5g_profile_sheets.py`: an index
(`profile_sheets_index.json.gz`, gzipped so a Windows checkout cannot rewrite
its line ends and break its hash) that maps level -> code -> [part, offset, length],
numbered part files holding each sheet as its own zlib-compressed JSON, and a
stamp listing every file with its SHA-256. So one sheet is read without reading
any other, and no sheet is held in memory until it is asked for.

THE READER REFUSES (raises `ProfileStoreRefused`; `available()` says False):
  * a file the stamp names that is missing or altered (the WP-D11b discipline);
  * a store whose candidate set differs from the findings corpus's -- two run
    stamps in one answer would date it wrongly whichever one it printed;
  * any store marked synthetic (the T7 scale test's);
  * an index built before WP-D14b, with no name table ("rebuild the store").

It computes nothing. Every figure, share, rank and sentence is in the store.
Standard library only, so opening the store costs no more than the index.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import zlib

INDEX_NAME = "profile_sheets_index.json.gz"
# 2 = WP-D14b: the index carries `places`, the name table (level -> code ->
# name, label, parent codes). An index without it is refused.
INDEX_FORMAT = 2
STAMP_NAME = "profile_sheets_stamp.json"
PART_PATTERN = "profile_sheets.part{}.bin"
LEVELS = ("gp", "block", "district", "all")

# p-<level>-<code>-<row>[-<key>] or p-all-<row>[-<key>]
SHEET_ID_RE = re.compile(
    r"^p-(?:(gp|block|district)-([A-Za-z0-9_.]+)|(all))-([A-Z]{1,2}\d?)(?:-(\S+))?$")


class ProfileStoreRefused(RuntimeError):
    """The store failed a check and will not be served."""


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ProfileStore:
    """One store on disk. `expected_candidate_set` is the findings corpus's id
    (None skips that comparison -- the builder's own checks use it).
    `allow_synthetic` is for the T7 scale test and nothing else."""

    def __init__(self, directory, allow_synthetic: bool = False,
                 expected_candidate_set: str | None = None):
        self.dir = str(directory)
        self.allow_synthetic = allow_synthetic
        self.expected_candidate_set = expected_candidate_set
        self._stamp = None
        self._index = None
        self._verified = False
        self._names = {}          # level -> {folded name: [codes]}, built on first find

    # ── checks ──────────────────────────────────────────────────────────────
    def _path(self, name: str) -> str:
        return os.path.join(self.dir, name)

    def stamp(self) -> dict:
        if self._stamp is None:
            path = self._path(STAMP_NAME)
            if not os.path.exists(path):
                raise ProfileStoreRefused(f"no profile sheet stamp at {path}")
            with open(path, encoding="utf-8") as fh:
                self._stamp = json.load(fh)
        return self._stamp

    def verify(self) -> None:
        """Every check, once per instance. Raises ProfileStoreRefused."""
        if self._verified:
            return
        st = self.stamp()
        if st.get("synthetic") and not self.allow_synthetic:
            raise ProfileStoreRefused("the store is marked synthetic (a scale "
                                      "test's), never served")
        if (self.expected_candidate_set is not None
                and st.get("candidate_set_id") != self.expected_candidate_set):
            raise ProfileStoreRefused(
                f"the store was built from candidate set "
                f"{st.get('candidate_set_id')}, the findings corpus from "
                f"{self.expected_candidate_set}")
        files = st.get("files") or []
        if not files or files[0]["file"] != INDEX_NAME:
            raise ProfileStoreRefused("the stamp names no index")
        for f in files:
            path = self._path(f["file"])
            if not os.path.exists(path):
                raise ProfileStoreRefused(f"{f['file']} is named by the stamp "
                                          f"and missing")
            if os.path.getsize(path) != f["bytes"] or _sha256(path) != f["sha256"]:
                raise ProfileStoreRefused(f"{f['file']} has been altered since "
                                          f"the stamp was written")
        with gzip.open(self._path(INDEX_NAME), "rt", encoding="utf-8") as fh:
            index = json.load(fh)
        named = [f["file"] for f in files[1:]]
        if index.get("parts") != named:
            raise ProfileStoreRefused("the index and the stamp name different parts")
        if index.get("candidate_set_id") != st.get("candidate_set_id"):
            raise ProfileStoreRefused("the index and the stamp disagree on the "
                                      "candidate set")
        if index.get("format") != INDEX_FORMAT or "places" not in index:
            raise ProfileStoreRefused("the index was built before WP-D14b and "
                                      "has no name table; rebuild the store")
        self._index = index
        self._verified = True

    def available(self) -> bool:
        try:
            self.verify()
            return True
        except (ProfileStoreRefused, OSError, ValueError):
            return False

    # ── reading ─────────────────────────────────────────────────────────────
    def index(self) -> dict:
        self.verify()
        return self._index

    def codes(self, level: str) -> list:
        return list(self.index()["sheets"].get(level, {}))

    def get(self, level: str, code) -> dict | None:
        """One sheet, read from its part file alone, or None for an unknown key."""
        entry = self.index()["sheets"].get(level, {}).get(str(code))
        if entry is None:
            return None
        part, offset, length = entry
        with open(self._path(self._index["parts"][part]), "rb") as fh:
            fh.seek(offset)
            blob = fh.read(length)
        return json.loads(zlib.decompress(blob).decode("utf-8"))

    def sentences(self, level: str, code) -> list:
        sheet = self.get(level, code)
        if sheet is None:
            return []
        notes = self._index["notes"]
        return [{"id": s["id"], "row": s["row"], "sentence": s["sentence"],
                 "note": notes.get(s["note"]) if s.get("note") else None}
                for s in sheet["sentences"]]

    def place(self, level: str, code) -> dict | None:
        """A place's name, label and parents, from the index alone."""
        places = self.index()["places"]
        entry = places.get(level, {}).get(str(code))
        if entry is None:
            return None
        parents = {}
        for parent in ("block", "district"):
            if parent in entry:
                pcode = entry[parent]
                parents[parent] = {"code": pcode,
                                   "name": places[parent][pcode]["name"]}
        return {"level": level, "code": str(code), "name": entry["name"],
                "label": entry["label"], "parents": parents}

    @staticmethod
    def _fold(name) -> str:
        return str(name or "").strip().casefold()

    def find(self, level: str, name) -> list:
        """Every code at `level` whose name equals `name`, ignoring case and
        outer spaces. Several when a name repeats at that level: choosing
        among them is the caller's job, never guessed here."""
        places = self.index()["places"].get(level)
        if places is None:
            return []
        if level not in self._names:
            table = {}
            for code, entry in places.items():
                table.setdefault(self._fold(entry["name"]), []).append(code)
            self._names[level] = table
        return list(self._names[level].get(self._fold(name), []))

    def sentence(self, sentence_id: str) -> dict | None:
        m = SHEET_ID_RE.match(sentence_id or "")
        if not m:
            return None
        level, code = (m.group(1), m.group(2)) if m.group(1) else ("all", "all")
        for item in self.sentences(level, code):
            if item["id"] == sentence_id:
                return item
        return None


# ── The module-level contract, over the committed store ─────────────────────
_DEFAULT: ProfileStore | None = None


def default_store() -> ProfileStore:
    """The store beside the insight corpora, bound to the findings corpus's
    candidate set. Imported lazily so this module stays light."""
    global _DEFAULT
    if _DEFAULT is None:
        from . import config
        _DEFAULT = ProfileStore(
            config.PROFILE_SHEETS_DIR,
            expected_candidate_set=config.load_stamp()["candidate_set_id"])
    return _DEFAULT


def available() -> bool:
    return default_store().available()


def stamp() -> dict:
    store = default_store()
    store.verify()
    return store.stamp()


def get(level: str, code) -> dict | None:
    return default_store().get(level, code)


def sentences(level: str, code) -> list:
    return default_store().sentences(level, code)


def sentence(sentence_id: str) -> dict | None:
    return default_store().sentence(sentence_id)


def place(level: str, code) -> dict | None:
    return default_store().place(level, code)


def find(level: str, name) -> list:
    return default_store().find(level, name)
