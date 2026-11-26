"""저장 담당: JSON 파일을 읽고 쓰는 일만 한다."""
import json
import os
import re
from datetime import datetime

MAX_STOCK = 999999999    # 재고 한도(보관 중 재고 + 대여 중 수량): 넘는 자료는 읽지 않고, 넘게 만드는 추가는 거부


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
    # 품목마다 보관 중 재고 + 반납되지 않은 수량이 재고 한도(MAX_STOCK)를 넘으면 안 된다
    for name, item in items.items():
        renting = sum(1 for loan in loans if loan["item"] == name and not loan["returned"])
        if item["stock"] + renting > MAX_STOCK:
            return False
    return True


def load_data(data_path):
    """자료 파일을 읽어 딕셔너리로 돌려준다.

    파일이 없거나, 열 수 없거나, UTF-8·JSON 문법이 깨졌거나, 구조(items·loans와 자료형)가 맞지 않으면 ValueError.
    """
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f, parse_int=parse_json_int)
    except FileNotFoundError:
        raise ValueError("자료 파일을 찾을 수 없습니다: " + data_path)
    except ValueError:
        # JSON 문법 오류, UTF-8로 읽을 수 없는 글자, 너무 긴 정수 모두 형식 오류로 본다
        raise ValueError("자료 파일 형식이 잘못되었습니다: " + data_path)
    except OSError:
        # 폴더이거나 읽기 권한이 없는 등 파일을 열 수 없는 경우
        raise ValueError("자료 파일을 읽을 수 없습니다: " + data_path)
    if not is_valid_data(data):
        raise ValueError("자료 파일 구조가 잘못되었습니다: " + data_path)
    return data


def save_data(data_path, data):
    """딕셔너리를 자료 파일에 저장한다. 실패하면 원본은 그대로 두고 ValueError."""
    write_json_safely(data_path, data)
