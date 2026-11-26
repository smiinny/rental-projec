"""처리 담당: 물품 추가·대여·반납·목록. 화면 출력이나 파일 저장은 하지 않는다.

data 딕셔너리를 받아 값을 바꾸고, 결과 문장을 돌려준다.
대여 기간·연체료·안내 문구는 직접 정하지 않고 rules.get_rule()이 준 규칙 객체에 맡긴다.
"""
from inputs import parse_date
from rules import get_rule

MAX_STOCK = 999999999    # 재고 한도(보관 중 재고 + 대여 중 수량): 넘으면 저장하지 않고 오류


def list_text(data):
    lines = ["[물품]"]
    for name, item in data["items"].items():
        rule = get_rule(item["category"])          # 규칙 선택 (Strategy)
        lines.append(name + " (" + item["category"] + ") 재고 " + str(item["stock"])
                     + " | " + rule.describe())
    lines.append("[대여 중]")
    for loan in data["loans"]:
        if not loan["returned"]:
            lines.append(str(loan["id"]) + "번 " + loan["item"] + " " + loan["borrower"]
                         + " 기한 " + loan["due_date"])
    return "\n".join(lines)


def add_item(data, item_name, category, count):
    get_rule(category)                             # 등록할 수 있는 분류인지 검사
    if item_name in data["items"]:
        item = data["items"][item_name]
        if item["category"] != category:
            raise ValueError("이미 다른 분류로 등록된 품목입니다: " + item_name
                             + " (" + item["category"] + ")")
        # 대여 중인 수량도 반납되면 재고로 돌아오므로 함께 센다
        renting = sum(1 for loan in data["loans"] if loan["item"] == item_name and not loan["returned"])
        if item["stock"] + renting + count > MAX_STOCK:
            raise ValueError("재고는 최대 " + str(MAX_STOCK) + "개까지입니다: " + item_name)
        item["stock"] += count
        return "재고 추가: " + item_name + " 재고 " + str(item["stock"])
    data["items"][item_name] = {"category": category, "stock": count}
    return "물품 추가: " + item_name + " (" + category + ") 재고 " + str(count)


def rent(data, item_name, borrower, rent_date):
    if item_name not in data["items"]:
        raise ValueError("없는 품목입니다: " + item_name)
    item = data["items"][item_name]
    if item["stock"] <= 0:
        raise ValueError("재고가 없습니다: " + item_name)

    rule = get_rule(item["category"])              # 규칙 선택 (Strategy)
    try:
        due_date = rule.due_date(rent_date)
    except OverflowError:
        # 9999-12-31처럼 기한이 날짜 범위를 넘으면 사용자용 오류로 바꾼다
        raise ValueError("반납 기한이 날짜 범위를 넘습니다: " + str(rent_date))

    loan_id = len(data["loans"]) + 1
    data["loans"].append({
        "id": loan_id,
        "item": item_name,
        "borrower": borrower,
        "rent_date": str(rent_date),
        "due_date": str(due_date),
        "returned": False,
        "return_date": None,
        "fee": 0,
    })
    item["stock"] -= 1
    return ("대여 완료: " + str(loan_id) + "번 " + item_name + " (" + borrower
            + ") 반납 기한 " + str(due_date) + "\n안내: " + rule.describe())


def find_loan(data, loan_id):
    for loan in data["loans"]:
        if loan["id"] == loan_id:
            return loan
    raise ValueError("없는 대여 번호입니다: " + str(loan_id))


def return_item(data, loan_id, return_date):
    loan = find_loan(data, loan_id)
    if loan["returned"]:
        raise ValueError("이미 반납한 대여입니다: " + str(loan_id))
    if return_date < parse_date(loan["rent_date"]):
        raise ValueError("반납일이 대여일보다 빠릅니다")

    late_days = max((return_date - parse_date(loan["due_date"])).days, 0)
    rule = get_rule(data["items"][loan["item"]]["category"])   # 규칙 선택 (Strategy)
    fee = rule.late_fee(late_days)

    loan["returned"] = True
    loan["return_date"] = str(return_date)
    loan["fee"] = fee
    data["items"][loan["item"]]["stock"] += 1
    return ("반납 완료: " + str(loan_id) + "번 " + loan["item"] + " 연체 "
            + str(late_days) + "일 연체료 " + str(fee) + "원")
