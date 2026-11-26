"""공유 물품 대여 프로그램 - 구조 개선 전(v1).

입력 검사, 대여 규칙, 파일 저장이 handle_command 함수 하나에 모두 들어 있다.
실행: python v1_before/rental.py data/items.json
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta

MAX_DIGITS = 9    # 수량·대여 번호는 0~9로 된 최대 9자리 숫자만 받는다 (Python 버전과 무관하게 같은 기준)


def parse_json_int(text):
    """자료 파일(JSON) 안의 정수를 바꾼다. 15자리를 넘으면 ValueError.

    Python 버전에 따라 아주 긴 정수를 받기도 하고 거부하기도 하므로, 자릿수를 직접 제한해
    어느 환경에서나 "자료 파일 형식이 잘못되었습니다"라는 같은 결과를 낸다.
    """
    if len(text.lstrip("-")) > 15:
        raise ValueError("정수가 너무 깁니다")
    return int(text)


def write_json_safely(data_path, data):
    """임시 파일(자료 파일 이름 + .tmp)에 끝까지 쓴 뒤 원본과 바꾼다.

    쓰는 도중 실패해도 원본 자료 파일은 그대로 남는다. 실패하면 ValueError.
    """
    temp_path = data_path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, data_path)     # 다 쓴 임시 파일로 한 번에 교체
    except OSError:
        if os.path.isfile(temp_path):
            os.remove(temp_path)             # 쓰다 만 임시 파일만 지운다
        raise ValueError("자료 파일을 저장할 수 없습니다: " + data_path)


def is_valid_data(data):
    """읽은 JSON이 이 프로그램이 쓰는 구조인지 확인한다. 맞으면 True.

    - 최상위는 딕셔너리이고 items는 {품목: {"category": 글자, "stock": 0 이상 정수}}
    - loans는 대여 기록 딕셔너리의 목록이고, 번호(id)는 1부터 차례대로 붙어 있어야 한다
    - 대여 기록의 item은 items에 있는 품목 이름(글자), 날짜는 실제 있는 YYYY-MM-DD 날짜
    - 반납 전 기록은 return_date가 null이고 연체료 0, 반납한 기록은 반납일과 0 이상 연체료가 있어야 한다
    문법만 맞는 {}, 자료형이 틀린 값, 해석할 수 없는 날짜가 들어와 프로그램이 멈추는 것을 막는다.
    """
    def to_date(text):
        if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    if not isinstance(data, dict):
        return False
    items = data.get("items")
    loans = data.get("loans")
    if not isinstance(items, dict) or not isinstance(loans, list):
        return False
    for item in items.values():
        if not isinstance(item, dict) or not isinstance(item.get("category"), str):
            return False
        stock = item.get("stock")
        if type(stock) is not int or stock < 0:
            return False
    for number, loan in enumerate(loans, start=1):
        if not isinstance(loan, dict):
            return False
        if type(loan.get("id")) is not int or loan.get("id") != number:
            return False
        if not isinstance(loan.get("item"), str) or loan.get("item") not in items:
            return False
        if not isinstance(loan.get("borrower"), str) or type(loan.get("returned")) is not bool:
            return False
        rent_date = to_date(loan.get("rent_date"))
        due_date = to_date(loan.get("due_date"))
        if rent_date is None or due_date is None or due_date < rent_date:
            return False
        fee = loan.get("fee")
        if type(fee) is not int or fee < 0:
            return False
        if loan["returned"]:
            return_date = to_date(loan.get("return_date"))
            if return_date is None or return_date < rent_date:
                return False
        elif loan.get("return_date") is not None or fee != 0:
            return False
    return True


def handle_command(line, data_path):
    # --- 저장된 자료 읽기 ---
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f, parse_int=parse_json_int)
    except FileNotFoundError:
        return "오류: 자료 파일을 찾을 수 없습니다: " + data_path
    except ValueError:
        # JSON 문법 오류, UTF-8로 읽을 수 없는 글자, 너무 긴 정수 모두 형식 오류로 본다
        return "오류: 자료 파일 형식이 잘못되었습니다: " + data_path
    except OSError:
        # 폴더이거나 읽기 권한이 없는 등 파일을 열 수 없는 경우
        return "오류: 자료 파일을 읽을 수 없습니다: " + data_path
    if not is_valid_data(data):
        return "오류: 자료 파일 구조가 잘못되었습니다: " + data_path

    parts = line.split()
    if len(parts) == 0:
        return "오류: 입력 형식이 잘못되었습니다"

    if parts[0] == "list":
        if len(parts) != 1:
            return "오류: 입력 형식이 잘못되었습니다"
        lines = ["[물품]"]
        for name in data["items"]:
            item = data["items"][name]
            # 분류별 안내 문구 (분류 조건 1번째)
            if item["category"] == "일반":
                guide = "3일 대여, 연체료 하루 500원(최대 3000원)"
            elif item["category"] == "전자기기":
                guide = "1일 대여, 연체료 하루 1000원"
            else:
                return "오류: 알 수 없는 분류입니다: " + item["category"]
            lines.append(name + " (" + item["category"] + ") 재고 " + str(item["stock"])
                         + " | " + guide)
        lines.append("[대여 중]")
        for loan in data["loans"]:
            if not loan["returned"]:
                lines.append(str(loan["id"]) + "번 " + loan["item"] + " " + loan["borrower"]
                             + " 기한 " + loan["due_date"])
        return "\n".join(lines)

    elif parts[0] == "add":
        if len(parts) != 4:
            return "오류: 입력 형식이 잘못되었습니다"
        item_name = parts[1]
        category = parts[2]
        # isdigit()은 '²' 같은 문자도 숫자로 보므로 0~9만, 그리고 최대 9자리까지만 허용한다
        count = 0
        if parts[3].isascii() and parts[3].isdigit() and len(parts[3]) <= MAX_DIGITS:
            count = int(parts[3])
        if count < 1:
            return "오류: 수량은 1 이상의 숫자여야 합니다: " + parts[3]
        # 등록할 수 있는 분류인지 검사 (분류 조건 2번째)
        if category != "일반" and category != "전자기기":
            return "오류: 알 수 없는 분류입니다: " + category
        if item_name in data["items"]:
            item = data["items"][item_name]
            if item["category"] != category:
                return ("오류: 이미 다른 분류로 등록된 품목입니다: " + item_name
                        + " (" + item["category"] + ")")
            item["stock"] = item["stock"] + count
            message = "재고 추가: " + item_name + " 재고 " + str(item["stock"])
        else:
            data["items"][item_name] = {"category": category, "stock": count}
            message = "물품 추가: " + item_name + " (" + category + ") 재고 " + str(count)
        try:
            write_json_safely(data_path, data)
        except ValueError as error:
            return "오류: " + str(error)
        return message

    elif parts[0] == "rent":
        if len(parts) != 4:
            return "오류: 입력 형식이 잘못되었습니다"
        item_name = parts[1]
        borrower = parts[2]
        try:
            # strptime은 '2026-1-5'도 받으므로 YYYY-MM-DD 모양인지 먼저 확인한다
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", parts[3]):
                raise ValueError
            rent_date = datetime.strptime(parts[3], "%Y-%m-%d").date()
        except ValueError:
            return "오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): " + parts[3]
        if item_name not in data["items"]:
            return "오류: 없는 품목입니다: " + item_name
        item = data["items"][item_name]
        if item["stock"] <= 0:
            return "오류: 재고가 없습니다: " + item_name
        # 분류별 대여 기간과 안내 문구 (분류 조건 3번째)
        if item["category"] == "일반":
            days = 3
            guide = "3일 대여, 연체료 하루 500원(최대 3000원)"
        elif item["category"] == "전자기기":
            days = 1
            guide = "1일 대여, 연체료 하루 1000원"
        else:
            return "오류: 알 수 없는 분류입니다: " + item["category"]
        try:
            due_date = rent_date + timedelta(days=days)
        except OverflowError:
            # 9999-12-31처럼 기한이 날짜 범위를 넘으면 프로그램이 멈추지 않고 오류 문장을 낸다
            return "오류: 반납 기한이 날짜 범위를 넘습니다: " + str(rent_date)
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
        item["stock"] = item["stock"] - 1
        try:
            write_json_safely(data_path, data)
        except ValueError as error:
            return "오류: " + str(error)
        return ("대여 완료: " + str(loan_id) + "번 " + item_name + " (" + borrower
                + ") 반납 기한 " + str(due_date) + "\n안내: " + guide)

    elif parts[0] == "return":
        if len(parts) != 3:
            return "오류: 입력 형식이 잘못되었습니다"
        if not (parts[1].isascii() and parts[1].isdigit() and len(parts[1]) <= MAX_DIGITS):
            return "오류: 대여 번호는 숫자여야 합니다: " + parts[1]
        loan_id = int(parts[1])
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", parts[2]):
                raise ValueError
            return_date = datetime.strptime(parts[2], "%Y-%m-%d").date()
        except ValueError:
            return "오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): " + parts[2]
        loan = None
        for one in data["loans"]:
            if one["id"] == loan_id:
                loan = one
        if loan is None:
            return "오류: 없는 대여 번호입니다: " + str(loan_id)
        if loan["returned"]:
            return "오류: 이미 반납한 대여입니다: " + str(loan_id)
        rent_date = datetime.strptime(loan["rent_date"], "%Y-%m-%d").date()
        due_date = datetime.strptime(loan["due_date"], "%Y-%m-%d").date()
        if return_date < rent_date:
            return "오류: 반납일이 대여일보다 빠릅니다"
        late_days = (return_date - due_date).days
        if late_days < 0:
            late_days = 0
        # 분류별 연체료 (분류 조건 4번째)
        category = data["items"][loan["item"]]["category"]
        if category == "일반":
            fee = late_days * 500
            if fee > 3000:
                fee = 3000
        elif category == "전자기기":
            fee = late_days * 1000
        else:
            return "오류: 알 수 없는 분류입니다: " + category
        loan["returned"] = True
        loan["return_date"] = str(return_date)
        loan["fee"] = fee
        data["items"][loan["item"]]["stock"] += 1
        try:
            write_json_safely(data_path, data)
        except ValueError as error:
            return "오류: " + str(error)
        return ("반납 완료: " + str(loan_id) + "번 " + loan["item"] + " 연체 "
                + str(late_days) + "일 연체료 " + str(fee) + "원")

    else:
        return "오류: 알 수 없는 명령입니다: " + parts[0]


def main():
    if len(sys.argv) != 2:
        print("사용법: python rental.py <자료파일.json>")
        return
    print("명령: rent <품목> <이름> <날짜> | return <번호> <날짜> | add <품목> <분류> <수량> | list | quit")
    for line in sys.stdin:
        line = line.strip()
        if line == "quit":
            break
        print(handle_command(line, sys.argv[1]))


if __name__ == "__main__":
    main()
