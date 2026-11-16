"""공유 물품 대여 - 웹 화면 (선택 확장).

터미널 프로그램과 같은 main.handle_command()를 그대로 불러 쓴다.
외부 패키지 없이 파이썬 표준 라이브러리(http.server)만 사용한다.

실행: python v3_changed/web_app.py data/items_v3.json
접속: 브라우저에서 http://localhost:8000
"""
import html
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

import main
import rules
import storage

DATA_PATH = "data/items_v3.json"


def rule_text(category):
    """분류의 안내 문구. 규칙이 없는 분류면 그 사실을 알려 준다."""
    try:
        return rules.get_rule(category).describe()
    except ValueError:
        return "(등록되지 않은 분류)"


def make_page(message):
    """현재 자료와 처리 결과 문장으로 HTML 화면을 만든다."""
    try:
        data = storage.load_data(DATA_PATH)
    except ValueError as error:
        return "<h1>공유 물품 대여</h1><p>오류: " + html.escape(str(error)) + "</p>"

    today = str(date.today())
    item_rows = ""
    item_options = ""
    for name, item in data["items"].items():
        item_rows += ("<tr><td>" + html.escape(name) + "</td><td>" + html.escape(item["category"])
                      + "</td><td>" + str(item["stock"]) + "</td><td>"
                      + html.escape(rule_text(item["category"])) + "</td></tr>")
        item_options += "<option>" + html.escape(name) + "</option>"

    category_options = ""
    for category in rules.RULES:
        category_options += "<option>" + html.escape(category) + "</option>"

    loan_rows = ""
    for loan in data["loans"]:
        if loan["returned"]:
            continue
        loan_rows += ("<tr><td>" + str(loan["id"]) + "</td><td>" + html.escape(loan["item"])
                      + "</td><td>" + html.escape(loan["borrower"]) + "</td><td>" + loan["due_date"]
                      + "</td><td><form method='post' action='/return'>"
                      + "<input type='hidden' name='loan_id' value='" + str(loan["id"]) + "'>"
                      + "<input type='date' name='date' value='" + today + "'> "
                      + "<button>반납</button></form></td></tr>")
    if loan_rows == "":
        loan_rows = "<tr><td colspan='5'>대여 중인 물품이 없습니다.</td></tr>"

    # 결과 문장이 두 줄(대여 완료 + 안내)일 수 있으므로 줄바꿈을 <br>로 바꾼다.
    message_html = html.escape(message).replace("\n", "<br>")

    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>공유 물품 대여</title>
<style>
 body { font-family: sans-serif; max-width: 760px; margin: 30px auto; }
 table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
 th, td { border: 1px solid #999; padding: 6px 10px; text-align: left; }
 th { background: #eee; }
 .message { padding: 10px; background: #f3f3f3; border-left: 4px solid #555; }
</style></head><body>
<h1>공유 물품 대여</h1>
<p class="message">""" + message_html + """</p>
<h2>대여 신청</h2>
<form method="post" action="/rent">
 품목 <select name="item">""" + item_options + """</select>
 이름 <input name="borrower" size="8">
 대여일 <input type="date" name="date" value='""" + today + """'>
 <button>대여</button>
</form>
<h2>물품 재고와 대여 규칙</h2>
<table><tr><th>품목</th><th>분류</th><th>재고</th><th>반납 기한 · 연체료 안내</th></tr>""" + item_rows + """</table>
<h2>대여 중</h2>
<table><tr><th>번호</th><th>품목</th><th>빌린 사람</th><th>반납 기한</th><th>반납</th></tr>""" + loan_rows + """</table>
<h2>물품 추가</h2>
<form method="post" action="/add">
 품목 <input name="item" size="10">
 분류 <select name="category">""" + category_options + """</select>
 수량 <input type="number" name="count" value="1" min="1" style="width:60px">
 <button>추가</button>
</form>
<p>이미 있는 품목을 같은 분류로 추가하면 재고가 늘어납니다.</p>
</body></html>"""


class RentalHandler(BaseHTTPRequestHandler):
    def send_page(self, message):
        body = make_page(message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_page("품목을 고르고 이름을 적어 대여하세요.")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))

        def value(key):
            # 값 안의 공백은 명령을 나누는 기준과 겹치므로 없앤다.
            return "".join(form.get(key, [""])[0].split())

        if self.path == "/rent":
            line = "rent " + value("item") + " " + value("borrower") + " " + value("date")
        elif self.path == "/return":
            line = "return " + value("loan_id") + " " + value("date")
        elif self.path == "/add":
            line = "add " + value("item") + " " + value("category") + " " + value("count")
        else:
            line = ""
        # 화면에서 받은 값을 터미널과 같은 명령 한 줄로 바꿔 같은 함수에 넘긴다.
        self.send_page(main.handle_command(line, DATA_PATH))


if __name__ == "__main__":
    if len(sys.argv) == 2:
        DATA_PATH = sys.argv[1]
    print("웹 화면 실행 중: http://localhost:8000  (끝내려면 Ctrl+C)")
    HTTPServer(("localhost", 8000), RentalHandler).serve_forever()
