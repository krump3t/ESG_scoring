import json, re
from pathlib import Path

def compile_md_to_json(md_path: Path, out_json: Path):
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        themes = {}
        for m in re.finditer(r"^##\s+\d+\.\s+(.+)$", text, flags=re.M):
            theme = m.group(1).strip()
            themes[theme] = {"stages": ["0","1","2","3","4"]}
        obj = {"version": "1.0-md", "themes": themes}
        out_json.write_text(json.dumps(obj, indent=2))
        return True
    return False

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    md = Path("/mnt/data/esg_maturity_rubric.md")
    out_json = base / "rubrics/maturity_v1.json"
    if not compile_md_to_json(md, out_json):
        print("No MD rubric found; keeping existing JSON.")
