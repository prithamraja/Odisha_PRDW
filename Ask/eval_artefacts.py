"""Where an eval harness writes while it is running (D31.7, WP-4c 3.5).

THE ARTEFACT THIS CLOSES. This repo lives in a Google Drive folder (D6). All
three of WP-4c's results files were damaged by the sync layer, and the shape of
the damage says exactly what did it: replay 1 came back with one record written
twice and an orphan fragment in the middle; replay 2 lost FOUR questions to two
unrecoverable fragments. `run_full_eval` appends one JSON line per question and
flushes on every one — a flush-per-line file inside a folder something else is
continuously uploading and rewriting underneath it.

WP-4c hardened the READER (`grade_full_eval.read_records` repairs split lines
and duplicated writes) and made the writer rewrite the whole file from memory at
the end. Both were right and neither is the fix: the reader is repairing damage
that should never have been written, and the rewrite only helps a run that
reaches its own last line.

THE FIX IS THE PATH. Stream to a LOCAL temporary file, on a disk with no sync
layer on it, and copy the finished artefact into the repo in one operation once
the run is over. The repo path is still where the file ends up — nothing about
how the artefacts are read or named changes — but nothing is ever written into
a synced folder a line at a time.

PRDW_EVAL_SCRATCH overrides the scratch directory; the default is the platform
temp directory, which is local on every machine this has run on.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

SCRATCH_ENV = "PRDW_EVAL_SCRATCH"


def scratch_dir() -> Path:
    """A local directory to stream into. Created if it does not exist."""
    root = Path(os.environ.get(SCRATCH_ENV)
                or Path(tempfile.gettempdir()) / "prdw_eval")
    root.mkdir(parents=True, exist_ok=True)
    return root


def local_twin(final_path: Path) -> Path:
    """The scratch path a given repo artefact is streamed to."""
    return scratch_dir() / final_path.name


def publish(local_path: Path, final_path: Path) -> Path:
    """Copy a finished artefact into the repo, in ONE operation."""
    final_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_path, final_path)
    return final_path


@contextmanager
def streamed_artefact(final_path: Path, mode: str = "w", **kwargs):
    """Open a LOCAL file to stream into; copy it to `final_path` on exit.

    The copy happens even when the body raises, because a partial replay is
    still evidence — losing it would trade one failure mode for another.
    """
    local = local_twin(final_path)
    handle = local.open(mode, **kwargs)
    try:
        yield handle
    finally:
        try:
            handle.close()
        finally:
            if local.exists():
                publish(local, final_path)


@contextmanager
def appended_artefact(final_path: Path, mode: str = "a", **kwargs):
    """Like `streamed_artefact`, for a file that is APPENDED to and resumable.

    `run_consistency_eval` is append-only and keyed on (run, question), so a
    replay that already ran is skipped rather than repeated — which means the
    existing repo copy is INPUT as well as output. It is copied to the scratch
    disk first, appended to there, and copied back when the run ends.
    """
    local = local_twin(final_path)
    if final_path.exists():
        shutil.copyfile(final_path, local)
    elif local.exists():
        local.unlink()
    handle = local.open(mode, **kwargs)
    try:
        yield handle
    finally:
        try:
            handle.close()
        finally:
            if local.exists():
                publish(local, final_path)
