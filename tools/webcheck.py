#!/usr/bin/env python3
"""webcheck: 브라우저 없이 HTTP 요청만으로 웹 서비스 기능을 확인한다. 표준 라이브러리만 사용.
화면 조작(Computer Use)이 아니라 서버에 요청을 보내고 응답을 검사한다.

사용:
  python3 webcheck.py smoke http://127.0.0.1:8000 / /about     페이지 요약(상태, 제목, 폼, 버튼, 링크)
  python3 webcheck.py links http://127.0.0.1:8000 --depth 1    같은 사이트 링크와 정적 파일 깨짐 확인
  python3 webcheck.py run webchecks.json                       스펙 파일의 체크 실행 (t.py로 돌리면 기록됨)
  python3 webcheck.py init                                     스펙 예시 출력

run 공통 옵션: --base URL (스펙의 base 대신), --wait 초 (서버가 뜰 때까지 기다림, 기본 5)
종료 코드: 0 전부 통과, 1 실패 있음, 2 체크 0개이거나 서버 응답 없음.
JavaScript 실행은 안 한다. JS로 그리는 화면과 클릭 동작은 Browser에서 사람이 확인한다.
"""
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

TIMEOUT = 15
SPEC_EXAMPLE = {
    "base": "http://127.0.0.1:8000",
    "checks": [
        {"name": "C1 메인 페이지", "path": "/", "expect": {"status": 200, "contains": ["할 일"]}},
        {"name": "C2 항목 생성", "method": "POST", "path": "/api/todos", "json": {"title": "우유"},
         "expect": {"status": [200, 201], "json_has": ["id"]}, "save": {"todo_id": "id"}},
        {"name": "C2 생성한 항목 조회", "path": "/api/todos/{todo_id}",
         "expect": {"status": 200, "json": {"title": "우유"}}},
        {"name": "C3 빈 제목은 거부", "method": "POST", "path": "/api/todos", "json": {"title": ""},
         "expect": {"status": [400, 422]}},
        {"name": "C4 로그인 폼", "method": "POST", "path": "/login", "form": {"user": "a", "pw": "b"},
         "expect": {"status": 200, "redirect_to": "/dashboard", "not_contains": ["Traceback"]}},
    ],
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self._in_title = "", False
        self.forms, self.buttons, self.links, self.assets = [], [], [], []
        self._form = None
        self._in_button = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": (a.get("method") or "get").upper(), "fields": []}
            self.forms.append(self._form)
        elif tag in ("input", "select", "textarea"):
            name = a.get("name") or a.get("id") or "?"
            typ = a.get("type", tag)
            req = "*" if "required" in a else ""
            if self._form is not None:
                self._form["fields"].append(f"{name}:{typ}{req}")
            if typ in ("submit", "button"):
                self.buttons.append(a.get("value") or name)
        elif tag == "button":
            self._in_button = True
            self.buttons.append(a.get("id") or a.get("name") or "")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag in ("script", "img") and a.get("src"):
            self.assets.append(a["src"])
        elif tag == "link" and a.get("href") and "stylesheet" in (a.get("rel") or ""):
            self.assets.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "form":
            self._form = None
        elif tag == "button":
            self._in_button = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif self._in_button and self.buttons and not self.buttons[-1]:
            self.buttons[-1] = data.strip()[:30]


def make_opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(opener, method, url, body=None, headers=None):
    """(status, final_url, headers, text, ms) 반환. 연결 실패면 status=None."""
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        kind, payload = body
        if kind == "json":
            data = json.dumps(payload).encode()
            hdrs.setdefault("Content-Type", "application/json")
        else:
            data = urllib.parse.urlencode(payload).encode()
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    t0 = time.time()
    try:
        r = opener.open(req, timeout=TIMEOUT)
        status, final, rh, raw = r.status, r.geturl(), r.headers, r.read()
    except urllib.error.HTTPError as e:
        status, final, rh, raw = e.code, e.geturl() or url, e.headers, e.read()
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        return None, url, {}, str(getattr(e, "reason", e)), (time.time() - t0) * 1000
    text = raw.decode((rh.get_content_charset() if rh else None) or "utf-8", errors="replace")
    return status, final, rh, text, (time.time() - t0) * 1000


def wait_for(base, secs):
    opener = make_opener()
    end = time.time() + secs
    while True:
        st, *_ = request(opener, "GET", base)
        if st is not None or time.time() >= end:
            return st is not None
        time.sleep(0.5)


def no_server(base):
    print(f"[NO-SERVER] {base} 응답 없음. 서버가 떠 있는지, 실제 포트, 0.0.0.0 바인딩을 확인.")
    return 2


def dig(obj, path):
    """'items.0.id' 같은 점 경로. 빈 문자열이면 루트."""
    if path in ("", "$"):
        return True, obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list) and part.lstrip("-").isdigit() and -len(cur) <= int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def subst(v, vars_):
    if isinstance(v, str):
        return re.sub(r"\{(\w+)\}", lambda m: str(vars_.get(m.group(1), m.group(0))), v)
    if isinstance(v, dict):
        return {k: subst(x, vars_) for k, x in v.items()}
    if isinstance(v, list):
        return [subst(x, vars_) for x in v]
    return v


def evaluate(exp, status, final, rh, text, ms):
    errs = []
    want = exp.get("status")
    if want is not None:
        ok = status in want if isinstance(want, list) else status == want
        if not ok:
            errs.append(f"status {status} != {want}")
    for s in exp.get("contains", []):
        if s not in text:
            errs.append(f"본문에 {s!r} 없음")
    for s in exp.get("not_contains", []):
        if s in text:
            errs.append(f"본문에 {s!r} 있음")
    if exp.get("regex") and not re.search(exp["regex"], text):
        errs.append(f"regex {exp['regex']!r} 불일치")
    for k, v in exp.get("header", {}).items():
        if v.lower() not in (rh.get(k, "") if rh else "").lower():
            errs.append(f"header {k}에 {v!r} 없음")
    if exp.get("redirect_to") and not urllib.parse.urlparse(final).path.endswith(exp["redirect_to"]):
        errs.append(f"최종 URL {urllib.parse.urlparse(final).path} != {exp['redirect_to']}")
    if exp.get("max_ms") and ms > exp["max_ms"]:
        errs.append(f"{ms:.0f}ms > {exp['max_ms']}ms")
    needs_json = any(k in exp for k in ("json", "json_has", "json_len"))
    data = None
    if needs_json:
        try:
            data = json.loads(text)
        except ValueError:
            errs.append("응답이 JSON이 아님")
            return errs, None
    for path, v in exp.get("json", {}).items():
        found, got = dig(data, path)
        if not found:
            errs.append(f"json {path} 없음")
        elif got != v:
            errs.append(f"json {path} = {got!r} != {v!r}")
    for path in exp.get("json_has", []):
        if not dig(data, path)[0]:
            errs.append(f"json {path} 없음")
    for path, n in exp.get("json_len", {}).items():
        found, got = dig(data, path)
        if not found or not hasattr(got, "__len__") or len(got) != n:
            errs.append(f"json {path or '루트'} 길이 {len(got) if found and hasattr(got, '__len__') else '?'} != {n}")
    return errs, data


def cmd_run(args):
    spec_path, base_override, wait = None, None, 5.0
    i = 0
    while i < len(args):
        if args[i] == "--base":
            base_override = args[i + 1]; i += 2
        elif args[i] == "--wait":
            wait = float(args[i + 1]); i += 2
        else:
            spec_path = args[i]; i += 1
    if not spec_path:
        print("스펙 파일이 필요함. 예시: python3 webcheck.py init > webchecks.json")
        return 2
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    base = (base_override or spec.get("base", "")).rstrip("/")
    checks = spec.get("checks", [])
    if not checks:
        print("[NO-TESTS] 체크가 0개")
        return 2
    if not wait_for(base, wait):
        return no_server(base)
    opener, vars_ = make_opener(), {}
    passed = failed = 0
    for c in checks:
        c = subst(c, vars_)
        name = c.get("name", c.get("path", "?"))
        method = c.get("method", "GET").upper()
        body = ("json", c["json"]) if "json" in c else (("form", c["form"]) if "form" in c else None)
        st, final, rh, text, ms = request(opener, method, base + c.get("path", "/"), body, c.get("headers"))
        if st is None:
            failed += 1
            print(f"FAIL {name}: 연결 실패 ({text})")
            continue
        errs, data = evaluate(c.get("expect", {}), st, final, rh, text, ms)
        for var, path in c.get("save", {}).items():
            if data is None:
                try:
                    data = json.loads(text)
                except ValueError:
                    data = None
            found, got = dig(data, path) if data is not None else (False, None)
            if found:
                vars_[var] = got
            else:
                errs.append(f"save {var}: json {path} 없음")
        if errs:
            failed += 1
            snippet = re.sub(r"\s+", " ", text)[:160]
            print(f"FAIL {name} [{method} {c.get('path')}] {st} {ms:.0f}ms: " + "; ".join(errs))
            print(f"     응답 앞부분: {snippet}")
        else:
            passed += 1
            print(f"PASS {name} ({st}, {ms:.0f}ms)")
    print(f"webcheck: {passed} passed, {failed} failed ({passed + failed} checks)")
    return 0 if failed == 0 else 1


def summarize_json(text):
    try:
        d = json.loads(text)
    except ValueError:
        return None
    if isinstance(d, dict):
        return f"JSON dict keys={list(d)[:12]}"
    if isinstance(d, list):
        first = list(d[0])[:8] if d and isinstance(d[0], dict) else type(d[0]).__name__ if d else "-"
        return f"JSON list len={len(d)} first={first}"
    return f"JSON {type(d).__name__}"


def cmd_smoke(args):
    if not args:
        print("사용: webcheck.py smoke URL [PATH ...]")
        return 2
    base, paths = args[0].rstrip("/"), args[1:] or ["/"]
    if not wait_for(base, 3):
        return no_server(base)
    opener, bad = make_opener(), 0
    for p in paths:
        st, final, rh, text, ms = request(opener, "GET", base + p)
        ctype = rh.get("Content-Type", "") if rh else ""
        print(f"[{st}] GET {p}  {ms:.0f}ms  {ctype}  {len(text)}B" + (f"  최종 URL {final}" if final != base + p else ""))
        if st is None or st >= 400:
            bad += 1
            print("  " + re.sub(r"\s+", " ", text)[:200])
            continue
        js = summarize_json(text) if "json" in ctype or text.lstrip()[:1] in "[{" else None
        if js:
            print("  " + js)
            continue
        pg = Page()
        pg.feed(text)
        print(f"  title={pg.title!r} links={len(pg.links)} assets={len(pg.assets)} buttons={[b for b in pg.buttons if b][:10]}")
        for f in pg.forms[:5]:
            print(f"  form {f['method']} {f['action'] or '(same)'} fields={f['fields'][:12]}")
        if len(text) < 2000 and "<script" in text and not pg.forms:
            print("  (본문이 짧고 script 위주: JS로 그리는 화면일 수 있음. 화면은 Browser에서 확인)")
    return 1 if bad else 0


def cmd_links(args):
    if not args:
        print("사용: webcheck.py links URL [--depth N] [--max N]")
        return 2
    base = args[0].rstrip("/")
    depth = int(args[args.index("--depth") + 1]) if "--depth" in args else 1
    limit = int(args[args.index("--max") + 1]) if "--max" in args else 60
    if not wait_for(base, 3):
        return no_server(base)
    host = urllib.parse.urlparse(base).netloc
    opener = make_opener()
    seen, queue, broken, checked = set(), [(base + "/", 0, "(start)")], [], 0
    while queue and checked < limit:
        url, d, src = queue.pop(0)
        url = url.split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        st, final, rh, text, _ = request(opener, "GET", url)
        checked += 1
        if st is None or st >= 400:
            broken.append((st, url, src))
            continue
        if "html" not in (rh.get("Content-Type", "") if rh else ""):
            continue
        pg = Page()
        pg.feed(text)
        for a in pg.assets:
            u = urllib.parse.urljoin(url, a)
            if urllib.parse.urlparse(u).netloc == host and u not in seen:
                queue.append((u, depth + 1, url))  # 정적 파일은 깊이 제한 없이 한 번 확인
        if d < depth:
            for h in pg.links:
                if h.startswith(("mailto:", "tel:", "javascript:")):
                    continue
                u = urllib.parse.urljoin(url, h)
                if urllib.parse.urlparse(u).netloc == host:
                    queue.append((u, d + 1, url))
    for st, url, src in broken:
        print(f"BROKEN [{st}] {urllib.parse.urlparse(url).path}  (from {urllib.parse.urlparse(src).path or src})")
    more = f", {len(queue)}개 남음(--max)" if queue else ""
    print(f"links: {checked} checked, {len(broken)} broken{more}")
    return 1 if broken else 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "init":
        print(json.dumps(SPEC_EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        return cmd_run(args)
    if cmd == "smoke":
        return cmd_smoke(args)
    if cmd == "links":
        return cmd_links(args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
