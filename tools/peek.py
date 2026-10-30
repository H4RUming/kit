#!/usr/bin/env python3
"""peek: 파일, 폴더, 데이터를 요약해서 보여준다. 표준 라이브러리만 사용.

사용:
  python3 peek.py <경로> [<경로> ...]     요약
  python3 peek.py <파일> --lines 40:80    줄 범위만 출력 (줄번호 포함)
  python3 peek.py <폴더> --depth 3        트리 깊이 지정 (기본 2)
  python3 peek.py --env                   실행 환경 점검
"""
import argparse
import ast
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".kit",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".next",
             Path(__file__).resolve().parent.parent.name}  # 키트 폴더 이름이 .kit가 아니어도 제외
DATA_SAMPLE_ROWS = 5000      # 타입 추정에 쓰는 최대 행 수
JSON_FULL_LIMIT = 30_000_000  # 이보다 큰 .json은 통째로 파싱하지 않음


def human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


def count_lines(p):
    n = 0
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            n += chunk.count(b"\n")
    return n


# ---------- 폴더 ----------
def peek_dir(root, depth, max_entries=60):
    files, total = 0, 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        files += len(fns)
        total += sum((Path(dp) / f).stat().st_size for f in fns if (Path(dp) / f).is_file())
    print(f"[dir] {root}  files={files} size={human(total)}  (제외: {', '.join(sorted(SKIP_DIRS))})")
    shown = 0

    def walk(d, level):
        nonlocal shown
        try:
            entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return
        for e in entries:
            if e.name in SKIP_DIRS:
                continue
            if shown >= max_entries:
                return
            pad = "  " * level
            if e.is_dir():
                n = sum(1 for _ in e.rglob("*") if not any(s in _.parts for s in SKIP_DIRS))
                print(f"{pad}{e.name}/  ({n} items)")
                shown += 1
                if level + 1 < depth:
                    walk(e, level + 1)
            else:
                print(f"{pad}{e.name}  {human(e.stat().st_size)}")
                shown += 1
    walk(Path(root), 0)
    if shown >= max_entries:
        print(f"... {max_entries}개에서 자름. 하위 폴더를 따로 peek 하세요.")


# ---------- CSV/TSV ----------
def infer(v):
    if v == "":
        return None
    try:
        int(v)
        return "int"
    except ValueError:
        pass
    try:
        float(v)
        return "float"
    except ValueError:
        pass
    s = v.strip()
    if len(s) >= 8 and s[:4].isdigit() and s[4] in "-/":
        try:
            datetime.fromisoformat(s.replace("/", "-").replace("Z", "+00:00"))
            return "datetime(tz)" if (s.endswith("Z") or "+" in s[10:]) else "datetime"
        except ValueError:
            pass
    if s.lower() in ("true", "false"):
        return "bool"
    return "str"


def peek_csv(p, n_samples):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
        head = f.read(65536)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel_tab if p.suffix.lower() == ".tsv" else csv.excel
        reader = csv.reader(f, dialect)
        header = next(reader, [])
        stats = {h: {"types": {}, "null": 0, "uniq": set(), "min": None, "max": None} for h in header}
        samples, rows, bad = [], 0, 0
        for row in reader:
            rows += 1
            if len(row) != len(header):
                bad += 1
            if len(samples) < n_samples:
                samples.append(row)
            if rows > DATA_SAMPLE_ROWS:
                continue
            for h, v in zip(header, row):
                st = stats[h]
                t = infer(v)
                if t is None:
                    st["null"] += 1
                    continue
                st["types"][t] = st["types"].get(t, 0) + 1
                if len(st["uniq"]) <= 50:
                    st["uniq"].add(v)
                if t in ("int", "float"):
                    x = float(v)
                    st["min"] = x if st["min"] is None else min(st["min"], x)
                    st["max"] = x if st["max"] is None else max(st["max"], x)
    sep = repr(dialect.delimiter)
    print(f"[csv] {p}  rows={rows} cols={len(header)} sep={sep}"
          + (f"  컬럼 수가 다른 행={bad}" if bad else ""))
    scanned = min(rows, DATA_SAMPLE_ROWS)
    if rows > DATA_SAMPLE_ROWS:
        print(f"  (타입, 결측, 고유값은 앞 {DATA_SAMPLE_ROWS}행 기준)")
    for h in header:
        st = stats[h]
        types = "/".join(f"{k}:{v}" for k, v in sorted(st["types"].items(), key=lambda kv: -kv[1])) or "-"
        uniq = ">50" if len(st["uniq"]) > 50 else str(len(st["uniq"]))
        rng = f" range=[{st['min']:g}, {st['max']:g}]" if st["min"] is not None else ""
        ex = ""
        if st["uniq"] and len(st["uniq"]) <= 8:
            ex = " values=" + ",".join(sorted(st["uniq"])[:8])
        print(f"  {h}: {types} null={st['null']}/{scanned} uniq={uniq}{rng}{ex}")
    for r in samples:
        print("  >", r)


# ---------- JSON / JSONL ----------
def shape(o, depth=0, max_depth=4):
    pad = "  " * depth
    if depth >= max_depth:
        return f"{type(o).__name__}"
    if isinstance(o, dict):
        if not o:
            return "{}"
        lines = [f"dict({len(o)} keys)"]
        for i, (k, v) in enumerate(o.items()):
            if i >= 25:
                lines.append(f"{pad}  ... +{len(o) - 25} keys")
                break
            lines.append(f"{pad}  {k!r}: {shape(v, depth + 1, max_depth)}")
        return "\n".join(lines)
    if isinstance(o, list):
        if not o:
            return "list(0)"
        kinds = {type(x).__name__ for x in o[:200]}
        if all(isinstance(x, dict) for x in o[:200]):
            keys = {}
            for x in o[:200]:
                for k in x:
                    keys[k] = keys.get(k, 0) + 1
            n = min(len(o), 200)
            opt = [k for k, c in keys.items() if c < n]
            first = shape(o[0], depth + 1, max_depth)
            tail = f"\n{pad}  (앞 {n}개 중 일부에만 있는 키: {opt[:15]})" if opt else ""
            return f"list({len(o)}) of {first}{tail}"
        return f"list({len(o)}) of {'/'.join(sorted(kinds))}, first={shape(o[0], depth + 1, max_depth)}"
    if isinstance(o, str):
        return f"str {o[:60]!r}" + ("..." if len(o) > 60 else "")
    return f"{type(o).__name__} {o!r}"


def peek_json(p, n_samples):
    size = p.stat().st_size
    if p.suffix.lower() in (".jsonl", ".ndjson"):
        rows, objs, bad = 0, [], 0
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                rows += 1
                if len(objs) < 200:
                    try:
                        objs.append(json.loads(line))
                    except json.JSONDecodeError:
                        bad += 1
        print(f"[jsonl] {p}  rows={rows} size={human(size)}" + (f"  파싱 실패(앞부분)={bad}" if bad else ""))
        print(f"  앞 {len(objs)}행 구조: " + shape(objs))
        for o in objs[:n_samples]:
            print("  >", json.dumps(o, ensure_ascii=False)[:300])
        return
    if size > JSON_FULL_LIMIT:
        print(f"[json] {p}  size={human(size)}  너무 커서 앞 1000자만 출력")
        with open(p, encoding="utf-8", errors="replace") as f:
            print(f.read(1000))
        return
    with open(p, encoding="utf-8", errors="replace") as f:
        o = json.load(f)
    print(f"[json] {p}  size={human(size)}")
    print("  " + shape(o))


# ---------- Python ----------
def peek_py(p):
    src = p.read_text(encoding="utf-8", errors="replace")
    n = src.count("\n") + 1
    print(f"[py] {p}  lines={n}")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"  SyntaxError: {e}")
        return
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(f"{node.module}")
    if imports:
        print("  imports:", ", ".join(dict.fromkeys(imports)))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = ", ".join(a.arg for a in node.args.args)
            print(f"  L{node.lineno}-{node.end_lineno} def {node.name}({args})")
        elif isinstance(node, ast.ClassDef):
            print(f"  L{node.lineno}-{node.end_lineno} class {node.name}")
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    print(f"    L{sub.lineno} .{sub.name}()")
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            names = [t.id for t in node.targets]
            if any(x.isupper() for x in names):
                print(f"  L{node.lineno} {', '.join(names)} = ...")
        elif isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            print(f"  L{node.lineno} if __name__ == '__main__'")


# ---------- 일반 텍스트 ----------
def peek_text(p, head=25):
    size = p.stat().st_size
    with open(p, "rb") as f:
        if b"\0" in f.read(4096):
            print(f"[binary] {p}  size={human(size)}")
            return
    n = count_lines(p)
    print(f"[text] {p}  lines={n} size={human(size)}  (앞 {min(head, n)}줄)")
    with open(p, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i > head:
                break
            print(f"{i:>5}  {line.rstrip()[:200]}")
    if n > head:
        print(f"  ... 나머지는 --lines A:B 로")


def print_lines(p, spec):
    a, _, b = spec.partition(":")
    a = int(a or 1)
    b = int(b) if b else a + 50
    with open(p, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i < a:
                continue
            if i > b:
                break
            print(f"{i:>5}  {line.rstrip()}")


# ---------- 환경 ----------
def env():
    print(f"python: {sys.version.split()[0]} ({sys.executable})")
    for cmd in ("python3", "pip", "pip3", "node", "npm", "git", "rg", "pytest", "uv"):
        path = shutil.which(cmd)
        ver = ""
        if path and cmd in ("node", "npm", "git", "rg", "pytest", "uv"):
            try:
                ver = subprocess.run([cmd, "--version"], capture_output=True, text=True,
                                     timeout=10).stdout.strip().splitlines()[0]
            except Exception:
                ver = "?"
        print(f"  {cmd:7} {'OK  ' + (ver or path) if path else '없음'}")
    import importlib.util
    mods = ("pytest", "numpy", "pandas", "requests", "flask", "fastapi", "sklearn", "pydantic", "sqlite3")
    have = [m for m in mods if importlib.util.find_spec(m)]
    miss = [m for m in mods if m not in have]
    print("  import 가능:", ", ".join(have) or "-")
    print("  import 불가:", ", ".join(miss) or "-")
    # 시간대 함정: 'Z' 접미사 파싱 (3.11 미만은 실패)
    try:
        datetime.fromisoformat("2026-10-31T10:00:00Z")
        print("  fromisoformat('...Z'): OK")
    except ValueError:
        print("  fromisoformat('...Z'): 실패 (Python<3.11). replace('Z', '+00:00') 필요")
    try:
        total, used, free = shutil.disk_usage(".")
        print(f"  disk free: {human(free)}  cwd writable: {os.access('.', os.W_OK)}")
    except OSError:
        pass
    if shutil.which("git"):
        r = subprocess.run(["git", "status", "--short", "--branch"], capture_output=True, text=True)
        out = (r.stdout or r.stderr).strip().splitlines()
        print("  git:", out[0] if out else "(clean)", f"(+{len(out) - 1} changes)" if len(out) > 1 else "")


def main():
    ap = argparse.ArgumentParser(description="파일, 폴더, 데이터 요약")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--lines", help="A:B 줄 범위 출력")
    ap.add_argument("--depth", type=int, default=2, help="폴더 트리 깊이")
    ap.add_argument("--n", type=int, default=3, help="샘플 행 수")
    ap.add_argument("--head", type=int, default=25, help="텍스트 앞부분 줄 수")
    ap.add_argument("--env", action="store_true", help="실행 환경 점검")
    a = ap.parse_args()
    if a.env:
        env()
    if not a.paths and not a.env:
        ap.print_help()
        return 2
    for raw in a.paths:
        p = Path(raw)
        if not p.exists():
            print(f"[없음] {p}")
            continue
        try:
            if p.is_dir():
                peek_dir(p, a.depth)
            elif a.lines:
                print_lines(p, a.lines)
            elif p.suffix.lower() in (".csv", ".tsv"):
                peek_csv(p, a.n)
            elif p.suffix.lower() in (".json", ".jsonl", ".ndjson"):
                peek_json(p, a.n)
            elif p.suffix.lower() == ".py":
                peek_py(p)
            else:
                peek_text(p, a.head)
        except Exception as e:  # 요약 실패해도 다음 경로는 계속
            print(f"[오류] {p}: {type(e).__name__}: {e}. --lines 로 직접 보세요.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
