#!/usr/bin/env python3
"""t: 테스트를 돌리고 요약만 출력한다. 표준 라이브러리만 사용.

사용:
  python3 t.py                      테스트 명령 자동 감지 후 실행
  python3 t.py -- pytest -q tests/  명령 직접 지정
  python3 t.py --note "C1 경계값" -- python3 -m unittest test_rules

출력: 통과면 한 줄, 실패면 실패 요약과 마지막 N줄.
기록: 실행할 때마다 work/VERIFY.md에 한 줄 추가 (--no-log로 끔).
반복 방지:
  - 직전 실행 이후 바뀐 파일이 없고 명령도 같으면 다시 돌리지 않고 [SAME]과 직전 결과만 출력 (--force로 강제 실행)
  - 코드가 바뀌었는데 같은 실패가 연속되면 [경고]를 출력
종료 코드: 0 통과, 1 실패, 2 테스트 0개 또는 시간 초과 (통과로 읽으면 안 됨).
"""
import hashlib
import os
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SKIP = ("node_modules", ".venv", "venv", ".kit", ".git", "__pycache__", ".pytest_cache",
        Path(__file__).resolve().parent.parent.name)  # 키트 폴더 이름이 달라도 제외
STATE = Path(__file__).resolve().parent.parent / ".state" / "t.json"
IGNORE_FILES = {"VERIFY.md", "HANDOFF.md", "DECISIONS.md", "TASK.md"}
WORK_DIR = "work"  # 작업 문서 폴더. 지문 계산에서 제외


CODE_EXT = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".html", ".htm",
            ".css", ".scss", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".sql", ".sh", ".env.example")


def fingerprint(code_only=False):
    """작업 폴더 파일의 경로, 크기, 수정 시각으로 만든 해시. 문서 파일은 제외.
    code_only=True면 소스 파일만 본다 (서버가 쓰는 DB, 로그, 출력 파일 변화는 무시)."""
    h = hashlib.sha1()
    n = 0
    for dp, dns, fns in os.walk("."):
        dns[:] = sorted(d for d in dns if d not in SKIP and not (dp == "." and d == WORK_DIR))
        for f in sorted(fns):
            if f in IGNORE_FILES or f.endswith((".pyc", ".log")):
                continue
            if code_only and not f.endswith(CODE_EXT):
                continue
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            h.update(f"{p}|{st.st_size}|{st.st_mtime_ns}\n".encode())
            n += 1
            if n > 20000:
                return None
    return h.hexdigest()


def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(st):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(st, ensure_ascii=False))
    except OSError:
        pass


def fail_signature(summary, out):
    failed = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M)))
    return summary.split(" in ")[0] + "|" + ",".join(failed)


def has_py_tests():
    for p in Path(".").rglob("*.py"):
        if any(s in p.parts for s in SKIP):
            continue
        if p.name.startswith("test_") or p.name.endswith("_test.py"):
            return True
    return False


def detect():
    if has_py_tests():
        if importlib.util.find_spec("pytest"):
            return [sys.executable, "-m", "pytest", "-q", "-rfE", "--tb=short", "--no-header", "-p", "no:cacheprovider"]
        return [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test*.py"]
    pkg = Path("package.json")
    if pkg.exists() and shutil.which("npm"):
        try:
            if "test" in json.loads(pkg.read_text()).get("scripts", {}):
                return ["npm", "test", "--silent"]
        except (ValueError, OSError):
            pass
    return None


def summarize(cmd, code, out):
    lines = [l for l in out.splitlines() if l.strip()]
    text = "\n".join(lines[-15:])
    is_pytest = "pytest" in " ".join(cmd)
    if is_pytest:
        if code == 5:
            return "NO-TESTS", "pytest: 수집된 테스트 0개"
        m = [l for l in lines if re.search(r"\d+ (passed|failed|error|errors|skipped)", l)]
        s = m[-1].strip("= ").strip() if m else (lines[-1] if lines else "")
        if code == 0 and re.search(r"\bpassed\b", s) is None:
            return "NO-TESTS", s or "통과한 테스트 없음 (전부 skip?)"
        return ("PASS" if code == 0 else "FAIL"), s
    ran = re.findall(r"Ran (\d+) tests?", out)
    if ran:
        n = int(ran[-1])
        tail = next((l for l in reversed(lines) if l.startswith(("OK", "FAILED"))), "")
        if n == 0:
            return "NO-TESTS", "unittest: Ran 0 tests"
        if code == 0 and "skipped=" in tail and re.search(rf"skipped={n}\b", tail):
            return "NO-TESTS", f"Ran {n}, 전부 skip"
        return ("PASS" if code == 0 else "FAIL"), f"Ran {n} tests {tail}".strip()
    if code == 2 and "webcheck" in " ".join(cmd):
        return "NO-TESTS", (lines[-1] if lines else "webcheck: 체크 0개 또는 서버 응답 없음")
    return ("PASS" if code == 0 else "FAIL"), (lines[-1] if lines else "(출력 없음)")


def log(status, cmd, summary, secs, note):
    p = Path(WORK_DIR) / "VERIFY.md"
    p.parent.mkdir(exist_ok=True)
    new = not p.exists()
    with open(p, "a", encoding="utf-8") as f:
        if new:
            f.write("# VERIFY\n\n시각 | 결과 | 명령 | 요약 | 시간 | 메모\n\n")
        cmd_s = " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))
        f.write(f"- {datetime.now():%m-%d %H:%M} | {status} | `{cmd_s}` | {summary} | {secs:.1f}s | {note}\n")


def main():
    argv = sys.argv[1:]
    cmd = None
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="테스트 실행 후 요약 출력")
    ap.add_argument("--tail", type=int, default=40, help="실패 시 출력할 마지막 줄 수")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--note", default="", help="work/VERIFY.md에 남길 메모 (예: 완료 조건 번호)")
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--force", action="store_true", help="바뀐 파일이 없어도 다시 실행")
    a = ap.parse_args(argv)

    cmd = cmd or detect()
    if not cmd:
        print("[NO-TESTS] 테스트를 찾지 못함. test_*.py를 만들거나 `t.py -- <명령>`으로 지정하세요.")
        return 2

    st = load_state()
    fp = fingerprint()
    code_fp = fingerprint(code_only=True)
    key = " ".join(cmd)
    last = st.get("last", {})
    # webcheck는 서버 상태에 따라 결과가 바뀌므로(재시작 등) 파일이 같아도 다시 돌린다.
    live = "webcheck" in key
    if not a.force and not live and fp and last.get("fp") == fp and last.get("cmd") == key:
        print(f"[SAME] 직전 실행({last.get('at')}) 이후 바뀐 파일 없음. 다시 돌리지 않음 (--force로 강제).")
        print(f"  직전 결과: {last.get('status')}  {last.get('summary')}")
        return last.get("code", 1)

    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        code, out = -1, ((e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
        status, summary = "TIMEOUT", f"{a.timeout}s 초과"
    except FileNotFoundError:
        print(f"[FAIL] 명령을 찾을 수 없음: {cmd[0]}")
        return 1
    secs = time.time() - t0
    if code != -1:
        status, summary = summarize(cmd, code, out)

    shown = " ".join(cmd[2:] if cmd[0] == sys.executable else cmd)
    print(f"[{status}] exit={code} {secs:.1f}s  {shown}")
    print(f"  {summary}")
    if status != "PASS":
        lines = out.rstrip().splitlines()
        cut = lines[-a.tail:]
        if len(lines) > a.tail:
            print(f"  ... 앞 {len(lines) - a.tail}줄 생략 (--tail 로 조절)")
        print("\n".join(cut))
    if not a.no_log:
        log(status, cmd, summary, secs, a.note)

    rc = {"PASS": 0, "FAIL": 1}.get(status, 2)
    streak = 0
    if status == "FAIL":
        sig = fail_signature(summary, out)
        if st.get("fail_sig") == sig:
            # 파일이 바뀌었을 때만 "고쳤는데 또 실패"로 센다 (webcheck 재실행 등은 제외)
            streak = st.get("streak", 0) + (1 if code_fp != last.get("code_fp") else 0)
        else:
            streak = 1
        st["fail_sig"], st["streak"] = sig, streak
        if streak >= 2:
            print(f"[경고] 코드가 바뀌었는데 같은 실패가 {streak}회 연속. 같은 방식의 수정을 멈추고, "
                  "원인 가설 2개와 각각 확인할 방법을 사용자에게 보고할 것.")
    else:
        st.pop("fail_sig", None)
        st["streak"] = 0
    st["last"] = {"fp": fp, "code_fp": code_fp, "cmd": key, "status": status, "summary": summary,
                  "code": rc, "at": datetime.now().strftime("%H:%M:%S")}
    save_state(st)
    return rc


if __name__ == "__main__":
    sys.exit(main())
