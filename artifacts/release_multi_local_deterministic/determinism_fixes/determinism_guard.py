from __future__ import annotations
import os, random
try:
    import numpy as np
except Exception:
    np=None

def enforce():
    os.environ.setdefault("PYTHONHASHSEED","0")
    random.seed(42)
    if np is not None:
        np.random.seed(42)
    # call this at the start of scoring/demo entrypoints, then sort/normalize inputs deterministically.
