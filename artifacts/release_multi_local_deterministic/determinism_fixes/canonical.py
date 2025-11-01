from __future__ import annotations
import json, hashlib
def canonical_hash(obj)->str:
    s=json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',',':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()
