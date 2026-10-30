#!/usr/bin/env bash
# 어떻게 clone했든 아래 중 아무거나 실행하면 된다.
#   bash .kit/install.sh          (git clone <주소> .kit 로 받은 경우)
#   bash probe-kit/install.sh     (그냥 git clone <주소> 로 받은 경우)
#   cd probe-kit && bash install.sh
# 하는 일: 작업 폴더 루트 찾기, .kit 경로 맞추기, 템플릿 복사(기존 파일은 안 덮어씀),
#          .kit를 git 추적에서 제외, 환경 점검.
set -u
KIT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(pwd)"
INSIDE=0

# 키트 폴더 안에서 실행했으면 그 바로 위를 작업 폴더로 본다.
if [ "$ROOT" = "$KIT" ]; then
  INSIDE=1
  ROOT="$(dirname "$KIT")"
  echo "키트 폴더 안에서 실행함. 작업 폴더를 $ROOT 로 잡음"
fi
cd "$ROOT" || exit 1

if [ ! -e "$ROOT/README.md" ]; then
  echo "주의: $ROOT 에 README.md가 없음. 과제 폴더가 맞는지 확인 (ls). 맞으면 그대로 진행해도 됨."
fi

# AGENTS.md와 프롬프트는 .kit/ 경로를 기준으로 쓰여 있다. 다른 이름으로 받았으면 .kit로 옮긴다.
if [ "$KIT" != "$ROOT/.kit" ]; then
  if [ -e "$ROOT/.kit" ]; then
    if [ "$(cd "$ROOT/.kit" && pwd -P)" = "$(cd "$KIT" && pwd -P)" ]; then
      :  # 이미 같은 폴더를 가리킴
    else
      echo "주의: $ROOT/.kit 가 이미 다른 것으로 있음. 옮기지 않고 $KIT 를 그대로 씀."
      echo "      이 경우 AGENTS.md의 .kit 경로가 안 맞으니 Codex에게 키트 위치를 알려줄 것."
    fi
  else
    mv "$KIT" "$ROOT/.kit" && KIT="$ROOT/.kit"
    echo "이동: 키트 폴더를 .kit 로 이름 변경 (숨김 폴더)"
  fi
fi

for f in TASK.md DECISIONS.md HANDOFF.md; do
  if [ -e "$ROOT/$f" ]; then echo "유지: $f (이미 있음)"; else cp "$KIT/templates/$f" "$ROOT/$f"; echo "복사: $f"; fi
done

if [ -e "$ROOT/AGENTS.md" ] && ! grep -q "반복과 토큰 줄이기" "$ROOT/AGENTS.md"; then
  cp "$KIT/templates/AGENTS.md" "$ROOT/AGENTS.kit.md"
  echo "주의: 과제에 AGENTS.md가 이미 있음. 건드리지 않고 AGENTS.kit.md로 복사함."
  echo "      Codex에게 'AGENTS.kit.md도 읽고 따라. 과제 AGENTS.md와 충돌하면 과제 쪽을 따라'라고 지시하세요."
elif [ ! -e "$ROOT/AGENTS.md" ]; then
  cp "$KIT/templates/AGENTS.md" "$ROOT/AGENTS.md"; echo "복사: AGENTS.md"
else
  echo "유지: AGENTS.md (이미 키트 버전)"
fi

if [ -d "$ROOT/.git" ]; then
  EXC="$ROOT/.git/info/exclude"
  for pat in ".kit" ".kit/"; do
    grep -qxF "$pat" "$EXC" 2>/dev/null || echo "$pat" >> "$EXC"
  done
  echo "git: 키트 폴더를 .git/info/exclude 에 추가 (과제 .gitignore는 그대로)"
else
  echo "git: 저장소 아님. 커밋 기록이 필요하면 운영 규정 확인 후 git init"
fi

echo; echo "== 환경 점검 =="
python3 "$KIT/tools/peek.py" --env || echo "python3 실행 실패: 도구 대신 rg, sed -n 으로 진행"
echo
echo "=================================================="
if [ "$INSIDE" = 1 ]; then
  echo " 설치 끝. 지금 터미널은 키트 폴더(.kit로 이름이 바뀜) 안이니 먼저:  cd .."
  echo " 그다음 codex 실행."
else
  echo " 설치 끝. 이제 이 폴더($ROOT)에서 codex 실행."
fi
echo " codex가 이미 켜져 있었다면 껐다가 다시 켜야 AGENTS.md를 읽음."
echo " 첫 질문: AGENTS.md 규칙 세 줄로 요약해봐"
echo "=================================================="
