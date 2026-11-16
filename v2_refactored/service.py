"""처리 담당: 대여·반납·목록. 화면 출력이나 파일 저장은 하지 않는다.

data 딕셔너리를 받아 값을 바꾸고, 결과 문장을 돌려준다.
대여 기간과 연체료는 직접 계산하지 않고 rules.get_rule()이 준 규칙 객체에 맡긴다.
"""
from inputs import parse_date
from rules import get_rule


def list_text(data):
    lines = ["[물품]"]
    for name, item in data["items"].items():
        lines.append(name + " (" + item["category"] + ") 재고 " + str(item["stock"]))
    lines.append("[대여 중]")
    for loan in data["loans"]:
        if not loan["returned"]:
            lines.append(str(loan["id"]) + "번 " + loan["item"] + " " + loan["borrower"]
                         + " 기한 " + loan["due_date"])
    return "\n".join(lines)


def rent(data, item_name, borrower, rent_date):
    if item_name not in data["items"]:
        raise ValueError("없는 품목입니다: " + item_name)
    item = data["items"][item_name]
    if item["stock"] <= 0:
        raise ValueError("재고가 없습니다: " + item_name)

    rule = get_rule(item["category"])          # 규칙 선택 (Strategy)
    due_date = rule.due_date(rent_date)

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
            + ") 반납 기한 " + str(due_date))


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
