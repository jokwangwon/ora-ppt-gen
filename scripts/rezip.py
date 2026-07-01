#!/usr/bin/env python3
"""pptxgenjs 출력 .pptx 재압축.

pptxgenjs는 무압축 ZIP(빈 디렉터리 스텁 포함)으로 파일을 써서 용량이 크다.
이 스크립트로 표준 압축(deflate)으로 다시 묶어 크기를 줄인다.

사용법: python scripts/rezip.py out/deck.pptx
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def rezip(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as z:
        names = [n for n in z.namelist() if not n.endswith("/")]  # 디렉터리 스텁 제외
        items = [(n, z.read(n)) for n in names]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # [Content_Types].xml 는 맨 앞에 오는 것이 관례
        items.sort(key=lambda kv: (kv[0] != "[Content_Types].xml", kv[0]))
        for name, data in items:
            z.writestr(name, data)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("사용법: python scripts/rezip.py <file.pptx>", file=sys.stderr)
        return 1
    p = Path(argv[1])
    before = p.stat().st_size
    rezip(p)
    after = p.stat().st_size
    print(f"[rezip] {p.name}: {before:,} → {after:,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
