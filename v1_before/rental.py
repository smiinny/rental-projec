"""공유 물품 대여 프로그램 - 구조 개선 전(v1).

입력 검사, 대여 규칙, 파일 저장이 handle_command 함수 하나에 모두 들어 있다.
실행: python v1_before/rental.py data/items.json
"""
import json
import sys
from datetime import datetime, timedelta


def handle_command(line, data_path):
    # --- 저장된 자료 읽기 ---
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return "오류: 자료 파일을 찾을 수 없습니다: " + data_path

    parts = line.split()
    if len(parts) == 0:
        return "오류: 입력 형식이 잘못되었습니다"

    if parts[0] == "list":
        lines = ["[물품]"]
        for name in data["items"]:
            item = data["items"][name]
            lines.append(name + " (" + item["category"] + ") 재고 " + str(item["stock"]))
        lines.append("[대여 중]")
        for loan in data["loans"]:
            if not loan["returned"]:
                lines.append(str(loan["id"]) + "번 " + loan["item"] + " " + loan["borrower"]
                             + " 기한 " + loan["due_date"])
        return "\n".join(lines)

    elif parts[0] == "rent":
        if len(parts) != 4:
            return "오류: 입력 형식이 잘못되었습니다"
        item_name = parts[1]
        borrower = parts[2]
        try:
            rent_date = datetime.strptime(parts[3], "%Y-%m-%d").date()
        except ValueError:
            return "오류: 날짜 형식이 잘못되었습니다(YYYY-MM-DD): " + parts[3]
        if item_name not in data["items"]:
            return "오류: 없는 품목입니다: " + item_name
        item = data["items"][item_name]
        if item["stock"] <= 0:
            return "오류: 재고가 없습니다: " + item_name
        # 품목 분류별 대여 기간 (규칙이 늘어나면 이 if 문을 계속 고쳐야 한다)
        if item["category"] == "일반":
            days = 3
        elif item["category"] == "전자기기":
            days = 1
        else:
            return "오류: 알 수 없는 분류입니다: " + item["category"]
        due_date = rent_date + timedelta(days=days)
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
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return ("대여 완료: " + str(loan_id) + "번 " + item_name + " (" + borrower
                + ") 반납 기한 " + str(due_date))

    elif parts[0] == "return":
        if len(parts) != 3:
            return "오류: 입력 형식이 잘못되었습니다"
        if not parts[1].isdigit():
            return "오류: 대여 번호는 숫자여야 합니다: " + parts[1]
        loan_id = int(parts[1])
        try:
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
        # 품목 분류별 연체료 (대여 기간과 같은 분류 조건이 여기에도 반복된다)
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
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return ("반납 완료: " + str(loan_id) + "번 " + loan["item"] + " 연체 "
                + str(late_days) + "일 연체료 " + str(fee) + "원")

    else:
        return "오류: 알 수 없는 명령입니다: " + parts[0]


def main():
    if len(sys.argv) != 2:
        print("사용법: python rental.py <자료파일.json>")
        return
    print("명령: rent <품목> <이름> <날짜> | return <번호> <날짜> | list | quit")
    for line in sys.stdin:
        line = line.strip()
        if line == "quit":
            break
        print(handle_command(line, sys.argv[1]))


if __name__ == "__main__":
    main()
