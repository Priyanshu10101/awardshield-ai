"""cloud.py - Google Cloud Storage (input PDFs) and Firestore (results) for AwardShield.

Both are optional; with neither configured everything works on local files exactly as before.

Cloud Storage - the case's tender and bid PDFs
    A manifest's "assets_root" may be a gs:// URI (or AWARDSHIELD_ASSETS_URI overrides it for every
    case, e.g. gs://my-bucket/assets). Each entry ("rfp", "Bids/BID_1_GreenMetro.pdf") is then
    downloaded once into a local cache (AWARDSHIELD_CACHE_DIR, default <tmp>/awardshield-gcs) and
    the rest of the code reads those local copies. A changed object (new generation) is re-downloaded.

Firestore - the results
    The code keeps writing JSON files under output/<rfq_id>/ and data/state/<rfq_id>/ (the engine,
    RedSeal and the API read them there). push_case() mirrors those files into Firestore after a
    run; pull_case() / pull_all() write them back to disk - what Cloud Run needs, since its disk
    starts empty on every new instance.

    <collection>/{rfq_id}                    summary: title, winner, verdict, updated_at
    <collection>/{rfq_id}/files/{file_id}    one result file: area, path, json (text), data (map)

    Settings (config/truecost.json "firestore" block, or env):
      firestore.use         AWARDSHIELD_FIRESTORE             auto (on only inside Cloud Run) | true | false
      firestore.database    AWARDSHIELD_FIRESTORE_DATABASE    default "(default)"
      firestore.collection  AWARDSHIELD_FIRESTORE_COLLECTION  default "awardshield_cases"
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .settings import OUTPUT_DIR, STATE_DIR, setting

# ----------------------------------------------------------------------------
# Cloud Storage
# ----------------------------------------------------------------------------
CACHE_DIR = Path(os.getenv("AWARDSHIELD_CACHE_DIR") or Path(tempfile.gettempdir()) / "awardshield-gcs")
ASSETS_URI = os.getenv("AWARDSHIELD_ASSETS_URI", "")


def is_gcs(uri: str) -> bool:
    return str(uri).startswith("gs://")


def _split(uri: str) -> tuple[str, str]:
    bucket, _, prefix = uri[len("gs://"):].partition("/")
    return bucket, prefix.strip("/")


_storage_client = None


def _storage():
    global _storage_client
    if _storage_client is None:
        from google.cloud import storage  # pip install google-cloud-storage

        _storage_client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)
    return _storage_client


def _download(blob) -> Path:
    """Local copy of one object; downloaded again only when the object changed."""
    local = CACHE_DIR / blob.bucket.name / blob.name
    stamp = local.with_name(local.name + ".generation")
    if local.exists() and stamp.exists() and stamp.read_text() == str(blob.generation):
        return local
    local.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local))
    stamp.write_text(str(blob.generation))
    return local


def gcs_files(root_uri: str, entry: str) -> list[Path]:
    """One manifest entry under a gs:// root -> local PDF paths. Like the local version, an entry is
    either a single object or a folder (every .pdf directly or deeper under it)."""
    bucket_name, prefix = _split(root_uri.rstrip("/") + "/" + str(entry).strip("/"))
    bucket = _storage().bucket(bucket_name)
    single = bucket.get_blob(prefix)
    if single is not None:
        return [_download(single)]
    blobs = [b for b in _storage().list_blobs(bucket_name, prefix=prefix + "/")
             if b.name.lower().endswith(".pdf")]
    if not blobs:
        # keep the "documents not found" error of doc_reader meaningful
        return [CACHE_DIR / bucket_name / prefix]
    return sorted(_download(b) for b in blobs)


# ----------------------------------------------------------------------------
# Firestore
# ----------------------------------------------------------------------------
def firestore_enabled() -> bool:
    """auto = on only inside Cloud Run (K_SERVICE / CLOUD_RUN_JOB are set there), so a local run that
    sets GOOGLE_CLOUD_PROJECT just for Vertex AI keeps working on local files."""
    use = str(setting("firestore.use", "AWARDSHIELD_FIRESTORE", "auto")).lower()
    if use == "auto":
        return bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))
    return use in ("1", "true", "yes")


COLLECTION = setting("firestore.collection", "AWARDSHIELD_FIRESTORE_COLLECTION", "awardshield_cases")
_db_client = None


def _db():
    global _db_client
    if _db_client is None:
        from google.cloud import firestore  # pip install google-cloud-firestore

        _db_client = firestore.Client(
            project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
            database=setting("firestore.database", "AWARDSHIELD_FIRESTORE_DATABASE", "(default)"),
        )
    return _db_client


# the per-case files that are results (checkpoints stay local: they are a resume cache, not results)
_STATE_FILES = ("answers.json", "questions.json")
_MAX_BYTES = 900_000  # Firestore documents are limited to 1 MiB


def _areas(rfq_id: str) -> dict[str, Path]:
    return {"output": OUTPUT_DIR / rfq_id, "state": STATE_DIR / rfq_id}


def _local_files(rfq_id: str):
    areas = _areas(rfq_id)
    if areas["output"].exists():
        for p in sorted(areas["output"].rglob("*.json")):
            yield "output", p.relative_to(areas["output"]).as_posix(), p
    for name in _STATE_FILES:
        p = areas["state"] / name
        if p.exists():
            yield "state", name, p


def _file_id(area: str, rel: str) -> str:
    return f"{area}__{rel.replace('/', '__')}"  # '/' is not allowed in a document id


def _has_nested_list(x) -> bool:
    """Firestore cannot store a list directly inside a list."""
    if isinstance(x, dict):
        return any(_has_nested_list(v) for v in x.values())
    if isinstance(x, list):
        return any(isinstance(v, list) or _has_nested_list(v) for v in x)
    return False


def _summary(rfq_id: str) -> dict:
    out = OUTPUT_DIR / rfq_id

    def read(name):
        p = out / name
        try:
            return json.loads(p.read_text()) if p.exists() else {}
        except json.JSONDecodeError:
            return {}

    report, proof = read("report.json"), read("proof_pack.json")
    summary = {"rfq_id": rfq_id, "updated_at": datetime.now(timezone.utc)}
    if report:
        summary["ready_for_evaluation"] = report.get("ready_for_evaluation")
        summary["truecost_summary"] = report.get("summary")
    if proof:
        for k in ("status", "contested", "original_winner", "final_winner"):
            if k in proof:
                summary[f"verdict_{k}" if k != "status" else "verdict"] = proof[k]
    return summary


def push_case(rfq_id: str, title: str = "") -> int:
    """Like _push_case, but a Firestore error only prints a warning (the local files are kept)."""
    try:
        return _push_case(rfq_id, title)
    except Exception as e:  # noqa: BLE001 - a results mirror must never fail the run
        print(f"firestore: WARNING - could not save {rfq_id}: {e}")
        return 0


def _push_case(rfq_id: str, title: str = "") -> int:
    """Mirror output/<rfq_id>/**.json and the buyer answers / questions into Firestore.
    Returns the number of files written (unchanged files are skipped)."""
    if not firestore_enabled():
        return 0
    db = _db()
    case_ref = db.collection(COLLECTION).document(rfq_id)
    existing = {d.id: (d.to_dict() or {}).get("sha256") for d in case_ref.collection("files").stream()}
    batch, n, written = db.batch(), 0, 0
    for area, rel, path in _local_files(rfq_id):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        fid = _file_id(area, rel)
        if existing.get(fid) == digest:
            continue
        if len(raw) > _MAX_BYTES:
            print(f"firestore: skipped {area}/{rel} ({len(raw)} bytes, over the 1 MiB document limit)")
            continue
        text = raw.decode("utf-8")
        doc = {"area": area, "path": rel, "json": text, "sha256": digest,
               "updated_at": datetime.now(timezone.utc)}
        try:  # a native map too, so the results are browsable / queryable in the console
            data = json.loads(text)
            if isinstance(data, dict) and not _has_nested_list(data) and len(raw) < _MAX_BYTES // 2:
                doc["data"] = data
        except json.JSONDecodeError:
            pass
        batch.set(case_ref.collection("files").document(fid), doc)
        n += 1
        written += 1
        if n == 400:  # a batch takes at most 500 writes
            batch.commit()
            batch, n = db.batch(), 0
    summary = _summary(rfq_id)
    if title:
        summary["title"] = title
    batch.set(case_ref, summary, merge=True)
    batch.commit()
    print(f"firestore: {written} file(s) of {rfq_id} saved to {COLLECTION}/{rfq_id}")
    return written


def pull_case(rfq_id: str) -> int:
    """Like _pull_case, but a Firestore error only prints a warning (the local files are used)."""
    try:
        return _pull_case(rfq_id)
    except Exception as e:  # noqa: BLE001
        print(f"firestore: WARNING - could not load {rfq_id}: {e}")
        return 0


def _pull_case(rfq_id: str) -> int:
    """Write the case's files from Firestore to disk (only files whose content differs, so the
    API's cache keyed on file mtimes is not invalidated for nothing). Returns files written."""
    if not firestore_enabled():
        return 0
    areas = _areas(rfq_id)
    written = 0
    for d in _db().collection(COLLECTION).document(rfq_id).collection("files").stream():
        f = d.to_dict() or {}
        base = areas.get(f.get("area", ""))
        rel = f.get("path", "")
        if base is None or not rel or ".." in rel.split("/"):
            continue
        path = base / rel
        text = f.get("json", "")
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written += 1
    return written


_last_pull = 0.0


def pull_all(min_interval_s: float = 30.0) -> None:
    """Every case in Firestore -> disk; at most once per min_interval_s (the API calls it per request)."""
    global _last_pull
    if not firestore_enabled() or time.time() - _last_pull < min_interval_s:
        return
    _last_pull = time.time()
    try:
        ids = [ref.id for ref in _db().collection(COLLECTION).list_documents()]
    except Exception as e:  # noqa: BLE001 - the website keeps serving the files it has
        print(f"firestore: WARNING - could not list cases: {e}")
        return
    for rfq_id in ids:
        pull_case(rfq_id)
