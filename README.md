# probe-kit

Cofa-Probe 2차 예선용 개인 준비물. 문제나 정답은 없음. Python 표준 라이브러리만 사용.

## 세팅 (이것만 기억)

과제 폴더(README.md 있는 곳)에서:

```
git clone https://github.com/<아이디>/probe-kit .kit && bash .kit/install.sh
```

그다음 `codex`. 끝.

까먹고 그냥 `git clone https://github.com/<아이디>/probe-kit` 했어도 괜찮음:
- 과제 폴더에서 `bash probe-kit/install.sh`
- 또는 `cd probe-kit && bash install.sh` 후 `cd ..`

어떻게 받았든 install.sh가 작업 폴더를 찾고, 키트 폴더 이름을 `.kit`(숨김 폴더)로 바꿔줌. 여러 번 실행해도 기존 파일은 안 덮어씀.
codex를 먼저 켜버렸으면 install 후 codex를 껐다 다시 켜기 (AGENTS.md는 시작할 때만 읽음).

설치 후 구조 (루트에는 AGENTS.md만 추가됨):

```
과제폴더/
  AGENTS.md          Codex가 자동으로 읽는 규칙
  README.md ...      과제 파일들 (그대로)
  work/
    TASK.md          과제 계약서
    DECISIONS.md     결정 기록
    HANDOFF.md       인계 문서
    VERIFY.md        테스트와 수동 확인 기록 (t.py가 자동 생성)
    webchecks.json   웹 기능 체크 (웹 과제일 때)
    server.log       서버 로그 (tee로 저장)
  .kit/              도구 (숨김)
```

## 구성

- templates/AGENTS.md: Codex 작업 규칙. 합의 전 구현 금지, 토큰 규칙, 검증, 기록, 최소 변경 원칙(Ponytail에서 발췌, MIT)
- templates/TASK.md, DECISIONS.md, HANDOFF.md: 과제 계약서, 결정 기록, 인계 문서. 설치하면 `work/`에 복사됨
- tools/peek.py: 폴더 트리, CSV 컬럼 타입/결측/범위, JSON 구조, .py 함수 목록, 줄 범위 출력, `--env` 환경 점검
- tools/t.py: 테스트 실행 후 요약만 출력. 실패 시 마지막 40줄. work/VERIFY.md에 자동 기록. 테스트 0개나 전부 skip이면 exit 2. 바뀐 파일이 없으면 다시 안 돌리고 `[SAME]`, 코드를 바꿨는데 같은 실패가 반복되면 `[경고]`
- tools/webcheck.py: 브라우저 없이 HTTP로 웹 기능 확인. `smoke`(페이지 요약), `links`(깨진 링크와 정적 파일), `run work/webchecks.json`(기능 체크, t.py로 돌리면 work/VERIFY.md 기록), `init`(스펙 예시). 화면 조작이 아니라서 Computer Use에 해당하지 않음
- tools/q.py: 출력이 긴 명령(설치, 빌드, 스크립트)을 돌리고 전체 로그는 `.kit/.state/logs/`에 저장. 화면에는 종료 코드, 에러로 보이는 줄, 마지막 몇 줄만
- install.sh: 템플릿 복사, `.kit/`를 git 추적에서 제외, 환경 점검
- prompts/: 단계별 지시 카드. 붙여넣지 말고 `.kit/prompts/3_review.md 읽고 그대로 해`처럼 파일을 가리키면 됨
  - 1_kickoff: README 읽고 work/TASK.md 초안, README와 데이터의 빈틈 최대 5개 (질문은 내가 직접, 코드 금지)
  - 2_build: 완료 조건 하나만 구현, 계획 3줄 먼저, t.py 통과하면 커밋하고 멈춤. `[C?]`를 조건 번호로 바꿔서 지시
  - 3_review: 수정 없이 diff 검토만. 누락, 경계값, 과설계, 문서와 코드 불일치. 새 세션에서 돌리면 편향이 덜함
  - 4_handoff: work/HANDOFF.md 갱신 후 새 세션으로 넘어갈 때
  - 5_presubmit: 필수 파일 확인, 한계 최신화, 예상 서술형 질문 6개 (답은 본인이 머릿속으로)
  - 6_manual: webcheck로 못 보는 화면/클릭 동작을 내가 Browser에서 확인할 체크리스트 (최대 5단계). 결과를 알려주면 work/VERIFY.md에 MANUAL로 기록

## 오늘 밤 (시험 전)

1. GitHub에 public 레포 `probe-kit` 생성 후 이 폴더 그대로 push. 키, 토큰, 개인정보 넣지 말 것
2. 아무 빈 폴더에서 `git clone <레포 주소> .kit && bash .kit/install.sh` 돌아가는지 확인
3. Codex 설치해서 작은 과제 하나로 리허설. AGENTS.md를 실제로 읽는지 `AGENTS.md 규칙 세 줄로 요약해봐`로 확인

## 사전 체험 15분 (링크 받은 뒤 과제 시작 전 1회, 연습 문제라 평가 미반영)

실제 응시 장소와 장비, 휴대폰까지 연결한 상태로 진행.
1. (2분) 터미널에서 `git clone <레포 주소> .kit && bash .kit/install.sh`. clone 되는지, Python 버전, pytest 유무 확인
2. (1분) `node --version`
3. (3분) `codex` 실행, `/status`, `/model`로 모델 목록과 응답 속도 확인. `AGENTS.md 규칙 세 줄로 요약해봐`로 실제로 읽는지 확인
4. (2분) `python3 -m http.server 8000 --bind 0.0.0.0` 띄우고 Browser 도구에서 PORT 8000으로 열리는지 확인
5. (2분) Cofa Helper에게 질문: 공개 Skill 적용 방법, 작업 폴더 밖에 clone해도 되는지
6. (남은 시간) Proctor 구도와 연결 유지 확인, 체험 종료 후 예시 서술형 풀어보기

## 시험 당일 순서

1. 과제 폴더 루트에서: `git clone <레포 주소> .kit && bash .kit/install.sh`
   (README에 clone 위치 제한이 있으면 그걸 따름)
2. 환경 점검 결과 확인: Python 버전, pytest/pandas 유무, Node 유무
3. `codex` 실행, `/status`로 모델과 권한 확인
4. `AGENTS.md 규칙 세 줄로 요약해봐`로 규칙을 읽었는지 확인
5. `.kit/prompts/1_kickoff.md 읽고 그대로 해`
6. 담당자 에이전트에게 직접 질문하고, 답을 work/TASK.md "확인된 사실"과 "담당자 확인"에 반영
7. 조건마다 `.kit/prompts/2_build.md 읽고 C1으로 해` 반복. 큰 조건이 끝나면 3_review
8. 대화가 길어지면 4_handoff 후 새 세션, 제출 전 5_presubmit

## 서버 띄우기 (내가 직접)

새 터미널 탭(+)을 열고 서버 전용으로 쓴다. 이 탭은 닫지 않는다.

```
python3 app.py 2>&1 | tee work/server.log
```

- `app.py` 자리에 실제 실행 파일이나 명령을 넣는다 (예: `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000`)
- 서버는 `0.0.0.0`에 바인딩해야 Browser 미리보기에서 열린다
- 터미널에 찍힌 실제 포트를 Browser 도구의 PORT 칸에 넣고 원형 화살표
- Codex에게는 `서버 로그는 work/server.log에 있어. tail -n 30으로 봐`라고 알려준다
- 끌 때는 그 탭에서 Ctrl+C (선택 영역이 없는 상태에서)

## 웹 과제 검증 흐름

1. 내가 서버 띄우기 (위 섹션)
2. `python3 .kit/tools/webcheck.py smoke http://127.0.0.1:<포트> /` 로 페이지가 뜨는지, 폼과 버튼이 있는지
3. Codex에게: `C2 완료 조건을 work/webchecks.json에 체크로 추가하고 t.py로 webcheck run 돌려`
4. JS 화면이나 클릭 흐름은: `.kit/prompts/6_manual.md 읽고 C2로 해` 후 Browser에서 직접 확인하고 결과를 알려주기
5. 서버 코드를 고쳤으면 서버 재시작 후 다시 run (webcheck는 [SAME] 캐시를 안 씀)

## 토큰 운영 규칙 (사람 쪽)

Codex는 매 턴 그 세션의 대화 전체를 다시 입력으로 보낸다. 세션이 길수록 한 턴이 비싸진다.

- 세션을 단계별로 끊기: 인터뷰와 합의, 조건 2~3개 구현, 리뷰를 각각 다른 세션으로. 넘어갈 때 4_handoff
- 지시를 구체적으로: 파일, 함수, 완료 조건 번호를 찍어주면 탐색이 줄어든다. "계속", "다시 해봐"만 반복하지 않기
- 실패하면 바로 재시도시키지 말고 원인부터 묻기: `왜 실패했는지 가설만 말해. 고치지 마`
- 내가 직접 할 수 있는 건 두 번째 터미널에서: `ls`, 작은 파일 확인, `python3 .kit/tools/t.py`, 서버 실행. Codex 대화에 안 들어가니 토큰이 안 들고, 터미널 기록은 평가에 남음
- reasoning effort: 단순 수정은 낮게, 설계와 디버깅은 높게. `/model`에서 바꾸는 방법은 사전 체험 때 확인
- 같은 행동을 반복하면 바로 중단시키고 방향을 다시 지시. 중단 키(Esc 또는 Ctrl+C)는 사전 체험 때 확인
- `/status`에 토큰 사용량이 보이면 단계가 끝날 때마다 확인

## 담당자에게 물을 것 (순서대로)

- 지금 이 일을 실제로 어떻게 하고 있는지, 최근에 문제가 됐던 구체적인 사례
- 지금은 어떻게 우회하고 있는지, 시간이나 비용이 얼마나 드는지
- 누가 쓰는지, 결과를 누가 받는지
- 성공 기준: 어떤 숫자가 얼마가 되면 성공인지, 그걸 어디서 확인하는지
- 입력 데이터의 진짜 출처, 형식, 빠지거나 틀린 값이 있는지
- 경계값과 예외: 같으면 통과인지, 시간대, 중복, 빈 값
- 하면 안 되는 것, 바꾸면 안 되는 것
- 우선순위: 시간이 모자라면 무엇부터 할지
- 막히면: "제가 뭘 더 물어봐야 하나요?" (답할 수 있는 범위를 알려준다고 함)

## 시간 배분 (180분)

| 경과 | 할 일 |
|---|---|
| 0~25분 | 설치, README, 담당자 인터뷰, work/TASK.md 확정 |
| 25~140분 | 조건 단위로 구현, t.py 검증, 커밋 반복. 100분에 범위 재점검 |
| 140분 | 기능 동결. 버그 수정과 검증만 |
| 150분 | work/HANDOFF.md, work/DECISIONS.md 정리. 직접 읽으면서 서술형 대비 |
| 165분 | 제출 시작 (공식 권고: 종료 약 10분 전) |

## 서술형 대비 (문항당 5분, 문항 수는 응시 화면 기준)

확정 후 질문 생성에 최대 10분 대기. 제출물과 작업 기록을 바탕으로 문항이 나옴. AI와 복붙 금지, 이전 문항으로 못 돌아감, 시간이 끝나면 입력한 내용으로 자동 확정. 답은 이 순서로:
1. 내가 내린 결정과 근거 (work/DECISIONS.md)
2. 내 코드의 구체적인 약점이나 한계
3. 그게 왜 위험한지, 어떤 입력에서 깨지는지
4. 다음에 무엇을 검증하고 고칠지

제출 전에 work/HANDOFF.md의 "알려진 한계와 위험"을 꼭 직접 읽어둘 것.

## 세션 관리

대화가 길어지면 compact를 반복하지 말고:
`work/HANDOFF.md 갱신해` 후 새 세션에서 `work/HANDOFF.md, work/TASK.md, work/DECISIONS.md만 읽고 이어가`.

## 출처

최소 변경 원칙은 Ponytail(https://github.com/DietrichGebert/ponytail, MIT License, Copyright (c) 2026 DietrichGebert)의 AGENTS.md를 요약 번역함.
