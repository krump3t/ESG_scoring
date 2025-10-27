from typing import Dict, Any, List
from ..scoring.wx_client import embed_text_batch, extract_findings, classify_theme
from ..index.vector_store import VectorStore
from ..index.graph_store import GraphStore
from ..index.retriever import HybridRetriever

VS = VectorStore()
GS = GraphStore()
RETR = HybridRetriever(VS, GS)

def ensure_ingested(company: str, year: int) -> List[Dict[str, Any]]:
    return [
        {"chunk_id": f"{company}-{year}-1", "company": company, "year": year, "text": f"{company} {year} ESG strategy and targets.", "page_start": 1, "section": "Executive Summary"},
        {"chunk_id": f"{company}-{year}-2", "company": company, "year": year, "text": "GHG inventory includes Scopes 1 and 2.", "page_start": 2, "section": "GHG Accounting"},
    ]

def embed_and_index(chunks: List[Dict[str, Any]]) -> None:
    vecs = embed_text_batch([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        VS.upsert(c["chunk_id"], v, {"company": c["company"], "year": c["year"], "section": c.get("section","")})

def retrieve(company: str, year: int, query_text: str) -> List[Dict[str, Any]]:
    qv = embed_text_batch([query_text])[0]
    results = RETR.retrieve(qv, k=5, where={"company": company, "year": year})
    return results

def grade(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    findings = extract_findings(chunks, theme="General", rubric={})
    decision = classify_theme(findings, theme="General", rubric={})
    return {"findings": findings, "decisions": [decision]}
