from __future__ import annotations
import argparse, json, pathlib, subprocess, sys
import yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agents.crawler.provider_local import discover_from_config, materialize_bronze

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/companies_local.yaml")
    ap.add_argument("--chunk-size", type=int, default=1000)
    ap.add_argument("--chunk-overlap", type=int, default=200)
    args=ap.parse_args()
    cfg=yaml.safe_load(pathlib.Path(args.config).read_text(encoding="utf-8"))
    docs=discover_from_config(cfg)
    if not docs: print("no local PDFs discovered", file=sys.stderr); return 2
    bronze=[]
    for d in docs:
        bronze.append(materialize_bronze(d))
        cmd=[sys.executable,"scripts/ingest_single_doc.py","--org-id",d.org_id,"--year",str(d.year),
             "--pdf-path",d.pdf_path,"--source-url",d.source_url,
             "--chunk-size",str(args.chunk_size),"--chunk-overlap",str(args.chunk_overlap)]
        subprocess.check_call(cmd)
    pathlib.Path("artifacts/ingestion").mkdir(parents=True, exist_ok=True)
    pathlib.Path("artifacts/ingestion/local_bronze_manifest.json").write_text(json.dumps(bronze,indent=2),encoding="utf-8")
    print(json.dumps({"status":"ok","ingested":len(bronze)}))
if __name__=="__main__": sys.exit(main())
