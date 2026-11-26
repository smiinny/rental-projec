"""입력 담당: 사용자가 친 글자를 검사해서 쓸 수 있는 값으로 바꾼다."""
import re
from datetime import datetime


def parse_date(text):
    """'2026-11-16' 같은 글자를 날짜로 바꾼다. 형식이 틀리면 ValueError.

    strptime은 '2026-1-5'처럼 한 자리 월·일도 받으므로 YYYY-MM-DD 모양인지 먼저 확인한다.
    """
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            raise ValueError
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("날짜 형식이 잘못되었습니다(YYYY-MM-DD): " + text)


def to_number(text):
    """0~9로만 된 글자를 정수로 바꾼다. 바꿀 수 없으면 None.

    isdigit()만 쓰면 '²'도 통과하고, 4300자리를 넘는 숫자는 int()가 ValueError를 내므로 둘 다 막는다.
    """
    if not (text.isascii() and text.isdigit()):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_command(line):
    """한 줄 명령을 (명령 이름, 값 목록)으로 바꾼다. 형식이 틀리면 ValueError."""
    parts = line.split()
    if len(parts) == 0:
        raise ValueError("입력 형식이 잘못되었습니다")
    name = parts[0]

    if name == "list":
        if len(parts) != 1:
            raise ValueError("입력 형식이 잘못되었습니다")
        return "list", []

    if name == "add":
        if len(parts) != 4:
            raise ValueError("입력 형식이 잘못되었습니다")
        count = to_number(parts[3])
        if count is None or count < 1:
            raise ValueError("수량은 1 이상의 숫자여야 합니다: " + parts[3])
        return "add", [parts[1], parts[2], count]

    if name == "rent":
        if len(parts) != 4:
            raise ValueError("입력 형식이 잘못되었습니다")
        return "rent", [parts[1], parts[2], parse_date(parts[3])]

    if name == "return":
        if len(parts) != 3:
            raise ValueError("입력 형식이 잘못되었습니다")
        loan_id = to_number(parts[1])
        if loan_id is None:
            raise ValueError("대여 번호는 숫자여야 합니다: " + parts[1])
        return "return", [loan_id, parse_date(parts[2])]

    raise ValueError("알 수 없는 명령입니다: " + name)
