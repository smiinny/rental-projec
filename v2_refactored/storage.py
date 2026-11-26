"""저장 담당: JSON 파일을 읽고 쓰는 일만 한다."""
import json


def is_valid_data(data):
    """읽은 JSON이 이 프로그램이 쓰는 구조인지 확인한다.

    최상위는 딕셔너리이고 items는 {품목: {"category": 글자, "stock": 0 이상 정수}},
    loans는 대여 기록 딕셔너리의 목록이어야 한다. 대여 기록의 품목은 items에 있어야 한다.
    문법만 맞는 {}나 [] 같은 파일이 들어와 KeyError로 멈추는 것을 막는다.
    """
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
    for loan in loans:
        if not isinstance(loan, dict):
            return False
        if type(loan.get("id")) is not int or loan.get("item") not in items:
            return False
        if not isinstance(loan.get("borrower"), str) or type(loan.get("returned")) is not bool:
            return False
        if not isinstance(loan.get("rent_date"), str) or not isinstance(loan.get("due_date"), str):
            return False
        if loan.get("return_date") is not None and not isinstance(loan.get("return_date"), str):
            return False
        if type(loan.get("fee")) is not int:
            return False
    return True


def load_data(data_path):
    """자료 파일을 읽어 딕셔너리로 돌려준다.

    파일이 없거나, JSON 문법이 깨졌거나, 구조(items·loans와 자료형)가 맞지 않으면 ValueError.
    """
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError("자료 파일을 찾을 수 없습니다: " + data_path)
    except json.JSONDecodeError:
        raise ValueError("자료 파일 형식이 잘못되었습니다: " + data_path)
    if not is_valid_data(data):
        raise ValueError("자료 파일 구조가 잘못되었습니다: " + data_path)
    return data


def save_data(data_path, data):
    """딕셔너리를 자료 파일에 저장한다."""
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
