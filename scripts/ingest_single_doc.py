from __future__ import annotations
import argparse, json, os, pathlib, sys, hashlib
DETERMINISTIC_TS="2025-10-28T06:00:00Z"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agents.extraction.enhanced_pdf_extractor import extract_document  # real extractor

def _sha256_text(t:str)->str: return hashlib.sha256(t.encode("utf-8")).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--org-id", required=True); ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--pdf-path", required=True); ap.add_argument("--source-url", required=True)
    ap.add_argument("--chunk-size", type=int, default=1000); ap.add_argument("--chunk-overlap", type=int, default=200)
    a=ap.parse_args()
    doc_id=f"{a.org_id}_{a.year}"
    out_dir=pathlib.Path(f"data/silver/org_id={a.org_id}/year={a.year}"); out_dir.mkdir(parents=True, exist_ok=True)

    # Use real extractor - extract_document returns list of dicts
    chunks=extract_document(a.pdf_path, source_url=a.source_url, provider="local", chunk_size=a.chunk_size)
    norm=[]
    for i,ch in enumerate(chunks):
        t=(ch.get("text") or ch.get("extract_30w") or "").strip()
        if not t: continue
        page=int(ch.get("page", ch.get("page_no",1))); section=ch.get("section") or ""
        norm.append({
            "id": f"{doc_id}_p{page}_c{i}", "doc_id": doc_id, "org_id": a.org_id, "year": a.year,
            "page": page, "section": section, "text": t, "sha256_raw": _sha256_text(t),
            "source_url": a.source_url, "ts": DETERMINISTIC_TS
        })
    jsonl=out_dir/f"{doc_id}_chunks.jsonl"
    with open(jsonl,"w",encoding="utf-8") as f:
        for it in norm: f.write(json.dumps(it, ensure_ascii=False)+"\n")
    try:
        import pandas as pd; pd.DataFrame(norm).to_parquet(out_dir/f"{doc_id}_chunks.parquet", index=False)
    except Exception as e: print(f"[warn] parquet not written: {e}", file=sys.stderr)
    mani={"status":"ok" if norm else "empty","doc_id":doc_id,"org_id":a.org_id,"year":a.year,
          "pdf_path":os.path.abspath(a.pdf_path),"chunks":len(norm),"ts":DETERMINISTIC_TS}
    (out_dir/"ingestion_manifest.json").write_text(json.dumps(mani,indent=2),encoding="utf-8")
    print(json.dumps(mani)); return 0

if __name__=="__main__": sys.exit(main())
