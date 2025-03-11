#웹으로 데이터를 전송하는 API 서버
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# 최근 받은 데이터를 저장할 변수 (초기값)
received_data = {"message": "No data received"}

@app.route("/api", methods=["GET", "POST"])
def api():
    global received_data

    if request.method == "POST":
        # JSON 요청인지 확인
        if request.is_json:
            received_data = request.get_json()
            return jsonify({"status": "success", "message": "JSON data received", "data": received_data})

        # 폼 데이터 요청인지 확인
        if not request.form:
            return jsonify({"status": "error", "message": "No data received"}), 400

        raw_data_list = list(request.form.keys())
        if not raw_data_list:
            return jsonify({"status": "error", "message": "Empty form data"}), 400

        raw_data = raw_data_list[0]

        # 데이터를 파싱하여 딕셔너리 형태로 변환
        data_dict = {}
        pairs = raw_data.split("|")
        for pair in pairs:
            key_value = pair.strip().split(":")
            if len(key_value) == 2:
                key, value = key_value[0].strip(), key_value[1].strip()
                data_dict[key] = value

        received_data = data_dict  # 최신 데이터 저장
        print(f"📩 변환된 데이터: {received_data}")  # 터미널에서 확인

        return jsonify({"status": "success", "message": "Form data received", "data": received_data})

    # GET 요청 시 최근 저장된 데이터 반환
    return jsonify(received_data)

@app.route("/")
def index():
    return render_template("api.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010, debug=True)