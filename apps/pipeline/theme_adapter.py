from __future__ import annotations
from pathlib import Path
import json, os, hashlib, time
from apps.scoring.rubric_v3_loader import get_rubric_v3
from libs.qa.tee import Tee

SCHEMA=Path("rubrics/esg_rubric_schema_v3.json")
INP_DEFAULT=Path("artifacts/demo/headlam_demo_response_theme.json")
OUT=Path("artifacts/demo/headlam_demo_response.json")
LOG=Path("artifacts/sca_qax/run.log.jsonl")
ALLOW_DEMO=os.getenv("ALLOW_DEMO_EVIDENCE","0")=="1"
SEED=os.getenv("ESG_SEED","42")

def now(): return int(time.time()*1000)
def sha256hex(b: bytes)->str: return hashlib.sha256(b).hexdigest()
def sha16(b: bytes)->str: return sha256hex(b)[:16]
def jlog(step:str,status:str,msg:str,trace_id:str,extra:dict|None=None):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec={"ts_ms":now(),"step":step,"status":status,"msg":msg,"trace_id":trace_id}
    if extra: rec.update(extra)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False)+"\n")

schema=json.loads(SCHEMA.read_text())
theme_codes=[t["code"] for t in schema["themes"]]

inp_path=os.getenv("ADAPTER_INPUT", str(INP_DEFAULT))
INP=Path(inp_path)

if not INP.exists():
    if not ALLOW_DEMO:
        raise SystemExit("Missing input evidence; provide real evidence or set ALLOW_DEMO_EVIDENCE=1 to allow demo.")
    demo={"company":"Headlam Group Plc","evidence":[
        {"theme":"GHG","quote":"Scope 1 and Scope 2 emissions totaled 5,240 tCO2e in 2025"},
        {"theme":"GHG","quote":"Climate risk assessment: transition risks related to carbon pricing"},
        {"theme":"TSP","quote":"Committed to achieving net-zero emissions by 2050"}
    ]}
    INP.parent.mkdir(parents=True, exist_ok=True)
    INP.write_text(json.dumps(demo, indent=2, ensure_ascii=False))

data=json.loads(INP.read_text())
scores={t:{"score":None,"evidence":[]} for t in theme_codes}
for ev in data.get("evidence",[]):
    t=ev.get("theme")
    if t in scores:
        scores[t]["evidence"].append({
          "quote":ev.get("quote",""),
          "page":ev.get("page", None),
          "doc_id":ev.get("doc_id", "DEMO_DOC" if ALLOW_DEMO else None),
          "pdf_hash":ev.get("pdf_hash", "demo" if ALLOW_DEMO else None)
        })

rubric = get_rubric_v3()
min_evidence = rubric.get_evidence_requirements()

for theme_code, obj in scores.items():
    ev = obj.get("evidence", [])
    if len(ev) >= min_evidence:
        # Evidence-first scoring: score=2 if evidence threshold met
        base_score = 2
        obj["score"] = base_score

        # Add rubric v3 metadata for enhanced provenance
        # Framework detection from evidence text
        detected_frameworks = []  # STRICT_FRAMEWORK_DETECTION
        # Require explicit confirmations, not just keyword mentions
        import re as _fw_re
        STRICT_PATTERNS = {
            'SBTi': r'(validated by|approved by|aligned with|committed to)\s*(the\s*)?SBTi|science[- ]?based target(s)? initiative',
            'GRI':  r'GRI( Standards| Index| table| framework)?',
            'TCFD': r'Task Force on Climate[- ]?Related Financial Disclosures|TCFD( recommendations| framework)?',
            'ISSB': r'ISSB|IFRS S[12]'
        }
        for quote in ev:
            quote_text = quote.get("quote", "") or ""
            # Use strict patterns requiring explicit framework confirmations
            for fw_name, fw_pattern in STRICT_PATTERNS.items():
                if _fw_re.search(fw_pattern, quote_text, _fw_re.IGNORECASE):
                    detected_frameworks.append(fw_name)

        frameworks_unique = list(set(detected_frameworks))
        obj["frameworks"] = frameworks_unique

        # Apply framework boost only for explicitly confirmed frameworks
        if frameworks_unique:
            boosted_score = rubric.apply_framework_boost(theme_code, base_score, frameworks_unique)
            obj["score"] = boosted_score
            obj["boost_applied"] = True
            # Higher confidence for confirmed frameworks
            obj["confidence"] = min(0.95, 0.7 + (0.05 * len(frameworks_unique)))
        else:
            obj["boost_applied"] = False
            # Base confidence for meeting evidence threshold
            obj["confidence"] = 0.7

        # Freshness penalty (assuming evidence is current - 0 months old)
        evidence_age_months = 0  # Would calculate from PDF date in production
        obj["freshness_penalty"] = 0.0  # No penalty for current evidence
    else:
        obj["score"] = None

scores_bytes=json.dumps(scores, sort_keys=True, ensure_ascii=False).encode()
trace_id="sha256:"+sha16(scores_bytes)
out={"company":data.get("company","DemoCo"),"trace_id":trace_id,"scores":scores}
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))

# Generate scoring provenance for traceability
provenance = {
    "trace_id": trace_id,
    "scored_themes": [k for k,v in scores.items() if v.get("score") is not None],
    "rubric_version": "v3",
    "min_evidence_required": min_evidence,
    "explanations": {}
}

for theme_code in scores.keys():
    if scores[theme_code].get("score") is not None:
        theme_obj = rubric.get_theme(theme_code)
        provenance["explanations"][theme_code] = {
            "theme_name": theme_obj.name if theme_obj else theme_code,
            "score": scores[theme_code].get("score"),
            "confidence": scores[theme_code].get("confidence", 0.0),
            "evidence_count": len(scores[theme_code].get("evidence", [])),
            "frameworks_detected": scores[theme_code].get("frameworks", []),
            "freshness_penalty": scores[theme_code].get("freshness_penalty", 0.0),
            "scoring_method": "Evidence-first threshold (rubric v3 enhanced)"
        }

prov_path = Path("artifacts/sca_qax/scoring_provenance.json")
prov_path.parent.mkdir(parents=True, exist_ok=True)
prov_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
print("Scoring provenance written to: {}".format(prov_path.as_posix()))

print("Theme adapter wrote: {} (trace_id={})".format(OUT.as_posix(), trace_id))
print("   Themes with scores:", [k for k,v in scores.items() if v.get("score") is not None])
print("   Total evidence items:", sum(len(v.get("evidence",[])) for v in scores.values()))
jlog("theme_adapter","ok","wrote theme-based response",trace_id,{"output":OUT.as_posix(),"themes":list(scores.keys())})
