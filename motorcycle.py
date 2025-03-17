import cv2
import numpy as np
import threading
import time
import os
import urllib.request
from datetime import datetime
from ultralytics import YOLO

# ✅ ESP32-CAM 스트리밍 URL
ESP32_CAM_URL = "http://10.0.66.32:5000/stream"

# ✅ 저장 폴더 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOTORCYCLE_IMAGE_FOLDER = os.path.join(BASE_DIR, "static", "motorcycle_images")
os.makedirs(MOTORCYCLE_IMAGE_FOLDER, exist_ok=True)

# ✅ YOLOv8 모델 로드
MODEL_PATH = os.path.join(BASE_DIR, "yolov8s.pt")
model = YOLO(MODEL_PATH)

# ✅ 오토바이 감지 상태 변수
motorcycle_detected = False
last_motorcycle_time = 0
ALERT_THRESHOLD = 5  # 5초 이상 같은 위치에서 감지되면 알람

# ✅ 프레임을 저장하는 변수
frame = None
lock = threading.Lock()


def detect_motorcycle():
    """ESP32-CAM에서 프레임을 가져와 오토바이를 감지하는 함수"""
    global motorcycle_detected, last_motorcycle_time, frame
    stream = urllib.request.urlopen(ESP32_CAM_URL)
    bytes_stream = b""

    while True:
        try:
            bytes_stream += stream.read(1024)
            a = bytes_stream.find(b"\xff\xd8")
            b = bytes_stream.find(b"\xff\xd9")

            if a != -1 and b != -1:
                jpg = bytes_stream[a:b + 2]
                bytes_stream = bytes_stream[b + 2:]

                with lock:
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                # ✅ YOLOv8으로 오토바이 감지
                results = model(frame, conf=0.5)
                detected = False  # 오토바이 감지 여부

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = model.names[int(box.cls[0])]

                        if label == "motorcycle":
                            detected = True
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, "Motorcycle", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                            # ✅ 감지된 오토바이 이미지 저장
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            img_path = os.path.join(MOTORCYCLE_IMAGE_FOLDER, f"motorcycle_{timestamp}.jpg")
                            cv2.imwrite(img_path, frame)
                            print(f"📸 오토바이 감지! 이미지 저장: {img_path}")

                # ✅ 오토바이 감지 상태 업데이트
                if detected:
                    motorcycle_detected = True
                    last_motorcycle_time = time.time()
                elif time.time() - last_motorcycle_time > ALERT_THRESHOLD:
                    motorcycle_detected = False  # 일정 시간이 지나면 감지 상태 해제

        except Exception as e:
            print(f"❌ ESP32-CAM 스트리밍 오류: {e}")
            break


def get_video_frame():
    """실시간 영상 프레임을 웹 페이지에 전송하는 함수"""
    while True:
        with lock:
            if frame is None:
                continue
            img = frame.copy()

        # ✅ 프레임을 JPEG 형식으로 변환하여 스트리밍
        _, buffer = cv2.imencode(".jpg", img)
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


def get_alert_status():
    """오토바이 감지 상태 반환"""
    return {"motorcycle_detected": motorcycle_detected}


# ✅ 오토바이 감지를 위한 백그라운드 스레드 실행
threading.Thread(target=detect_motorcycle, daemon=True).start()
