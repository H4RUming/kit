# kit

Codex용 작업 하네스. 규칙(AGENTS.md), 작업 문서 템플릿, 단계별 지시 카드, 검증 도구로 구성된다. 도구는 Python 표준 라이브러리만 사용한다.

SK하이닉스 AI 해커톤 2026 2차 예선(Cofa-Probe) 대비용으로 만들었다. 실전 두 번 응시 후 무엇이 통했고 무엇을 바꿀지는 [회고](retro/2026-skhynix-hackathon.md)에 정리했다.

## Setup

과제 루트(README.md가 있는 폴더)에서:

```
git clone https://github.com/H4RUming/kit .kit && bash .kit/install.sh
```

`.kit` 없이 받았으면 `bash kit/install.sh`. install.sh가 작업 폴더를 찾아 키트를 `.kit`로 옮기고, 템플릿을 복사하고(기존 파일은 유지), `.kit`를 git 추적에서 제외하고, 환경을 점검한다.

이후 `head -3 AGENTS.md`로 `# Agent Rules`를 확인하고 `codex`를 실행한다. AGENTS.md는 세션 시작 때만 읽히므로, codex를 먼저 켰다면 재시작한다.

확인용 첫 메시지:
```
파일 만들지 말고 아무것도 실행하지 마. AGENTS.md의 Hard rules 번호랑 제목만 한국어로 나열해
```

## Layout

```
<task root>/
  AGENTS.md         Codex 규칙 (자동 로드)
  work/
    TASK.md         요구사항, 제약, 가정, 완료 조건, 변경 이력
    DECISIONS.md    결정과 근거 (직접 작성)
    HANDOFF.md      세션 인계
    VERIFY.md       검증 기록 (t.py가 생성)
    webchecks.json  웹 기능 체크
    server.log
  .kit/
    tools/          peek, t, q, webcheck, dbcheck
    prompts/        지시 카드
    docs/           web, db, auth, minimal 세부 규칙
```

AGENTS.md는 Hard rules, 작업 흐름, 토큰 규칙만 담는다. 세부 규칙은 `.kit/docs/`에 두고 해당 작업일 때만 읽게 한다.

## Workflow

| 시점 | 입력 | 동작 |
|---|---|---|
| 시작 | `킥오프` | README에서 요구사항(출처 줄 번호)과 제약 추출, TASK 초안, 빈틈 5개 |
| 인터뷰 후 | `TASK.md 확정. 담당자 답변 반영해` | 확정 |
| 조건마다 | `C1 진행` | 계획 3줄, 뼈대 확인, 구현, 해당 조건 테스트, 커밋, 3줄 설명 후 정지 |
| 설명 받은 뒤 | (직접) DECISIONS.md에 한 줄 | |
| 조건 2~3개마다 | `리뷰` | 수정 없이 검토 |
| 화면 확인 | `수동확인 C3` | Browser 체크리스트, 결과를 VERIFY에 MANUAL로 기록 |
| 컨텍스트 절반 | `핸드오프` | HANDOFF 전체 갱신, 새 세션 첫 문장 |
| 150분 | `제출점검` | 필수 파일, 한계 정리, 예상 질문 6개 |

조건마다 HANDOFF의 "현재 상태"는 자동 갱신된다. t.py가 `[경고]`를 내면 Codex가 멈추고 가설 2개를 보고한다.

## Tools

```
python3 .kit/tools/peek.py <path>            폴더 트리, CSV 컬럼 타입/결측/범위, JSON 구조, .py 심볼, SQLite 스키마
python3 .kit/tools/peek.py <file> --lines 40:80
python3 .kit/tools/peek.py --env             Python, Node, 패키지, 디스크, git

python3 .kit/tools/t.py                      테스트 자동 감지, 요약 출력, VERIFY 기록
python3 .kit/tools/t.py --note C3 -- python3 -m pytest -q -k C3_
python3 .kit/tools/q.py -- <cmd>             긴 출력 명령. 로그는 .kit/.state/logs/

python3 .kit/tools/webcheck.py smoke <base> / /path
python3 .kit/tools/webcheck.py links <base>
python3 .kit/tools/webcheck.py ui <base> / /path
python3 .kit/tools/webcheck.py run work/webchecks.json
python3 .kit/tools/webcheck.py init

python3 .kit/tools/dbcheck.py reconcile data.csv app.db <table> --key id
python3 .kit/tools/dbcheck.py query app.db "SELECT ..."
```

t.py 출력: `[PASS]`, `[FAIL]`, `[NO-TESTS]`(0개 또는 전부 skip), `[SAME]`(변경 없음, 재실행 안 함), `[경고]`(코드 변경 후 같은 실패 반복). webcheck는 서버 상태에 의존하므로 `[SAME]` 캐시를 쓰지 않는다.

webcheck는 HTTP 요청만 보내며 브라우저를 조작하지 않는다. 스펙에서 `{run}`은 실행마다 바뀌는 값, `{env:NAME}`은 환경변수(출력 시 마스킹)다. 쿠키는 체크 사이에 유지된다.

## Server

별도 터미널 탭에서:

```
python3 app.py 2>&1 | tee work/server.log
```

`0.0.0.0`에 바인딩해야 Browser 미리보기에서 열린다. 터미널에 찍힌 포트를 Browser의 PORT에 넣는다. 종료는 해당 탭에서 Ctrl+C.

환경변수 확인은 값을 출력하지 않는다: `test -n "$NAME" && echo set`

Browser 미리보기에서 로그인이 유지되지 않으면 미리보기가 다른 도메인으로 임베드되어 세션 쿠키가 제3자 쿠키로 처리되는 경우가 많다. 로그인 흐름은 webcheck로 검증하고, 쿠키 설정 변경은 담당자 확인 후에만 한다.

## Interview

README에 있는 내용은 묻지 않는다. 킥오프가 짚은 빈틈부터 시작해 아래 항목에서 빠진 것을 확인한다.

- 경계값: 같을 때, 이상/초과, 포함/제외
- 빈 값, 형식 오류, 음수, 과도한 길이
- 중복 데이터, 중복 요청
- 시간대, 날짜 형식, 마감 경계
- 권한: 역할별로 보고 바꿀 수 있는 것, 비로그인
- 실패 시 동작, 부분 실패
- 데이터 규모
- 요구사항 충돌 시 우선순위

마지막에 요약해서 확인받는다.

## Time

| 경과 | |
|---|---|
| 0~25분 | 설치, 킥오프, 인터뷰, TASK 확정 |
| 25~140분 | 조건 단위 구현과 검증. 100분에 범위 점검 |
| 140분 | 기능 동결 |
| 150분 | 제출점검, DECISIONS와 HANDOFF 직접 읽기 |
| 165분 | 제출 |

## Follow-up answers

결정과 근거, 구체적인 약점, 그 약점이 깨지는 조건, 다음 검증 계획 순서로 쓴다. 확실하지 않으면 검증하지 못한 부분과 확인 방법을 명시한다.

## Credits

`docs/minimal.md`와 AGENTS.md의 Minimal change는 [Ponytail](https://github.com/DietrichGebert/ponytail)(MIT, Copyright (c) 2026 DietrichGebert)의 AGENTS.md를 요약 번역했다. 라이선스 전문은 THIRD_PARTY_LICENSES.md.
