"""doc_reader.py - case manifest -> labelled documents -> Gemini message
parts.

No extraction here: the extractor sub-agents read the PDFs themselves. Each
document goes to the
model behind a header line it cites as evidence:
  --- DOCUMENT (BID of GreenMetro, commercial): BID_1_GreenMetro.pdf ---

All documents travel in ONE user message; only_documents(...) is the before_model_callback that
hides the documents a sub-agent must not see (another bidder's bid, or the tender).
"""

import hashlib
import json
from functools import cached_property
from pathlib import Path

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from pydantic import BaseModel, model_validator

from .settings import CONFIG_DIR, ROOT


class Document(BaseModel, frozen=True):
    path: Path
    supplier: str = ""  # "" = tender document
    kind: str = "rfp"   # rfp | commercial | technical | psa

    @property
    def header(self) -> str:
        who = f"BID of {self.supplier}, {self.kind}" if self.supplier else "TENDER / RFP"
        return f"--- DOCUMENT ({who}): {self.path.name} ---"


class Supplier(BaseModel):
    name: str
    commercial: list[Path] = []
    technical: list[Path] = []
    psa: list[Path] = []


class Case(BaseModel):
    """The manifest itself (config/projects/<COUNTRY>/<RFQ_ID>.manifest.
    json); extra keys are ignored."""
    rfq_id: str
    title: str = ""
    country: str
    currency: str
    assets_root: str = "."  # a local folder (relative to the workspace root) or gs://bucket/prefix
    rfp_documents: list[Path]
    suppliers: list[Supplier]

    @classmethod
    def load(cls, arg: str) -> "Case":
        """Load a manifest by path or by its rfq_id under the config directory."""
        path = Path(arg) if Path(arg).is_file() else None
        if path is None:
            for candidate in CONFIG_DIR.rglob("*.json"):
                try:
                    manifest = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if manifest.get("rfq_id") == arg:
                    path = candidate
                    break
        if path is None:
            raise SystemExit(f"manifest '{arg}' not found under {CONFIG_DIR}")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def _files(self, entry: Path) -> list[Path]:
        """An entry is a file or a folder (every PDF in it); relative to
        assets_root. With a gs:// root (or AWARDSHIELD_ASSETS_URI) the PDFs are downloaded from
        Cloud Storage into a local cache first (cloud.py)."""
        from .cloud import ASSETS_URI, gcs_files, is_gcs

        root = ASSETS_URI or self.assets_root
        if is_gcs(root):
            return gcs_files(root, entry.as_posix())
        p = ROOT / root / entry  # an absolute entry overrides the root
        return sorted(p.glob("*.pdf")) if p.is_dir() else [p]

    @cached_property
    def documents(self) -> list[Document]:
        docs = [Document(path=p) for e in self.rfp_documents for p in self._files(e)]
        for s in self.suppliers:
            for kind in ("commercial", "technical", "psa"):
                docs += [
                    Document(path=p, supplier=s.name, kind=kind)
                    for e in getattr(s, kind)
                    for p in self._files(e)
                ]
        return docs

    @model_validator(mode="after")
    def _files_exist(self) -> "Case":
        if missing := [str(d.path) for d in self.documents if not d.path.exists()]:
            raise ValueError(f"documents not found: {missing}")
        if not any (not d.supplier for d in self.documents):
            raise ValueError("no tender document: rfp_documents is empty or its folder has no pdf")
        return self

    @property
    def supplier_names(self) -> list[str]:
        return [s.name for s in self.suppliers]

    def of(self, supplier: str) -> list[Document]:
        """The tender + ONE supplier's documents (what a per-supplier
        extractor reads)."""
        return [d for d in self.documents if d.supplier in ("", supplier)]


def pack(docs: list[Document]) -> list[types.Part]:
    """Header line + raw PDF bytes per document (Gemini reads PDFs natively,
    scans included)."""
    return [
        part
        for d in docs
        for part in (
            types.Part(text=d.header),
            types.Part.from_bytes(
                data=d.path.read_bytes(),
                mime_type="application/pdf",
            ),
        )
    ]


DOCUMENT_HEADER = "--- DOCUMENT ("
TENDER_HEADER = "--- DOCUMENT (TENDER / RFP)"


def only_documents(tender: bool, supplier: str = ""):
    """before_model_callback: drop every document the agent must not see.

    A document is a text part starting '--- DOCUMENT (' plus the parts after it, up to the next
    such header (or the end of that message). The tender is kept only if `tender`; a bid only
    if it is `supplier`'s. Every other part (intro text, earlier agents' replies) is kept.
    """
    own_bid = f"{DOCUMENT_HEADER}BID of {supplier}, "

    def visible(header: str) -> bool:
        if header.startswith(TENDER_HEADER):
            return tender
        if header.startswith(f"{DOCUMENT_HEADER}BID of "):
            return bool(supplier) and header.startswith(own_bid)
        return True

    def callback(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
        contents = []
        for content in llm_request.contents:
            keep, parts = True, []
            for part in content.parts or []:
                if part.text and part.text.startswith(DOCUMENT_HEADER):
                    keep = visible(part.text)
                if keep:
                    parts.append(part)
            if parts:
                contents.append(content.model_copy(update={"parts": parts}))
        llm_request.contents = contents
        return None

    return callback


def docs_hash(docs: list[Document]) -> str:
    """Same files -> same hash (extraction cache key)."""
    h = hashlib.sha256()
    for d in docs:
        h.update(d.path.name.encode() + d.path.read_bytes())
    return h.hexdigest()[:20]


def read_pdf_text(path: Path) -> str:
    """Text layer per page - checks.py uses it to verify the model's quotes.
    """
    from pypdf import PdfReader
    return "\n".join(
        f"[page {i}]\n{p.extract_text() or ''}"
        for i, p in enumerate(PdfReader(path).pages, 1)
    )
