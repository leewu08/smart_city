import cv2
import requests
import numpy as np
from flask import Flask, Response

# ✅ 원본 스트리밍 서버 주소 (여러 개의 서버에서 동일한 주소를 사용 가능)
STREAM_SERVER_URL = "http://10.0.66.94:5000/video_feed"

app = Flask(__name__)

def generate_frames():
    """원본 스트리밍 서버의 MJPEG 데이터를 받아서 재전송하는 함수"""
    while True:
        img_resp = requests.get(STREAM_SERVER_URL, stream=True)
        if img_resp.status_code == 200:
            bytes_stream = bytes()
            for chunk in img_resp.iter_content(chunk_size=1024):
                bytes_stream += chunk
                a = bytes_stream.find(b'\xff\xd8')
                b = bytes_stream.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = bytes_stream[a:b+2]
                    bytes_stream = bytes_stream[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                    # OpenCV에서 MJPEG로 변환
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Flask에서 스트리밍 데이터를 제공하는 엔드포인트"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """<html><body><h1>ESP32-CAM Streaming Client</h1>
              <img src="/video_feed" width="640" height="480"></body></html>"""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)