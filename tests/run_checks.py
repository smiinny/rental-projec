"""검사 코드: 같은 입력을 v1(개선 전), v2(개선 후), v3(기능 변경 후)에 넣고 결과를 비교한다.

실행(프로젝트 최상위 폴더에서):  python tests/run_checks.py
결과는 화면에 출력되고 results/check_log.txt 에도 저장된다.

검사 내용
 1) 기존 검사 18개: 예상 결과와 세 버전의 실제 출력이 같은지, 저장된 JSON이 서로 같은지,
    그리고 오류가 난 명령마다 그 명령 직전과 직후의 자료 파일이 같은지(오류 때 저장하지 않는지),
    자료 파일이 없을 때 실행 후에도 파일이 새로 생기지 않는지
 2) 새 기능 검사 4개: v3에서 장기 대여 규칙이 동작하고 저장값이 예상과 같은지,
    v1·v2에서는 오류가 나고 자료 파일이 바뀌지 않는지
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS = {
    "v1": os.path.join(ROOT, "v1_before", "rental.py"),
    "v2": os.path.join(ROOT, "v2_refactored", "main.py"),
    "v3": os.path.join(ROOT, "v3_changed", "main.py"),
}
MISSING = "no_such_file.json"

GUIDE_STANDARD = "안내: 3일 대여, 연체료 하루 500원(최대 3000원)"
GUIDE_ELECTRONICS = "안내: 1일 대여, 연체료 하루 1000원"
GUIDE_LONG = "안내: 14일 대여, 연체 2일까지 면제 후 하루 200원"

# (종류, 상황, 명령 목록, 예상 출력 줄 목록)
OLD_CASES = [
    ("정상", "대여 후 기한 내 반납 (안내 문구 포함)",
     ["rent 우산 김민수 2026-11-02", "return 1 2026-11-05"],
     ["대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "반납 완료: 1번 우산 연체 0일 연체료 0원"]),
    ("정상", "전자기기 2일 연체",
     ["rent 보조배터리 이서연 2026-11-02", "return 1 2026-11-05"],
     ["대여 완료: 1번 보조배터리 (이서연) 반납 기한 2026-11-03", GUIDE_ELECTRONICS,
      "반납 완료: 1번 보조배터리 연체 2일 연체료 2000원"]),
    ("정상", "대여 후 목록 보기 (품목별 안내 문구)",
     ["rent 우산 김민수 2026-11-02", "list"],
     ["대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "[물품]",
      "우산 (일반) 재고 1 | 3일 대여, 연체료 하루 500원(최대 3000원)",
      "보조배터리 (전자기기) 재고 1 | 1일 대여, 연체료 하루 1000원",
      "돗자리 (일반) 재고 0 | 3일 대여, 연체료 하루 500원(최대 3000원)",
      "[대여 중]", "1번 우산 김민수 기한 2026-11-05"]),
    ("정상", "새 물품 추가 후 대여",
     ["add 삼각대 전자기기 2", "rent 삼각대 박지훈 2026-11-02"],
     ["물품 추가: 삼각대 (전자기기) 재고 2",
      "대여 완료: 1번 삼각대 (박지훈) 반납 기한 2026-11-03", GUIDE_ELECTRONICS]),
    ("경계", "재고 0인 품목 대여",
     ["rent 돗자리 박지훈 2026-11-02"],
     ["오류: 재고가 없습니다: 돗자리"]),
    ("경계", "마지막 1개를 빌린 뒤 다시 대여",
     ["rent 보조배터리 이서연 2026-11-02", "rent 보조배터리 박지훈 2026-11-02"],
     ["대여 완료: 1번 보조배터리 (이서연) 반납 기한 2026-11-03", GUIDE_ELECTRONICS,
      "오류: 재고가 없습니다: 보조배터리"]),
    ("경계", "일반 물품 15일 연체(상한 3000원)",
     ["rent 우산 김민수 2026-11-02", "return 1 2026-11-20"],
     ["대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "반납 완료: 1번 우산 연체 15일 연체료 3000원"]),
    ("경계", "재고 0인 품목에 재고 추가 후 대여",
     ["add 돗자리 일반 1", "rent 돗자리 박지훈 2026-11-02"],
     ["재고 추가: 돗자리 재고 1",
      "대여 완료: 1번 돗자리 (박지훈) 반납 기한 2026-11-05", GUIDE_STANDARD]),
    ("잘못된 입력", "없는 품목·틀린 날짜·값 부족·모르는 명령",
     ["rent 노트북 김민수 2026-11-02", "rent 우산 김민수 2026-13-40", "rent 우산", "hello"],
     ["오류: 없는 품목입니다: 노트북",
      "오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): 2026-13-40",
      "오류: 입력 형식이 잘못되었습니다",
      "오류: 알 수 없는 명령입니다: hello"]),
    ("잘못된 입력", "반납 오류(숫자 아님·없는 번호·대여일 이전·중복 반납)",
     ["rent 우산 김민수 2026-11-02", "return abc 2026-11-03", "return 9 2026-11-03",
      "return 1 2026-11-01", "return 1 2026-11-03", "return 1 2026-11-03"],
     ["대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "오류: 대여 번호는 숫자여야 합니다: abc",
      "오류: 없는 대여 번호입니다: 9",
      "오류: 반납일이 대여일보다 빠릅니다",
      "반납 완료: 1번 우산 연체 0일 연체료 0원",
      "오류: 이미 반납한 대여입니다: 1"]),
    ("잘못된 입력", "물품 추가 오류(수량 0·없는 분류·다른 분류로 중복·값 부족)",
     ["add 삼각대 전자기기 0", "add 삼각대 가구 1", "add 우산 전자기기 1", "add 삼각대"],
     ["오류: 수량은 1 이상의 숫자여야 합니다: 0",
      "오류: 알 수 없는 분류입니다: 가구",
      "오류: 이미 다른 분류로 등록된 품목입니다: 우산 (일반)",
      "오류: 입력 형식이 잘못되었습니다"]),
    ("잘못된 입력", "자료 파일 누락",
     ["list"],
     ["오류: 자료 파일을 찾을 수 없습니다: " + MISSING]),
    # [피드백 반영] isdigit()은 통과하지만 int()로 바꿀 수 없는 숫자 문자
    ("잘못된 입력", "0~9가 아닌 숫자 문자(²)를 수량·대여 번호에 입력",
     ["add 삼각대 전자기기 ²", "rent 우산 김민수 2026-11-02", "return ² 2026-11-03"],
     ["오류: 수량은 1 이상의 숫자여야 합니다: ²",
      "대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "오류: 대여 번호는 숫자여야 합니다: ²"]),
    # [피드백 반영] 내용이 깨진 자료 파일 (data/items_broken.json)
    ("잘못된 입력", "손상된 자료 파일(JSON 형식 오류)",
     ["list", "rent 우산 김민수 2026-11-02"],
     ["오류: 자료 파일 형식이 잘못되었습니다: data.json",
      "오류: 자료 파일 형식이 잘못되었습니다: data.json"]),
]

# [2차 피드백 반영] strptime이 받아 주던 한 자리 월·일 날짜
OLD_CASES.append(
    ("잘못된 입력", "한 자리 월·일 날짜(2026-1-5, 2026-11-5)",
     ["rent 우산 김민수 2026-1-5", "rent 우산 김민수 2026-11-02", "return 1 2026-11-5"],
     ["오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): 2026-1-5",
      "대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): 2026-11-5"]))

# [3차 피드백 반영] 형식은 맞지만 반납 기한이 날짜 범위(9999-12-31)를 넘는 대여
OLD_CASES.append(
    ("경계", "날짜 범위 끝(9999-12-28은 기한 9999-12-31, 9999-12-31은 범위 초과)",
     ["rent 우산 김민수 9999-12-31", "rent 우산 김민수 9999-12-28"],
     ["오류: 반납 기한이 날짜 범위를 넘습니다: 9999-12-31",
      "대여 완료: 1번 우산 (김민수) 반납 기한 9999-12-31", GUIDE_STANDARD]))

# [4·6차 피드백 반영] 수량·대여 번호는 최대 9자리(MAX_DIGITS). Python의 int() 변환 한도와 관계없이
# 프로그램이 직접 자릿수를 검사하므로, 9자리는 받고 10자리·5000자리는 어느 Python 버전에서나 거부해야 한다.
LONG_NUMBER = "1" * 5000
OLD_CASES.append(
    ("경계", "수량·대여 번호 자릿수 제한(9자리 허용, 10자리·5000자리 거부)",
     ["add 삼각대 전자기기 999999999", "add 삼각대 전자기기 1000000000",
      "add 삼각대 전자기기 " + LONG_NUMBER, "rent 우산 김민수 2026-11-02",
      "return 1000000000 2026-11-03", "return " + LONG_NUMBER + " 2026-11-03",
      "return 000000001 2026-11-03"],
     ["물품 추가: 삼각대 (전자기기) 재고 999999999",
      "오류: 수량은 1 이상의 숫자여야 합니다: 1000000000",
      "오류: 수량은 1 이상의 숫자여야 합니다: " + LONG_NUMBER,
      "대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD,
      "오류: 대여 번호는 숫자여야 합니다: 1000000000",
      "오류: 대여 번호는 숫자여야 합니다: " + LONG_NUMBER,
      "반납 완료: 1번 우산 연체 0일 연체료 0원"]))

# [5차 피드백 반영] 인수가 없어야 하는 list에 불필요한 인수가 붙은 경우
OLD_CASES.append(
    ("잘못된 입력", "list에 불필요한 인수(list 우산, list 1 2)",
     ["list 우산", "list 1 2", "rent 우산 김민수 2026-11-02"],
     ["오류: 입력 형식이 잘못되었습니다",
      "오류: 입력 형식이 잘못되었습니다",
      "대여 완료: 1번 우산 (김민수) 반납 기한 2026-11-05", GUIDE_STANDARD]))

# 기본 자료가 아닌 파일로 실행하는 검사
DATA_FOR = {"손상된 자료 파일(JSON 형식 오류)": "items_broken.json"}

NEW_CASES = [
    ("새 기능", "장기 품목 대여(14일)와 안내 문구",
     ["rent 공학용계산기 최유진 2026-11-02"],
     ["대여 완료: 1번 공학용계산기 (최유진) 반납 기한 2026-11-16", GUIDE_LONG]),
    ("새 기능", "장기 품목 2일 연체(면제 구간)",
     ["rent 공학용계산기 최유진 2026-11-02", "return 1 2026-11-18"],
     ["대여 완료: 1번 공학용계산기 (최유진) 반납 기한 2026-11-16", GUIDE_LONG,
      "반납 완료: 1번 공학용계산기 연체 2일 연체료 0원"]),
    ("새 기능", "장기 품목 5일 연체",
     ["rent 공학용계산기 최유진 2026-11-02", "return 1 2026-11-21"],
     ["대여 완료: 1번 공학용계산기 (최유진) 반납 기한 2026-11-16", GUIDE_LONG,
      "반납 완료: 1번 공학용계산기 연체 5일 연체료 600원"]),
    ("새 기능", "장기 분류로 새 물품 추가",
     ["add 제도기 장기 2"],
     ["물품 추가: 제도기 (장기) 재고 2"]),
]

# [피드백 반영] 새 기능 검사에서 v3가 저장한 JSON의 값도 확인한다: (설명, 꺼내는 함수, 예상값)
NEW_SAVED = [
    [("공학용계산기 재고", lambda d: d["items"]["공학용계산기"]["stock"], 0),
     ("대여 기록 반납 기한", lambda d: d["loans"][0]["due_date"], "2026-11-16"),
     ("대여 기록 반납 여부", lambda d: d["loans"][0]["returned"], False)],
    [("공학용계산기 재고", lambda d: d["items"]["공학용계산기"]["stock"], 1),
     ("반납일", lambda d: d["loans"][0]["return_date"], "2026-11-18"),
     ("저장된 연체료", lambda d: d["loans"][0]["fee"], 0)],
    [("공학용계산기 재고", lambda d: d["items"]["공학용계산기"]["stock"], 1),
     ("반납일", lambda d: d["loans"][0]["return_date"], "2026-11-21"),
     ("저장된 연체료", lambda d: d["loans"][0]["fee"], 600)],
    [("제도기 품목", lambda d: d["items"]["제도기"], {"category": "장기", "stock": 2}),
     ("대여 기록 수", lambda d: len(d["loans"]), 0)],
]


def run(version, data_name, commands, missing_file=False):
    """자료 파일의 복사본으로 프로그램을 실행하고 (출력 줄 목록, 저장된 JSON 글자)를 돌려준다."""
    with tempfile.TemporaryDirectory() as folder:
        data_path = os.path.join(folder, "data.json")
        if missing_file:
            data_path = MISSING
        else:
            shutil.copy(os.path.join(ROOT, "data", data_name), data_path)
        # 프로그램은 복사본이 있는 폴더에서 실행하고, 오류 문장이 같도록 파일 이름만 넘긴다
        result = subprocess.run(
            [sys.executable, "-X", "utf8", VERSIONS[version], os.path.basename(data_path)],
            input="\n".join(commands + ["quit"]) + "\n",
            capture_output=True, encoding="utf-8", cwd=folder)
        lines = result.stdout.splitlines()[1:]      # 첫 줄(명령 안내)은 뺀다
        # 실행이 끝난 뒤의 자료 파일 내용. 파일이 없으면 None (누락 파일 검사에서 쓰임)
        saved_path = os.path.join(folder, os.path.basename(data_path))
        saved = None
        if os.path.exists(saved_path):
            with open(saved_path, encoding="utf-8") as f:
                saved = f.read()
        return lines, saved


def check_error_keeps_file(version, data_name, commands, missing_file=False):
    """오류가 난 명령마다 그 명령 직전과 직후의 자료 파일 내용이 같은지 확인한다.

    명령을 앞에서부터 1개, 2개, ... 넣어 실행하고, 새로 나온 첫 출력이 "오류:"이면
    바로 앞 단계의 파일과 비교한다. 돌려주는 값: (확인한 오류 명령 수, 파일이 바뀐 명령 목록)
    """
    if missing_file:
        before_out, before_saved = [], None
    else:
        with open(os.path.join(ROOT, "data", data_name), encoding="utf-8") as f:
            before_out, before_saved = [], f.read()
    checked = 0
    changed = []
    for k in range(1, len(commands) + 1):
        out, saved = run(version, data_name, commands[:k], missing_file)
        new_lines = out[len(before_out):]
        if new_lines and new_lines[0].startswith("오류:"):
            checked += 1
            if saved != before_saved:
                changed.append(commands[k - 1])
        before_out, before_saved = out, saved
    return checked, changed


def main():
    log = []
    fail = 0

    def write(text=""):
        print(text)
        log.append(text)

    def write_lines(label, lines):
        for index, text in enumerate(lines):
            if len(text) > 120:     # 5000자리 숫자 같은 긴 줄은 기록에서 줄여 보여 준다
                text = text[:60] + "...(총 %d자)" % len(text)
            write("    " + (label if index == 0 else " " * len(label)) + text)

    write("=== 1) 기존 검사: 같은 입력을 v1 / v2 / v3 에 넣기 (자료: data/items.json) ===")
    for number, (kind, title, commands, expected) in enumerate(OLD_CASES, start=1):
        missing = title == "자료 파일 누락"
        data_name = DATA_FOR.get(title, "items.json")
        outputs = {}
        saves = {}
        for version in VERSIONS:
            outputs[version], saves[version] = run(version, data_name, commands, missing)
        same_saved = saves["v1"] == saves["v2"] == saves["v3"]
        keep = {v: check_error_keeps_file(v, data_name, commands, missing) for v in VERSIONS}
        keep_ok = all(not changed for _, changed in keep.values())
        ok = all(outputs[v] == expected for v in VERSIONS) and same_saved and keep_ok
        if missing:
            ok = ok and all(saves[v] is None for v in VERSIONS)
        if not ok:
            fail += 1
        write("")
        write("[검사 %d] (%s) %s -> %s" % (number, kind, title, "통과" if ok else "실패"))
        write_lines("입력: ", commands)
        write_lines("예상: ", expected)
        for version in VERSIONS:
            if outputs[version] == expected:
                write("    %s  : 예상과 같은 %d줄 출력" % (version, len(expected)))
            else:
                write_lines(version + "  : ", outputs[version])
        if missing:
            write("    실행 후에도 자료 파일이 생기지 않음(v1·v2·v3) : "
                  + str(all(saves[v] is None for v in VERSIONS)))
        else:
            write("    저장된 JSON이 v1 = v2 = v3 : " + str(same_saved))
        checked = keep["v1"][0]
        if checked:
            write("    오류 명령 %d개의 직전·직후 자료 파일이 같음(v1·v2·v3) : %s" % (checked, keep_ok))

    write("")
    write("=== 2) 새 기능 검사: 장기 대여 규칙 (자료: data/items_v3.json) ===")
    with open(os.path.join(ROOT, "data", "items_v3.json"), encoding="utf-8") as f:
        original = f.read()
    for number, (kind, title, commands, expected) in enumerate(NEW_CASES, start=1):
        v1_out, v1_saved = run("v1", "items_v3.json", commands)
        v2_out, v2_saved = run("v2", "items_v3.json", commands)
        v3_out, v3_saved = run("v3", "items_v3.json", commands)
        old_error = "오류: 알 수 없는 분류입니다: 장기"
        saved = json.loads(v3_saved)
        saved_ok = True
        saved_lines = []
        for label, get, want in NEW_SAVED[number - 1]:
            got = get(saved)
            saved_ok = saved_ok and got == want
            saved_lines.append("%s 예상 %s / 실제 %s" % (label, want, got))
        unchanged = v1_saved == original and v2_saved == original
        ok = (v3_out == expected and v1_out[0] == old_error and v2_out[0] == old_error
              and saved_ok and unchanged)
        if not ok:
            fail += 1
        write("")
        write("[새 검사 %d] %s -> %s" % (number, title, "통과" if ok else "실패"))
        write_lines("입력: ", commands)
        write_lines("예상(v3): ", expected)
        write_lines("실제(v3): ", v3_out)
        write_lines("저장값(v3): ", saved_lines)
        write("    변경 전 v1의 첫 출력: " + v1_out[0])
        write("    변경 전 v2의 첫 출력: " + v2_out[0])
        write("    v1·v2 자료 파일이 바뀌지 않음 : " + str(unchanged))

    write("")
    total = len(OLD_CASES) + len(NEW_CASES)
    write("=== 요약: %d개 중 %d개 통과, %d개 실패 ===" % (total, total - fail, fail))

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "check_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
