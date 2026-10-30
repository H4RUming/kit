#!/usr/bin/env python3
"""q: 출력이 긴 명령을 조용히 실행한다. 전체 로그는 파일에, 화면에는 요약만. 표준 라이브러리만 사용.

사용:
  python3 q.py -- pip install -r requirements.txt
  python3 q.py --tail 30 -- python3 scripts/build_report.py
  python3 q.py --grep "KeyError|row" -- python3 run.py

출력: 종료 코드, 시간, 총 줄 수, 로그 경로, 에러로 보이는 줄(최대 15), 마지막 N줄(기본 15).
전체 로그가 필요하면 출력된 로그 경로에서 rg나 sed -n 으로 필요한 부분만 본다.
"""
import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / ".state" / "logs"
ERR = re.compile(r"(error|exception|traceback|failed|fatal|not found|denied|refused|cannot|errno)", re.I)


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--")
    opts, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=None, help="마지막 N줄 (기본: 실패 15, 성공 5)")
    ap.add_argument("--grep", help="추가로 보여줄 줄의 정규식")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args(opts)
    if not cmd:
        print("명령이 없음")
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]", "_", Path(cmd[0]).name)[:20]
    stamp = f"{datetime.now():%H%M%S_%f}"[:10]
    log = LOG_DIR / f"{stamp}_{name}.log"
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        code = -1
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out += f"\n[q] {a.timeout}s 시간 초과. 서버처럼 계속 도는 프로세스는 q로 돌리지 말 것.\n"
    except FileNotFoundError:
        print(f"[FAIL] 명령을 찾을 수 없음: {cmd[0]}")
        return 127
    secs = time.time() - t0
    log.write_text(f"$ {' '.join(cmd)}\n{out}", encoding="utf-8")

    lines = out.rstrip().splitlines()
    status = "OK" if code == 0 else ("TIMEOUT" if code == -1 else "FAIL")
    try:
        shown_log = log.relative_to(Path.cwd())
    except ValueError:
        shown_log = log
    print(f"[{status}] exit={code} {secs:.1f}s lines={len(lines)} log={shown_log}")

    ntail = a.tail if a.tail is not None else (5 if code == 0 else 15)
    tail_start = max(1, len(lines) - ntail + 1)
    errs = [f"  L{n}: {l.strip()[:200]}" for n, l in enumerate(lines, 1)
            if ERR.search(l) and n < tail_start]
    if a.grep:
        g = re.compile(a.grep)
        errs += [f"  L{n}: {l.strip()[:200]}" for n, l in enumerate(lines, 1)
                 if g.search(l) and n < tail_start]
    if errs and code != 0:
        uniq = list(dict.fromkeys(errs))
        print(f"  마지막 줄들 앞쪽에서 에러로 보이는 줄 {len(uniq)}개" + (" (앞 15개)" if len(uniq) > 15 else ""))
        print("\n".join(uniq[:15]))
    elif a.grep and errs:
        print("\n".join(list(dict.fromkeys(errs))[:15]))
    if lines:
        tail = lines[-ntail:]
        if len(lines) > ntail:
            print(f"  --- 마지막 {len(tail)}줄 ---")
        print("\n".join(tail))
    return code if code >= 0 else 124


if __name__ == "__main__":
    sys.exit(main())
