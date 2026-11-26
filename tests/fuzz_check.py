"""무작위 검사: v1·v2·v3에 무작위 명령과 일부러 망가뜨린 자료를 넣어 버전끼리 결과를 비교한다.

실행(프로젝트 최상위 폴더에서):
    python tests/fuzz_check.py                 # 씨드 1로 300회
    python tests/fuzz_check.py 1000 1 2 3      # 씨드 1, 2, 3으로 각각 1000회 (총 3000회)
결과는 화면과 results/fuzz_log.txt에 저장된다. 로그에는 씨드별 횟수·결과와 전체 합계가 모두 남는다.
같은 씨드면 같은 입력이 만들어지므로 누구나 같은 실행을 다시 할 수 있다.

비교 대상과 판단 기준
  - v1 ↔ v2 (리팩터링 전후): 모든 입력에서 화면 출력과 실행 후 자료 파일(JSON 글자)이 완전히 같아야 한다.
  - v2 ↔ v3 (기능 변경 전후): '장기' 분류가 들어간 명령은 의도한 변경이라 비교에서 뺀다.
    그 밖의 입력에서는 화면 출력과 실행 후 자료 파일이 완전히 같아야 한다.
  - 멈춤: v1·v2·v3 어느 버전이든 오류 출력에 Traceback이 나오면 멈춘 것으로 센다.
  하나라도 해당하면 그 입력을 로그에 남기고, 실행이 끝나면 실패(종료 코드 1)로 끝낸다.

tests/run_checks.py가 정해 둔 상황을 확인한다면, 이 파일은 미처 생각하지 못한 입력을 넓게 훑는다.
"""
import copy
import json
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = {"v1": f"{ROOT}/v1_before/rental.py", "v2": f"{ROOT}/v2_refactored/main.py", "v3": f"{ROOT}/v3_changed/main.py"}
BASE = json.load(open(f"{ROOT}/data/items.json", encoding="utf-8"))

NAMES = ["우산", "보조배터리", "돗자리", "삼각대", "노트북", "", "우 산"]
CATS = ["일반", "전자기기", "장기", "가구", "", "0"]
NUMS = ["0", "1", "2", "3", "9", "10", "-1", "abc", "²", "１", "999999999", "1000000000", "01", "1.5", "1e3", "٣"]
DATES = ["2026-11-02", "2026-11-05", "2026-11-20", "2026-1-5", "2026-13-40", "2026-02-29", "2024-02-29",
         "0001-01-01", "9999-12-31", "9999-12-28", "2026/11/02", "abcd-ef-gh", "２０２６-11-02", "2026-11-02T00"]
BAD_VALUES = [None, [], {}, "", "x", -1, 0, 2, True, 1.5, "2026-02-30", "2026-1-5", "2026-11-01", "9999-12-31"]

LOG = []


def say(text):
    print(text)
    LOG.append(text)


def make_command(rng):
    """틀린 숫자·날짜·인수 개수가 섞인 명령 한 줄을 만든다."""
    k = rng.random()
    if k < .3:
        return " ".join(["rent", rng.choice(NAMES), rng.choice(["김민수", "a"]), rng.choice(DATES)][:rng.choice([1, 2, 3, 4, 4, 4, 5])])
    if k < .55:
        return " ".join(["return", rng.choice(NUMS), rng.choice(DATES)][:rng.choice([1, 2, 3, 3, 3, 4])])
    if k < .8:
        return " ".join(["add", rng.choice(NAMES), rng.choice(CATS), rng.choice(NUMS)][:rng.choice([1, 2, 3, 4, 4, 4, 5])])
    if k < .9:
        return rng.choice(["list", "list x", "LIST", "list  ", "  list", "quit x"])
    return rng.choice(["", "hello", "rent", "return", "\t", "add 우산 일반 1 1"])


def make_data(rng):
    """자료 파일에 쓸 바이트를 만든다.

    대략 절반은 정상 자료, 나머지는 대여 기록 하나를 넣고 그중 한 값을 망가뜨린 자료이고,
    가끔은 UTF-8이 아닌 글자나 깨진 JSON 문법을 넣는다.
    """
    data = copy.deepcopy(BASE)
    k = rng.random()
    if k < .04:
        return json.dumps(data, ensure_ascii=False).encode("euc-kr")       # UTF-8이 아닌 한글
    if k < .08:
        return rng.choice([b"", b"{", b"[]", b"null", b"\xff\xfe{}", b'{"items": {}, "loans": []',
                           b'{"items": {"\xec\x9a\xb0\xec\x82\xb0": {"category": "\xec\x9d\xbc\xeb\xb0\x98", "stock": '
                           + b"1" * 5000 + b'}}, "loans": []}'])
    if k < .5:
        return json.dumps(data, ensure_ascii=False).encode("utf-8")
    loan = {"id": 1, "item": "우산", "borrower": "a", "rent_date": "2026-11-02", "due_date": "2026-11-05",
            "returned": False, "return_date": None, "fee": 0}
    data["loans"].append(loan)
    data["items"]["우산"]["stock"] = 1
    field = rng.choice(["id", "item", "borrower", "rent_date", "due_date", "returned", "return_date", "fee",
                        "cat", "stock", "none"])
    bad = rng.choice(BAD_VALUES)
    if field == "cat":
        data["items"]["우산"]["category"] = bad
    elif field == "stock":
        data["items"]["우산"]["stock"] = bad
    elif field != "none":
        loan[field] = bad
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def run_version(path, data, commands):
    """자료 복사본으로 한 버전을 실행하고 (화면 출력, 실행 후 자료 파일 글자, 오류 출력)을 돌려준다."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(f"{tmp}/data.json", "wb") as f:
            f.write(data)
        result = subprocess.run([sys.executable, "-X", "utf8", path, "data.json"],
                                input="\n".join(commands + ["quit"]) + "\n",
                                capture_output=True, encoding="utf-8", cwd=tmp)
        with open(f"{tmp}/data.json", "rb") as f:
            saved = f.read()
    return result.stdout, saved, result.stderr


def run_seed(seed, count):
    """한 씨드로 count회 검사하고 (v1↔v2 차이, v2↔v3 차이, v2↔v3 비교 횟수, 멈춤) 수를 돌려준다."""
    rng = random.Random(seed)
    diff12 = diff23 = compared23 = stops = 0
    for _ in range(count):
        data = make_data(rng)
        commands = [make_command(rng) for _ in range(rng.randint(1, 6))]
        res = {v: run_version(path, data, commands) for v, path in V.items()}
        for v in V:
            if "Traceback" in res[v][2]:
                stops += 1
                say("  멈춤 %s | %s | 명령 %s" % (v, res[v][2].strip().splitlines()[-1][:80], commands))
        if res["v1"][:2] != res["v2"][:2]:
            diff12 += 1
            say("  v1≠v2 | 명령 %s" % commands)
        if not any("장기" in c for c in commands):
            compared23 += 1
            if res["v2"][:2] != res["v3"][:2]:
                diff23 += 1
                say("  v2≠v3 | 명령 %s" % commands)
    return diff12, diff23, compared23, stops


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seeds = [int(s) for s in sys.argv[2:]] or [1]
    say("무작위 검사: 씨드 %s, 씨드마다 %d회" % (", ".join(map(str, seeds)), count))
    total = [0, 0, 0, 0]
    for seed in seeds:
        d12, d23, c23, stops = run_seed(seed, count)
        say("== 씨드 %d, %d회: v1·v2 차이 %d회 | v2·v3 차이 %d회('장기' 없는 %d회 비교) | 멈춤 %d회"
            % (seed, count, d12, d23, c23, stops))
        total = [a + b for a, b in zip(total, (d12, d23, c23, stops))]
    say("== 합계 %d회: v1·v2 차이 %d회 | v2·v3 차이 %d회('장기' 없는 %d회 비교) | 멈춤 %d회"
        % (count * len(seeds), total[0], total[1], total[2], total[3]))
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "fuzz_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")
    sys.exit(1 if total[0] or total[1] or total[3] else 0)


if __name__ == "__main__":
    main()
