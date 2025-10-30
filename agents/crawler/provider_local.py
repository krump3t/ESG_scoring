from __future__ import annotations
import hashlib, os, pathlib
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class LocalDoc:
    org_id: str
    year: int
    pdf_path: str
    source_url: str

def _sha256_path(p: str) -> str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()

def discover_from_config(companies_yaml: Dict[str, Any]) -> List[LocalDoc]:
    out: List[LocalDoc] = []
    for e in companies_yaml.get("companies", []):
        if e.get("provider") == "local":
            # Skip if no pdf_path (already processed)
            if "pdf_path" not in e:
                continue
            pdf = pathlib.Path(e["pdf_path"])
            if pdf.exists() and pdf.suffix.lower()==".pdf":
                out.append(LocalDoc(e["org_id"], int(e["year"]), str(pdf), e.get("source_url","file://"+str(pdf.resolve()))))
    return out

def materialize_bronze(ld: LocalDoc) -> Dict[str, Any]:
    s=os.stat(ld.pdf_path)
    return {
        "phase":"bronze","org_id":ld.org_id,"year":ld.year,
        "path": os.path.abspath(ld.pdf_path),
        "sha256": _sha256_path(ld.pdf_path),
        "bytes": s.st_size, "mtime": int(s.st_mtime),
        "source_url": ld.source_url, "ts": "2025-10-28T06:00:00Z"
    }
