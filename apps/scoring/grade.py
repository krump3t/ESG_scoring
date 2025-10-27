from typing import List, Dict
from .watsonx_client import extract_evidence, classify_maturity

def grade_from_chunks(chunks: List[Dict]) -> Dict:
    findings = extract_evidence(chunks)
    decisions = classify_maturity(findings)
    overall = sum(d["stage"] for d in decisions)/len(decisions) if decisions else 0
    return {"decisions": decisions, "overall": overall, "findings": findings}
