"""무작위 검사: v1·v2·v3에 무작위 명령과 일부러 망가뜨린 자료를 넣어,
출력·저장 결과가 버전끼리 다르거나 프로그램이 멈추는(Traceback) 경우를 찾는다.

실행(프로젝트 최상위 폴더에서):  python tests/fuzz_check.py [횟수=300] [씨드=1]
결과는 화면과 results/fuzz_log.txt에 저장된다. 같은 씨드면 같은 입력이 만들어진다.
tests/run_checks.py가 정해 둔 상황을 확인한다면, 이 파일은 미처 생각하지 못한 입력을 넓게 훑는다.
"""
import json, os, random, subprocess, sys, tempfile, copy
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1
random.seed(SEED)
LOG = []
def say(text):
    print(text); LOG.append(text)
V = {"v1": f"{ROOT}/v1_before/rental.py", "v2": f"{ROOT}/v2_refactored/main.py", "v3": f"{ROOT}/v3_changed/main.py"}
BASE = json.load(open(f"{ROOT}/data/items.json", encoding="utf-8"))
names = ["우산", "보조배터리", "돗자리", "삼각대", "노트북", "", "우 산"]
cats = ["일반", "전자기기", "장기", "가구", "", "0"]
nums = ["0", "1", "2", "3", "9", "10", "-1", "abc", "²", "１", "999999999", "1000000000", "01", "1.5", "1e3", "٣"]
dates = ["2026-11-02", "2026-11-05", "2026-11-20", "2026-1-5", "2026-13-40", "2026-02-29", "2024-02-29",
         "0001-01-01", "9999-12-31", "9999-12-28", "2026/11/02", "abcd-ef-gh", "２０２６-11-02", "2026-11-02T00"]
def cmd():
    k = random.random()
    if k < .3: return " ".join(["rent", random.choice(names), random.choice(["김민수", "a"]), random.choice(dates)][:random.choice([1,2,3,4,4,4,5])])
    if k < .55: return " ".join(["return", random.choice(nums), random.choice(dates)][:random.choice([1,2,3,3,3,4])])
    if k < .8: return " ".join(["add", random.choice(names), random.choice(cats), random.choice(nums)][:random.choice([1,2,3,4,4,4,5])])
    if k < .9: return random.choice(["list", "list x", "LIST", "list  ", "  list", "quit x"])
    return random.choice(["", "hello", "rent", "return", "\t", "add 우산 일반 1 1"])
def mutate(d):
    d = copy.deepcopy(d); k = random.random()
    loan = {"id": 1, "item": "우산", "borrower": "a", "rent_date": "2026-11-02", "due_date": "2026-11-05",
            "returned": False, "return_date": None, "fee": 0}
    if k < .5: return d
    d["loans"].append(loan); d["items"]["우산"]["stock"] = 1
    f = random.choice(["id", "item", "borrower", "rent_date", "due_date", "returned", "return_date", "fee", "cat", "stock", "none"])
    bad = random.choice([None, [], {}, "", "x", -1, 0, 2, True, 1.5, "2026-02-30", "2026-1-5", "2026-11-01", "9999-12-31"])
    if f == "cat": d["items"]["우산"]["category"] = bad
    elif f == "stock": d["items"]["우산"]["stock"] = bad
    elif f != "none": loan[f] = bad
    return d
diff = 0; tb = 0; seen = set()
for t in range(N):
    data = mutate(BASE); cmds = [cmd() for _ in range(random.randint(1, 6))]
    res = {}
    for v, path in V.items():
        with tempfile.TemporaryDirectory() as tmp:
            json.dump(data, open(f"{tmp}/data.json", "w", encoding="utf-8"), ensure_ascii=False)
            r = subprocess.run([sys.executable, "-X", "utf8", path, "data.json"], input="\n".join(cmds + ["quit"]) + "\n",
                               capture_output=True, encoding="utf-8", cwd=tmp)
            res[v] = (r.stdout, open(f"{tmp}/data.json", encoding="utf-8").read(), r.stderr)
    for v in V:
        if "Traceback" in res[v][2]:
            tb += 1; key = ("tb", v, res[v][2].strip().splitlines()[-1][:80])
            if key not in seen:
                seen.add(key); say("TRACEBACK " + " ".join(map(str, [v, key[2], "| cmds:", cmds, "| data loans:", data["loans"][:1], data["items"].get("우산")])))
    if res["v1"][:2] != res["v2"][:2]:
        diff += 1; o1 = res["v1"][0].splitlines(); o2 = res["v2"][0].splitlines()
        first = next((i for i in range(max(len(o1), len(o2))) if (o1[i:i+1] != o2[i:i+1])), None)
        key = ("diff", (o1[first] if first is not None and first < len(o1) else "")[:40])
        if key not in seen:
            seen.add(key); say("DIFF v1/v2 " + " ".join(map(str, ["| cmds:", cmds, "| v1:", o1[first:first+1] if first is not None else "(save)", "| v2:", o2[first:first+1] if first is not None else "(save)"])))
say(f"== 씨드 {SEED}, {N}회: v1·v2 출력·저장 차이 {diff}회, Traceback(멈춤) {tb}회")
with open(os.path.join(ROOT, "results", "fuzz_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
sys.exit(1 if diff or tb else 0)
