#!/usr/bin/env python3
"""dbcheck: CSV와 SQLite 테이블을 대조하고, DB를 읽기 전용으로 조회한다. 표준 라이브러리만 사용.

사용:
  python3 dbcheck.py reconcile data.csv app.db items --key id
      CSV와 테이블 대조: 행 수, 컬럼별 결측 수, 숫자 컬럼 합계/최소/최대, 고유값 수, 키 중복과 누락
  옵션:
      --key COL             기준 키 컬럼 (CSV와 DB 이름이 같을 때)
      --map csv_col=db_col  이름이 다른 컬럼 짝 (여러 번 가능)
      --expect-rows N       의도적으로 일부 행을 거르는 경우 DB에 있어야 할 행 수
      --only a,b,c          이 컬럼만 대조
      --tol 1e-6            숫자 합계 허용 오차 (상대)
  python3 dbcheck.py query app.db "SELECT status, COUNT(*) FROM items GROUP BY status" [--max 20]
      읽기 전용 조회 (쓰기 쿼리는 실패함). 결과는 최대 N행만 출력

t.py로 돌리면 work/VERIFY.md에 기록된다:
  python3 .kit/tools/t.py -- python3 .kit/tools/dbcheck.py reconcile data.csv app.db items --key id
종료 코드: 0 전부 일치, 1 불일치 있음, 2 파일/테이블 없음.
"""
import csv
import sqlite3
import sys
from pathlib import Path


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    for cand in (s, s.replace(",", "")):  # "1,234.5" 같은 천 단위 구분도 허용
        try:
            return float(cand)
        except ValueError:
            continue
    return None


def is_null(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def norm_key(v):
    if v is None:
        return None
    f = num(v)
    if f is not None and f == int(f):
        return str(int(f))
    return str(v).strip()


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        head = f.read(65536)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        r = csv.reader(f, dialect)
        header = next(r, [])
        rows = [row for row in r if any(c.strip() for c in row)]
    return header, rows


def ro_connect(db):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def parse_opts(args):
    opts = {"key": None, "map": {}, "expect_rows": None, "only": None, "tol": 1e-6, "max": 20}
    pos, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--key":
            opts["key"] = args[i + 1]; i += 2
        elif a == "--map":
            c, d = args[i + 1].split("=", 1); opts["map"][c] = d; i += 2
        elif a == "--expect-rows":
            opts["expect_rows"] = int(args[i + 1]); i += 2
        elif a == "--only":
            opts["only"] = [x.strip() for x in args[i + 1].split(",")]; i += 2
        elif a == "--tol":
            opts["tol"] = float(args[i + 1]); i += 2
        elif a == "--max":
            opts["max"] = int(args[i + 1]); i += 2
        else:
            pos.append(a); i += 1
    return pos, opts


def reconcile(args):
    pos, o = parse_opts(args)
    if len(pos) != 3:
        print("사용: dbcheck.py reconcile data.csv app.db table [--key id] [--map a=b] [--expect-rows N]")
        return 2
    csv_path, db, table = pos
    if not Path(csv_path).exists() or not Path(db).exists():
        print(f"[NO-FILE] {csv_path if not Path(csv_path).exists() else db} 없음")
        return 2
    header, rows = read_csv(csv_path)
    con = ro_connect(db)
    try:
        cur = con.execute(f'SELECT * FROM "{table}"')
    except sqlite3.Error as e:
        print(f"[NO-TABLE] {table}: {e}")
        return 2
    db_cols = [d[0] for d in cur.description]
    db_rows = cur.fetchall()
    con.close()

    lower_db = {c.lower(): c for c in db_cols}
    pairs = []
    for c in header:
        d = o["map"].get(c) or lower_db.get(c.lower())
        if d and (o["only"] is None or c in o["only"] or d in o["only"]):
            pairs.append((c, d))
    only_csv = [c for c in header if not (o["map"].get(c) or lower_db.get(c.lower()))]
    mapped = {d for _, d in pairs}
    only_db = [d for d in db_cols if d not in mapped and (o["only"] is None)]

    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))

    print(f"[info] CSV rows={len(rows)} cols={len(header)}  DB {table} rows={len(db_rows)} cols={len(db_cols)}  대조 컬럼={len(pairs)}")
    if only_csv:
        print(f"[info] CSV에만 있는 컬럼: {only_csv[:15]}")
    if only_db:
        print(f"[info] DB에만 있는 컬럼: {only_db[:15]}")

    want = o["expect_rows"] if o["expect_rows"] is not None else len(rows)
    check("행 수", len(db_rows) == want, f"DB {len(db_rows)} vs 기대 {want}" + ("" if o["expect_rows"] is None else " (--expect-rows)"))

    ci = {c: header.index(c) for c, _ in pairs}
    di = {d: db_cols.index(d) for _, d in pairs}
    for c, d in pairs:
        cv = [r[ci[c]] if ci[c] < len(r) else "" for r in rows]
        dv = [r[di[d]] for r in db_rows]
        label = c if c == d else f"{c}={d}"
        cn, dn = sum(map(is_null, cv)), sum(map(is_null, dv))
        if o["expect_rows"] is None:
            check(f"[{label}] 결측 수", cn == dn, f"CSV {cn} vs DB {dn}")
        cnum = [num(v) for v in cv if not is_null(v)]
        dnum = [num(v) for v in dv if not is_null(v)]
        numeric = cnum and dnum and all(x is not None for x in cnum) and all(x is not None for x in dnum)
        if numeric and o["expect_rows"] is None:
            cs, ds = sum(cnum), sum(dnum)
            ok = abs(cs - ds) <= o["tol"] * max(1.0, abs(cs))
            check(f"[{label}] 합계", ok, f"CSV {cs:g} vs DB {ds:g}")
            check(f"[{label}] 최소/최대", (min(cnum), max(cnum)) == (min(dnum), max(dnum)),
                  f"CSV [{min(cnum):g}, {max(cnum):g}] vs DB [{min(dnum):g}, {max(dnum):g}]")
        elif o["expect_rows"] is None:
            cu = len({str(v).strip() for v in cv if not is_null(v)})
            du = len({str(v).strip() for v in dv if not is_null(v)})
            check(f"[{label}] 고유값 수", cu == du, f"CSV {cu} vs DB {du}")

    if o["key"]:
        kc = o["key"]
        kd = o["map"].get(kc) or lower_db.get(kc.lower())
        if kc not in header or not kd:
            check(f"키 {kc}", False, "CSV나 DB에 키 컬럼이 없음")
        else:
            ck = [norm_key(r[header.index(kc)]) for r in rows]
            dk = [norm_key(r[db_cols.index(kd)]) for r in db_rows]
            dup_db = len(dk) - len(set(dk))
            dup_csv = len(ck) - len(set(ck))
            check(f"키 {kc} DB 중복", dup_db == 0, f"{dup_db}개" + (f" (CSV에도 중복 {dup_csv}개)" if dup_csv else ""))
            miss = sorted(set(ck) - set(dk), key=str)
            extra = sorted(set(dk) - set(ck), key=str)
            if o["expect_rows"] is None:
                check(f"키 {kc} CSV에 있는데 DB에 없음", not miss, f"{len(miss)}개 예: {miss[:5]}" if miss else "")
            else:
                print(f"[info] CSV에만 있는 키 {len(miss)}개 (의도적으로 거른 행인지 확인) 예: {miss[:5]}")
            check(f"키 {kc} DB에만 있음", not extra, f"{len(extra)}개 예: {extra[:5]}" if extra else "")

    passed, failed = sum(results), len(results) - sum(results)
    print(f"dbcheck: {passed} passed, {failed} failed ({len(results)} checks)")
    return 0 if failed == 0 else 1


def query(args):
    pos, o = parse_opts(args)
    if len(pos) != 2:
        print('사용: dbcheck.py query app.db "SELECT ..." [--max 20]')
        return 2
    db, sql = pos
    if not Path(db).exists():
        print(f"[NO-FILE] {db} 없음")
        return 2
    con = ro_connect(db)
    try:
        cur = con.execute(sql)
    except sqlite3.Error as e:
        print(f"[ERROR] {e}")
        return 1
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchmany(o["max"] + 1)
    con.close()
    print(" | ".join(cols))
    for r in rows[:o["max"]]:
        print(" | ".join("NULL" if v is None else str(v)[:40] for v in r))
    if len(rows) > o["max"]:
        print(f"... {o['max']}행에서 자름 (--max)")
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "reconcile":
        return reconcile(args)
    if cmd == "query":
        return query(args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
