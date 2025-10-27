from typing import List, Dict
from .wx_client import extract_findings as wx_extract_findings, classify_theme as wx_classify_theme

def extract_evidence(chunks: List[dict]) -> List[Dict]:
    return wx_extract_findings(chunks, theme="General", rubric={})

def classify_maturity(findings: List[Dict]) -> List[Dict]:
    themes = {"General": findings}
    decisions = []
    for theme, fs in themes.items():
        d = wx_classify_theme(fs, theme=theme, rubric={})
        decisions.append({"theme": d["theme"], "stage": d["stage"], "confidence": d["confidence"]})
    return decisions
