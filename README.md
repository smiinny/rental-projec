# 공유 물품 대여 프로그램 (과제 2: 디자인 패턴 리팩터링)

학생회실 공유 물품(우산, 보조배터리 등)의 물품 등록·대여·반납·연체료를 처리하는 작은 파이썬 프로그램입니다.
대여할 때와 목록을 볼 때 품목 분류에 맞는 반납 기한·연체료 안내 문구를 함께 보여 줍니다.
같은 기능을 세 단계로 나누어 담았습니다.

| 폴더 | 단계 | 내용 |
|---|---|---|
| `v1_before/` | 구조 개선 전 | 입력 검사·대여 규칙·저장이 함수 하나(`handle_command`)에 들어 있는 기본 프로그램 |
| `v2_refactored/` | 구조 개선 후 | 입력·처리·저장을 파일별로 나누고, 대여 규칙에 Strategy 패턴 적용 (동작은 v1과 같음) |
| `v3_changed/` | 기능 변경 후 | v2에 "장기 대여" 규칙 하나 추가 + 웹 화면(선택 확장) |

GitHub 저장소: https://github.com/smiinny/rental-projec

## 1. 필요한 것

- Python 3.10 이상 (3.13.18에서 실행·검사함)
- 외부 패키지 없음: 표준 라이브러리만 사용하므로 `pip install`이 필요 없습니다.

## 2. 실행 방법

모든 명령은 이 README가 있는 최상위 폴더에서 실행합니다.

```
python v1_before/rental.py data/items.json          # 개선 전
python v2_refactored/main.py data/items.json        # 개선 후
python v3_changed/main.py data/items_v3.json        # 기능 변경 후
```

실행 후 아래 명령을 한 줄씩 입력합니다.

| 명령 | 뜻 | 예시 |
|---|---|---|
| `rent <품목> <이름> <날짜>` | 대여 | `rent 우산 김민수 2026-11-02` |
| `return <대여번호> <날짜>` | 반납 | `return 1 2026-11-05` |
| `add <품목> <분류> <수량>` | 물품 추가 (이미 있으면 재고 추가) | `add 삼각대 전자기기 2` |
| `list` | 재고·안내 문구와 대여 중 목록 | `list` |
| `quit` | 종료 | `quit` |

물품 추가·대여·반납이 성공하면 자료 파일(JSON)에 바로 저장됩니다. 분류는 4번 표에 있는 이름만 쓸 수 있습니다. 예시 자료를 처음 상태로 되돌리려면
ZIP에 들어 있던 `data/items.json`, `data/items_v3.json`을 다시 덮어쓰면 됩니다.

### 웹 화면 (선택 확장)

```
python v3_changed/web_app.py data/items_v3.json
```

브라우저에서 http://localhost:8000 을 엽니다. 품목을 고르고 이름·대여일을 넣어 [대여],
"대여 중" 표에서 날짜를 고르고 [반납], 맨 아래에서 품목·분류·수량을 넣어 [추가]를 누릅니다.
결과 문장은 화면 위쪽에 나타나고, 재고 표에는 품목별 반납 기한·연체료 안내가 함께 보입니다.
끝낼 때는 터미널에서 Ctrl+C를 누릅니다. 웹 화면은 터미널 프로그램과 같은
`main.handle_command()`를 부르므로 검사·규칙·저장이 완전히 같습니다.

## 3. 검사 방법

```
python tests/run_checks.py
```

- 기존 검사 14개(정상 4, 경계 4, 잘못된 입력 6): 같은 입력을 v1·v2·v3에 넣고, 예상 결과와 실제 출력,
  저장된 JSON이 모두 같은지 확인합니다.
- 새 기능 검사 4개: 장기 대여 규칙이 v3에서 동작하고 저장된 JSON 값(재고, 기한, 연체료)이 예상과 같은지,
  v1·v2에서는 오류가 나고 자료 파일이 바뀌지 않는지 확인합니다.
- 결과는 화면에 나오고 `results/check_log.txt`에 저장됩니다. 검사는 자료 파일의 복사본으로
  실행하므로 `data/` 안의 예시 자료는 바뀌지 않습니다.

## 4. 대여 규칙

| 분류 | 대여 기간 | 연체료 | 규칙 클래스 (`rules.py`) |
|---|---|---|---|
| 일반 | 3일 | 하루 500원, 최대 3000원 | `StandardRule` |
| 전자기기 | 1일 | 하루 1000원, 상한 없음 | `ElectronicsRule` |
| 장기 (v3에서 추가) | 14일 | 연체 2일까지 면제, 이후 하루 200원 | `LongTermRule` |

## 5. 파일 구성

```
README.md
data/
  items.json            기존 검사용 예시 자료 (우산, 보조배터리, 돗자리)
  items_v3.json         v3용 예시 자료 (공학용계산기 = 장기 분류 추가)
  items_broken.json     검사용 손상된 자료 (JSON 형식 오류)
v1_before/
  rental.py             구조 개선 전 기본 프로그램
v2_refactored/
  main.py               연결: 입력 -> 처리 -> 저장 순서로 호출
  inputs.py             입력: 명령·날짜 검사
  service.py            처리: 물품 추가, 대여, 반납, 목록
  rules.py              처리: 분류별 대여 규칙과 안내 문구 (Strategy 패턴)
  storage.py            저장: JSON 읽기/쓰기
v3_changed/
  (v2와 같은 파일)       rules.py에 LongTermRule 추가, main.py는 설명 주석만 다름
  web_app.py            웹 화면 (선택 확장)
tests/
  run_checks.py         검사 코드 (예상·실제 결과 비교)
results/
  check_log.txt         검사 실행 결과 기록
  web_check.txt         웹 화면 동작 기록
  web_screen.png        웹 화면 캡처
```

v2와 v3의 차이는 macOS·Linux에서 `diff -r v2_refactored v3_changed`로, Windows에서는 git이 설치되어 있다면
`git diff --no-index v2_refactored v3_changed`로 폴더 전체를 비교해 확인할 수 있습니다.
(Windows의 `fc`는 폴더가 아니라 파일 두 개만 비교하므로 `fc v2_refactored\rules.py v3_changed\rules.py`처럼 파일별로 써야 합니다.)

## 6. AI 사용

이 프로젝트는 AI 도구(Claude)를 사용해 작성했습니다. 자세한 사용 기록과 본인이 검토·수정한 내용은 레포트 5번 항목에 적었습니다.
