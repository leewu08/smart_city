from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
  # 올바른 Flask 인스턴스 생성

# 현재 LED 상태 저장
led_state = {'LED1': 'OFF', 'LED2': 'OFF', 'AUTO_MODE1': False, 'AUTO_MODE2': False}

@app.route('/control_led', methods=['POST'])
def control_led():
    """ 아두이노가 LED 상태를 가져가기 위한 API """
    data = request.json
    device_id = data.get('ID')  # 제어할 아두이노 ID

    if device_id == "1":
        return jsonify({'LED1': led_state['LED1'], 'AUTO_MODE1': led_state['AUTO_MODE1']})
    elif device_id == "2":
        return jsonify({'LED2': led_state['LED2'], 'AUTO_MODE2': led_state['AUTO_MODE2']})

    return jsonify({'error': 'Invalid device ID'}), 400

@app.route('/set_led', methods=['POST'])
def set_led():
    """ 웹에서 LED 상태를 변경하는 API """
    data = request.json
    action = data.get('action')  # 'LED_ON', 'LED_OFF', 'AUTO_MODE'
    device_id = data.get('ID')

    if device_id == "1":
        if action == "LED_ON":
            led_state['LED1'] = 'ON'
        elif action == "LED_OFF":
            led_state['LED1'] = 'OFF'
        elif action == "AUTO_MODE":
            led_state['AUTO_MODE1'] = not led_state['AUTO_MODE1']

    elif device_id == "2":
        if action == "LED_ON":
            led_state['LED2'] = 'ON'
        elif action == "LED_OFF":
            led_state['LED2'] = 'OFF'
        elif action == "AUTO_MODE":
            led_state['AUTO_MODE2'] = not led_state['AUTO_MODE2']

    return jsonify({'status': 'success', 'led_state': led_state})

@app.route('/')
def index():
    return render_template("LedControl.html")  # 'templates' 폴더에 있어야 함

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=True)
