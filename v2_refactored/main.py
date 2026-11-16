"""공유 물품 대여 프로그램 - 구조 개선 후(v2).

입력(inputs) -> 처리(service + rules) -> 저장(storage)을 이 파일이 연결한다.
실행: python v2_refactored/main.py data/items.json
"""
import sys

import inputs
import service
import storage


def handle_command(line, data_path):
    """명령 한 줄을 처리하고 화면에 보여 줄 문장을 돌려준다."""
    try:
        data = storage.load_data(data_path)             # 저장된 자료 읽기
        name, values = inputs.parse_command(line)       # 입력 검사
        if name == "list":
            return service.list_text(data)
        if name == "add":
            message = service.add_item(data, *values)   # 처리
        elif name == "rent":
            message = service.rent(data, *values)
        else:
            message = service.return_item(data, *values)
        storage.save_data(data_path, data)              # 성공했을 때만 저장
        return message
    except ValueError as error:
        return "오류: " + str(error)


def main():
    if len(sys.argv) != 2:
        print("사용법: python main.py <자료파일.json>")
        return
    print("명령: rent <품목> <이름> <날짜> | return <번호> <날짜> | add <품목> <분류> <수량> | list | quit")
    for line in sys.stdin:
        line = line.strip()
        if line == "quit":
            break
        print(handle_command(line, sys.argv[1]))


if __name__ == "__main__":
    main()
