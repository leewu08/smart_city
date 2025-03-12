from flask import Flask, session, url_for, render_template, flash, send_from_directory, jsonify ,request, redirect
import os
import requests
from datetime import datetime, timedelta
from functools import wraps
from models import DBManager
from markupsafe import Markup
import json
import re
## sy branch
app = Flask(__name__)



app.secret_key = 'your-secret-key'  # 비밀 키 설정, 실제 애플리케이션에서는 더 안전한 방법으로 설정해야 함if __name__ == '__main__':

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
        if 'user_id' not in session:  # 'userid'가 세션에 없다면
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
        user = manager.get_user_by_id(id)  # DB에서 사용자 정보를 가져옴
        admin = manager.get_admin_by_id(id) # DB에서 관리자 정보를 가져옴 

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
                    return redirect(url_for('admin_dashboard')) #관리자 페이지로 이동
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
    user = manager.get_user_by_id(userid)  # 회원 정보 가져오기

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
                manager.update_password(userid, password)
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
    search_query = request.args.get("search_query", "")
    search_type = request.args.get("search_type", "all")  # 기본값은 'all'
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    db_manager = DBManager()

    # SQL 쿼리 및 파라미터 가져오기
    sql, values = db_manager.get_road_cctv_query(search_query, search_type, per_page, offset)
    count_sql, count_values = db_manager.get_road_cctv_count_query(search_query, search_type)

    # 검색된 가로등 목록 가져오기
    street_lights = db_manager.execute_query(sql, values)

    # 전체 CCTV 개수 카운트
    total_posts = db_manager.execute_count_query(count_sql, count_values)

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
    search_query = request.args.get("search_query", "")
    search_type = request.args.get("search_type", "all")  # 기본값은 'all'
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    db_manager = DBManager()

    # SQL 쿼리 및 파라미터 가져오기
    sql, values = db_manager.get_sidewalk_cctv_query(search_query, search_type, per_page, offset)
    count_sql, count_values = db_manager.get_sidewalk_cctv_count_query(search_query, search_type)

    # 검색된 가로등 목록 가져오기
    street_lights = db_manager.execute_query(sql, values)

    # 전체 CCTV 개수 카운트
    total_posts = db_manager.execute_count_query(count_sql, count_values)

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

##회원페이지 문의하기
#회원페이지에서 문의하기
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
        user = manager.get_user_by_id(userid)
        posts = manager.get_posts_info()
        return render_template('user_dashboard_inquiries_view.html', user=user, posts=posts)  
    
    if request.method == 'POST':
        user = manager.get_user_by_id(userid)
        inquiries_id = request.form.get('inquiries_id')
        posts = manager.get_inquiry_by_id(inquiries_id)
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
        reason_detail = request.form['reason_detail']
        manager.insert_deleted_user_table(userid)
        flash("회원탈퇴가 완료되었습니다.", 'success')
        return redirect(url_for('index'))
    
#탈퇴회원 로그인 후 dashboard페이지
@app.route('/delete_user_dashboard')
def delete_user():
    return render_template('delete_user_dashboard.html')

@app.route('/edit_password')
def edit_password():
    return render_template('edit_password.html')

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
    adminid = session['adminid']
    admin = manager.get_admin_by_id(adminid)
    return render_template('admin_dashboard.html', admin=admin)  # 관리자 대시보드 렌더링



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






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=True)

