from flask import Flask, session, url_for, render_template, flash, before_render_template, send_from_directory, jsonify ,request, redirect, Response
import os
import requests
from datetime import datetime, timedelta
from functools import wraps
from models import DBManager
from markupsafe import Markup
import json
import re
import threading
import license_plate
import cv2
import motorcycle

from api import handle_request  # api.py에서 handle_request 함수 불러오기
## sy branch
app = Flask(__name__)



app.secret_key = 'your-secret-key'  # 비밀 키 설정, 실제 애플리케이션에서는 더 안전한 방법으로 설정해야 함if __name__ == '__main__':
road_url = "http://10.0.66.14:5000/stream"
manager = DBManager()

# led센서 테스트
# @app.route('/test')
# def test():
#     return render_template('ledtest.html')

# led센서 테스트2
# @app.route('/led_control', methods=['GET'])
# def control_led():
#     command = request.args.get('command')
#     if command:
#         # 여기에서 MIT 인벤터에 명령을 전달하는 코드 필요
#         print(f"Received command: {command}")
#         return "Command Received"
#     return "No Command", 400


# 파일 업로드 경로 설정
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
# 업로드 폴더가 없으면 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask서버 실행시 보안상태 업데이트
@app.before_request
def update_security_status_on_start():
    if not hasattr(app, "has_run"):
        manager.user_update_security_status()
        app.has_run = True  # 실행 여부 저장


@app.route("/api", methods=["GET", "POST"])
def api():
    return handle_request()  # handle_request() 함수 호출


### 푸터에 들어갈 날짜데이터 (context_processor 사용)
@app.context_processor
def inject_full_date():
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    today_date = datetime.now()
    today = today_date.strftime("%Y년 %m월 %d일")
    weekday = weekdays[today_date.weekday()]
    full_date = f"{today} ({weekday})"
    return {"full_date": full_date}

### 홈페이지
@app.route('/')
def index():
    return render_template('index.html')

# 홈페이지에서 소개 페이지
@app.route('/index_about')
def index_about():
    return render_template('about.html')

### 회원가입 페이지등록 
#회원가입
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user_name = request.form['username']
        user_id = request.form['userid']
        password = request.form['password']
        address= request.form['address']
        gender = request.form['gender']
        email = request.form['email']
        birthday = request.form['birthday']
        reg_number = request.form['total_regnumber']
        
        #회원과 아이디가 중복되는지 확인
        if manager.duplicate_users(user_id):
            flash('이미 존재하는 아이디 입니다.', 'error')
            return render_template('register.html')
        
        #회원 이메일과 중복여부
        if manager.duplicate_email(email):
            flash('이미 등록된 이메일 입니다.', 'error')
            return render_template('register.html')
        
        if manager.duplicate_reg_number(reg_number):
            flash('이미 등록된 주민번호 입니다.', 'error')
            return render_template('register.html')


        if manager.register_users(user_id, user_name, password, email, address, birthday, reg_number, gender):
            flash('회원가입 신청이 완료되었습니다.', 'success')
            return redirect(url_for('index'))
        
        flash('회원가입에 실패했습니다.', 'error')
        return redirect(url_for('register'))
    return render_template('register.html')

# 이용약관 페이지
@app.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html')

# 개인정보 처리방침
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')


### 로그인 기능
## 로그인 필수 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'admin_id' not in session:  # 'user_id' 또는 'admin_id'가 세션에 없다면
            return redirect('/login')  # 로그인 페이지로 리디렉션
        return f(*args, **kwargs)
    return decorated_function

## 관리자 권한 필수 데코레이터
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:  # 'adminid'가 세션에 없다면
            return redirect('/login')  # 로그인 페이지로 리디렉션
        
        # 관리자 정보 확인
        admin = manager.get_admin_by_id(session['admin_id'])  # 세션의 관리자 ID로 확인
        if not admin:  # 관리자가 아니면
            return "접근 권한이 없습니다", 403  # 관리자만 접근 가능
        
        return f(*args, **kwargs)
    return decorated_function

### 로그인 정보 가져오기
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        id = request.form['userid']
        password = request.form['password']
        
        # 사용자 정보 확인
        user = manager.get_user_by_info(id)  # DB에서 사용자 정보를 가져옴
        admin = manager.get_admin_by_info(id) # DB에서 관리자 정보를 가져옴 

        if user:  # user가 None이 아닐 경우에만 진행
            if id and password:
                if user['password'] == password:  # 아이디와 비밀번호가 일치하면
                    session['user_id'] = id  # 세션에 사용자 아이디 저장
                    session['user_name'] = user['user_name']  # 세션에 이름(username) 저장
                    manager.update_last_login(id) #로그인 성공 후 마지막 로그인 갱신
                    if user['status'] == 'user' : #일반회원일경우
                        if user['security_status'] == 1 : #보안이 위험일때 경고알림
                            message = Markup('암호를 변경한지 90일 지났습니다.<br>암호를 변경하시길 권장합니다.')#Markup과 <br>태그로 flash메세지 줄나눔
                            flash(message, 'warning')
                        return redirect(url_for('user_dashboard', userid=session['user_id'])) # 회원 페이지로 이동
                    else :
                        return render_template('delete_user_dashboard.html', userid=session['user_id']) # 탈퇴한 계정
                else:
                    flash('아이디 또는 비밀번호가 일치하지 않습니다.', 'error')  # 로그인 실패 시 메시지
                    return redirect(url_for('login'))  # 로그인 폼 다시 렌더링          
                
        elif admin:
            if id and password: 
                if admin['password'] == password: #아이디와 비밀번호가 일치하면
                    session['admin_id'] = id #세션에 관리자 아이디 저장
                    session['admin_name'] = admin['admin_name'] #세션에 관리자이름 저장
                    manager.update_admin_last_login(id) # 로그인 성공 후 관리자 마지막 로그인 갱신
                    return redirect(url_for('admin_dashboard', admin = admin)) #관리자 페이지로 이동
                else: 
                    flash('아이디 또는 비밀번호가 일치하지 않습니다.', 'error')  # 로그인 실패 시 메시지
                    return redirect(url_for('login'))  # 로그인 폼 다시 렌더링 
                
        else:  # 존재하지 않는 사용자
            flash("존재하지 않는 아이디입니다.", 'error')
            return redirect(url_for('login'))  # 로그인 폼 다시 렌더링

    return render_template('login.html')  # GET 요청 시 로그인 폼 보여주기

@app.route('/need_login')
def need_login():
    flash('로그인이 필요합니다. 로그인해주세요', 'error')
    return redirect(url_for('login'))

### 회원 페이지
##로그인 후 회원페이지
@app.route('/user_dashboard')
@login_required
def user_dashboard():
    userid = session['user_id']
    user=manager.get_user_by_id(userid)
    return render_template('user_dashboard.html', user=user )

##회원 정보 수정 
@app.route('/user_dashboard/update_profile/<userid>', methods=['GET', 'POST'])
@login_required
def update_profile(userid):
    user = manager.get_user_by_info(userid)  # 회원 정보 가져오기

    if request.method == 'POST':
        print(userid)
        # 폼에서 입력한 값 받아오기
        email = request.form['email'] if request.form['email'] else user.email
        password = request.form['password'] if request.form['password'] else None
        confirm_password = request.form['confirm_password'] if request.form['confirm_password'] else None
        address = request.form['address'] if request.form['address'] else user.address
        username = request.form['username'] if request.form['username'] else user.user_name
        # 비밀번호가 입력되었으면 확인
        if password:
            if password != confirm_password:
                flash('비밀번호와 비밀번호 확인이 일치하지 않습니다.', 'error')
                return redirect(request.url)  # 현재 페이지로 리디렉션

            # 비밀번호 강도 체크 추가 (필요시)
            # 예시: 비밀번호 길이, 숫자 포함 여부 등
           
            if password == user['password'] : 
                flash('현재 비밀번호와 일치합니다.', 'warning')
                return redirect(request.url) #현재 페이지로 리디렉션
            # 비밀번호 업데이트
            else:
                flash('비밀번호를 변경하였습니다', 'success')
                manager.update_user_password(userid, password)
        # 나머지 정보 업데이트
        manager.update_user_info(userid, username, email, address)

        # 성공 메시지나 다른 페이지로 리디렉션
        flash('회원 정보가 성공적으로 수정되었습니다.', 'success')
        return redirect(url_for('user_dashboard'))  # 수정된 회원 정보를 대시보드에서 확인

    return render_template('update_profile.html', user=user)

##로그인 후 소개페이지
@app.route('/user_dashboard/about/<userid>')
@login_required
def user_dashboard_about(userid):
    user=manager.get_user_by_id(userid)
    return render_template('about.html', user=user)


##로그인 후 도로CCTV 페이지
@app.route('/user/dashboard/road/<userid>', methods=['GET'])
@login_required
def user_dashboard_road(userid):
    user = manager.get_user_by_id(userid)
    search_query = request.args.get("search_query", "").strip()
    search_type = request.args.get("search_type", "all")  # 기본값은 'all'
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # search_type이 'all'이면 search_query를 빈 문자열로 설정
    if search_type == "all":
        search_query = ""

    # SQL 쿼리 및 파라미터 가져오기
    sql, values = manager.get_road_cctv_query(search_query, search_type, per_page, offset)
    count_sql, count_values = manager.get_road_cctv_count_query(search_query, search_type)

    # 검색된 가로등 목록 가져오기
    street_lights = manager.execute_query(sql, values)
    # 전체 CCTV 개수 카운트
    total_posts = manager.execute_count_query(count_sql, count_values)

    # 페이지네이션 계산
    total_pages = (total_posts + per_page - 1) // per_page
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    return render_template(
        "user_dashboard_road.html",
        street_lights=street_lights,
        search_query=search_query,
        search_type=search_type,
        page=page,
        total_posts=total_posts,
        per_page=per_page,
        total_pages=total_pages,
        prev_page=prev_page,
        next_page=next_page,
        user=user
    )

##로그인 후 인도CCTV 페이지
@app.route('/user/dashboard/sidewalk/<userid>', methods=['GET'])
@login_required
def user_dashboard_sidewalk(userid):
    user = manager.get_user_by_id(userid)
    search_query = request.args.get("search_query", "").strip()
    search_type = request.args.get("search_type", "all")  # 기본값은 'all'
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    
    if search_type == "all":
        search_query = ""
    # SQL 쿼리 및 파라미터 가져오기
    sql, values = manager.get_sidewalk_cctv_query(search_query, search_type, per_page, offset)
    count_sql, count_values = manager.get_sidewalk_cctv_count_query(search_query, search_type)

    # 검색된 가로등 목록 가져오기
    street_lights = manager.execute_query(sql, values)

    # 전체 CCTV 개수 카운트
    total_posts = manager.execute_count_query(count_sql, count_values)

    # 페이지네이션 계산
    total_pages = (total_posts + per_page - 1) // per_page
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    return render_template(
        "user_dashboard_sidewalk.html",
        street_lights=street_lights,
        search_query=search_query,
        search_type=search_type,
        page=page,
        total_posts=total_posts,
        per_page=per_page,
        total_pages=total_pages,
        prev_page=prev_page,
        next_page=next_page,
        user = user
    )

#회원용 상세보기 라우트
@app.route('/user_dashboard/cctv/<userid>/<int:street_light_id>')
@login_required
def user_dashboard_cctv(userid,street_light_id):
    user = manager.get_user_by_info(userid)
    camera = manager.get_camera_by_info(street_light_id)
    return render_template('user_dashboard_cctv.html', user=user, camera=camera)

# 관리자용 상세보기 라우트
@app.route('/user_dashboard/cctv/<int:street_light_id>')
@admin_required
def admin_dashboard_cctv(street_light_id):
    admin = manager.get_admin_by_id(session['admin_id'])
    camera = manager.get_camera_by_info(street_light_id)
    return render_template('user_dashboard_cctv.html', user=admin, camera=camera, is_admin=True)

#회원페이지 문의하기
@app.route('/user_dashboard/inquiries/<userid>', methods=['GET','POST'])
@login_required
def user_dashboard_inquiries(userid):
    if request.method == 'GET':
        user = manager.get_user_by_id(userid)
        return render_template("user_dashboard_inquiries.html", user=user)
    
    if request.method == 'POST':
        user = manager.get_user_by_id(userid)
        userid = user['user_id']
        file = request.files['file']
        filename = file.filename if file else None
        # 파일이 있으면 저장
        if filename:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        inquiry_reason = request.form['inquiry_type']
        detail_reason = request.form.get('message')
        manager.add_inquire_user(userid, filename, inquiry_reason, detail_reason)
        flash("문의하기가 관리자에게 전달되었습니다.", 'success')
        return redirect(url_for('user_dashboard', user=user))
    
#문의된 정보 보기
@app.route('/user_dashboard/inquiries_view/<userid>', methods=['GET','POST'])
@login_required
def user_dashboard_inquiries_view(userid):
    if request.method == 'GET':
        user =manager.get_user_by_id(userid)
        posts = manager.get_posts_info()
        return render_template('user_dashboard_inquiries_view.html',user=user, posts=posts)  
    
    if request.method == 'POST':
        user = manager.get_user_by_id(userid)
        inquiries_id = request.form.get('inquiries_id')
        posts = manager.get_inquiry_by_info(inquiries_id)
        return render_template('user_dashboard_inquiry_detail.html', user=user, posts=posts)


#회원탈퇴
@app.route('/user_dashboard/delete_user/<userid>', methods=['GET','POST'])
@login_required
def user_dashboard_delete_user(userid):
    if request.method == 'GET':
        user = manager.get_user_by_id(userid)
        return render_template('user_dashboard_delete_page.html', user =user)
    
    if request.method == 'POST':
        user = manager.get_user_by_id(userid)
        reason = request.form['reason']
        detail_reason = request.form['detail_reason']
        manager.update_user_status(userid)
        manager.save_deleted_user(userid, reason, detail_reason)
        flash("회원탈퇴가 완료되었습니다.", 'success')
        return redirect(url_for('index'))
    
#탈퇴회원 로그인 후 dashboard페이지
@app.route('/delete_user_dashboard')
@login_required
def delete_user():
    return render_template('delete_user_dashboard.html')

#아이디/비밀번호찾기
@app.route('/index/search_account', methods=['GET', 'POST'])
def search_account():
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        username = request.form.get('username')
        regnumber = request.form.get('regnumber')
        userid = None  # 기본값 설정

        if search_type == "id":
            userid = manager.get_user_id_by_name_regnumber(username, regnumber)
            print(userid)
            return render_template('search_account.html', userid=userid, search_type=search_type )

        elif search_type == "password":
            userid = request.form.get('userid')
            password_data = manager.get_user_password_by_id_name_regnumber(userid, username, regnumber)
            password = None  # 기본값 설정

            if password_data: 
                raw_password = password_data['password']  # 딕셔너리에서 비밀번호 값 가져오기
                password = raw_password[:4] + '*' * (len(raw_password) - 4)  # 앞 4자리만 표시, 나머지는 '*'
            return render_template('search_account.html', password = password, userid=userid, search_type=search_type)
    return render_template('search_account.html')

#계정찾기 이후 새비밀번호 업데이트
@app.route('/index/search_account/edit_password/<userid>', methods=['GET','POST'])
def edit_password(userid):
    user = manager.get_user_by_info(userid)
    if request.method == 'POST': 
        password = request.form['new_password']
        success = manager.update_user_password(userid, password)
        return jsonify({"success": success})
    return render_template('edit_password.html', user = user)
    

## 로그아웃 라우트
@app.route('/logout')
def logout():
    # session.pop('user', None)  # 세션에서 사용자 정보 제거
    # session.pop('role', None)  # 세션에서 역할 정보 제거
    session.clear()
    return redirect('/')  # 로그아웃 후 로그인 페이지로 리디렉션



### 관리자 페이지
@app.route('/admin_dashboard')
@admin_required  # 관리자만 접근 가능
def admin_dashboard():
    adminid = session['admin_id']
    admin = manager.get_admin_by_id(adminid)
    return render_template('admin_dashboard.html', admin=admin)  # 관리자 대시보드 렌더링

@app.route("/lamp_check/<userid>")
def lamp_check(userid):
    return render_template("lamp_check.html")

@app.route("/load_car/<userid>")
def load_car(userid):
    return render_template("load_car.html", stream_url=road_url)

# YOLO 분석된 영상 스트리밍
@app.route("/processed_video_feed")
def processed_video_feed():
    """YOLOv8로 감지된 영상 스트리밍"""
    def generate():
        while True:
            with license_plate.lock:
                if license_plate.frame is None:
                    continue
                img = license_plate.frame.copy()

            results = license_plate.model(img)
            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            _, jpeg = cv2.imencode('.jpg', img)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# OCR 결과 API
@app.route("/ocr_result", methods=["GET"])
def get_ocr_result():
    """OCR 결과 반환 API"""
    response_data = {"license_plate": license_plate.ocr_result, "alert_message": license_plate.alert_message}

    if license_plate.alert_message:  # 알람 메시지가 있을 때만 초기화
        license_plate.alert_message = ""  # 메시지를 한 번만 표시하도록 초기화
    
    return jsonify(response_data)

@app.route("/sidewalk_motorcycle/<userid>")
def sidewalk_motorcycle(userid):
    return render_template("sidewalk_motorcycle.html")


# ✅ ESP32-CAM에서 감지된 오토바이 영상 제공
@app.route("/video_feed")
def video_feed():
    """ESP32-CAM 스트리밍"""
    return Response(motorcycle.get_video_frame(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ✅ 오토바이 감지 상태 API
@app.route("/alert_status", methods=["GET"])
def alert_status():
    """오토바이 감지 상태 반환"""
    return jsonify(motorcycle.get_alert_status())


## 기능소개 페이지


##관리자 페이지에서 문의정보 보기
##문의된 정보 보기
@app.route('/admin/admin_management_posts')
@admin_required
def admin_management_posts():
    return render_template("admin_management_posts.html")


##회원 문의 정보 보기
@app.route('/admin/admin_list_posts_member')
@admin_required
def admin_list_posts_member():
    posts = manager.get_enquired_posts_member()
    number = len(posts)
    return render_template("admin_list_posts_member.html", posts=posts, number=number)


## 답변상태 변환하기 
@app.route('/update_status_member/<userid>', methods=['POST'])
@admin_required
def update_answer_status(userid):
    enquired_at_str = request.form['enquired_at']
    enquired_at = datetime.strptime(enquired_at_str, '%Y-%m-%d %H:%M:%S')
    manager.update_answer_status(userid,enquired_at)
    if userid != '비회원':
        return redirect(url_for('admin_list_posts_member'))
    else :
        return redirect(url_for('admin_list_posts_nonmember'))

#회원 문의사항 상세정보보기
@app.route('/admin/admin_view_posts_member/<userid>', methods=['POST'])
@admin_required
def admin_view_posts_member(userid):
    enquired_at_str = request.form['enquired_at']
    enquired_at = datetime.strptime(enquired_at_str, '%Y-%m-%d %H:%M:%S')
    post = manager.get_enquired_post_by_id(userid,enquired_at)
    return render_template("admin_view_posts_member.html", post=post)

#이미지파일 가져오기
@app.route('/capture_file/<filename>')
def capture_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=True)

