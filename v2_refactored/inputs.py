"""입력 담당: 사용자가 친 글자를 검사해서 쓸 수 있는 값으로 바꾼다."""
from datetime import datetime


def parse_date(text):
    """'2026-11-16' 같은 글자를 날짜로 바꾼다. 형식이 틀리면 ValueError."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("날짜 형식이 잘못되었습니다(YYYY-MM-DD): " + text)


def parse_command(line):
    """한 줄 명령을 (명령 이름, 값 목록)으로 바꾼다. 형식이 틀리면 ValueError."""
    parts = line.split()
    if len(parts) == 0:
        raise ValueError("입력 형식이 잘못되었습니다")
    name = parts[0]

    if name == "list":
        return "list", []

    if name == "rent":
        if len(parts) != 4:
            raise ValueError("입력 형식이 잘못되었습니다")
        return "rent", [parts[1], parts[2], parse_date(parts[3])]

    if name == "return":
        if len(parts) != 3:
            raise ValueError("입력 형식이 잘못되었습니다")
        if not parts[1].isdigit():
            raise ValueError("대여 번호는 숫자여야 합니다: " + parts[1])
        return "return", [int(parts[1]), parse_date(parts[2])]

    raise ValueError("알 수 없는 명령입니다: " + name)
