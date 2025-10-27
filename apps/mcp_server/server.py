#!/usr/bin/env python3
import sys, json, traceback, pathlib, random, os, hashlib

# Ensure deterministic random for reproducible scoring
random.seed(int(os.getenv("SEED", "42")))

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.api.main import ScoreRequest, RUBRIC_PATH
from apps.pipeline.score_flow import ensure_ingested, embed_and_index, retrieve

def jsonrpc_response(id_, result=None, error=None):
    body = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        body["error"] = error
    else:
        body["result"] = result
    sys.stdout.write(json.dumps(body) + "\n")
    sys.stdout.flush()

def handle(method, params):
    if method == "esg.health":
        return {"status": "ok"}

    if method == "esg.compile_rubric":
        from rubrics.compile_rubric import compile_md_to_json
        md = pathlib.Path("/mnt/data/esg_maturity_rubric.md")
        out_json = ROOT / "rubrics/maturity_v1.json"
        ok = compile_md_to_json(md, out_json)
        return {"compiled": bool(ok), "output": str(out_json)}

    if method == "esg.score":
        import json as _json
        req = ScoreRequest(**params)
        if RUBRIC_PATH.exists():
            rubric = _json.loads(open(RUBRIC_PATH).read())
            themes = list(rubric["themes"].keys()) or ["General"]
        else:
            themes = ["General"]
        # Module-level seed is already set at import; re-seed per request for per-request determinism
        seed_val = int(hashlib.sha256((req.company + str(req.year)).encode()).hexdigest(), 16) % (2**32)
        random.seed(seed_val)
        decisions = []
        for t in themes:
            stage = random.randint(1,3)
            decisions.append({"theme": t, "stage": stage, "confidence": 0.6 + 0.1*stage,
                              "evidence":[{"quote":"Placeholder evidence.","page":1}]})
        overall = sum(d["stage"] for d in decisions)/len(decisions)
        return {"company": req.company, "year": req.year, "overall_stage": round(overall,2), "decisions": decisions}

    if method == "esg.ensure_ingested":
        company = params.get("company", "Acme Corp")
        year = int(params.get("year", 2024))
        chunks = ensure_ingested(company, year)
        return {"count": len(chunks), "chunks": chunks}

    if method == "esg.embed_index":
        chunks = params.get("chunks", [])
        embed_and_index(chunks)
        return {"indexed": len(chunks)}

    if method == "esg.retrieve":
        company = params.get("company", "Acme Corp")
        year = int(params.get("year", 2024))
        query = params.get("query", "ESG strategy")
        results = retrieve(company, year, query)
        return {"results": results}

    return {"_mcp_warning": f"Unknown method: {method}"}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            method = msg.get("method")
            params = msg.get("params", {}) or {}
            id_ = msg.get("id")
            result = handle(method, params)
            jsonrpc_response(id_, result=result)
        except Exception as e:
            tb = traceback.format_exc()
            jsonrpc_response(msg.get("id"), error={"code": -32000, "message": str(e), "data": tb})

if __name__ == "__main__":
    main()