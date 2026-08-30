#!/usr/bin/env python
"""책 『지금에 모인 미래』 생성. BRIEF_OUTPUT_DIR 이 있으면 그쪽에, 없으면 report/ 에."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

from bookgen.build import build

outdir = Path(__file__).resolve().parent / (os.getenv("BRIEF_OUTPUT_DIR") or "report")
outdir.mkdir(parents=True, exist_ok=True)
n = build(outdir)
print(f"책 생성 완료: {n}편 → {outdir / 'book'}")
