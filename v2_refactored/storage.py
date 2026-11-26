"""저장 담당: JSON 파일을 읽고 쓰는 일만 한다."""
import json


def load_data(data_path):
    """자료 파일을 읽어 딕셔너리로 돌려준다. 파일이 없거나 JSON 형식이 깨졌으면 ValueError."""
    try:
        with open(data_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError("자료 파일을 찾을 수 없습니다: " + data_path)
    except json.JSONDecodeError:
        raise ValueError("자료 파일 형식이 잘못되었습니다: " + data_path)


def save_data(data_path, data):
    """딕셔너리를 자료 파일에 저장한다."""
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
