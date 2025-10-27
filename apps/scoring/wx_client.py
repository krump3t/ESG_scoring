from typing import List, Dict
import math, random, hashlib

def embed_text_batch(texts: List[str]) -> List[List[float]]:
    vecs = []
    for t in texts:
        # Use stable hash instead of Python's non-deterministic hash()
        seed = int.from_bytes(hashlib.sha256(t.encode('utf-8')).digest()[:4], 'big')
        random.seed(seed)
        vecs.append([random.random() for _ in range(16)])
    return vecs

def extract_findings(chunks: List[Dict], theme: str, rubric: Dict) -> List[Dict]:
    findings = []
    for ch in chunks:
        snippet = ch.get("text","")[:80]
        findings.append({
            "chunk_id": ch.get("chunk_id",""),
            "quote": snippet,
            "page": ch.get("page_start",1),
            "section": ch.get("section",""),
            "theme": theme,
            "signals": ["generic_claim"]
        })
    return findings

def classify_theme(findings: List[Dict], theme: str, rubric: Dict) -> Dict:
    n = len(findings)
    stage = min(4, max(1, math.ceil(n/2)))
    return {
        "theme": theme,
        "stage": stage,
        "confidence": 0.5 + 0.1*stage,
        "rationale": f"Stage based on {n} findings and rubric heuristics."
    }
