#_*_ coding: utf-8 _*_

from flask import Flask, render_template, url_for, request, session, redirect, flash
import sqlite3
# 파싱
from bs4 import BeautifulSoup
import requests
# 파일 입력
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory

UPLOAD_FOLDER = 'static\\img\\profile_picture'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024     # 16 MB
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

#메인페이지
@app.route('/', methods=['GET', 'POST'])
def index():
	return url_login('index.html')

#선수페이지
@app.route('/player/<int:idx>', methods=['GET', 'POST'])
def player(idx):
	#[0] : number
	#[1] : name
	#[2] : position
	#[3] : country
	#[4] : birth
	#[5] : height
	#[6] : weight

	#Pos = request.form['index']
	#players = int(selectPlayer(Pos));
	titles = ["-", "감독/코치", "골키퍼", "수비수", "미드필더", "공격수"]
	positions = ["-", "staff", "gk", "df", "mf", "fw"]

	con = sqlite3.connect('tottenham')
	params = (positions[idx],)
	cur = con.cursor()
	cur.execute('''
		SELECT * FROM player WHERE position=?;
		''', params)
	row = cur.fetchall()
	con.commit()
	con.close()

	return url_login('player.html', titles[idx], row)

# 경기일정 페이지
@app.route('/schedule/<int:idx>', methods=['GET', 'POST'])
def schedule(idx, season=2018):
    leagueName = ["-", "프리미어리그", "챔피언스리그", "FA컵", "기타"]

    return url_login('schedule.html', leagueName[idx], None, None, idx, season)


# 경기일정 리스트(ajax활용)
@app.route('/schedule_list/')
def schedule_list():
    # 조회할 페이지 번호를 가져옴 get query string
    idx = request.args.get('idx')
    idx = int(idx)
    season = request.args.get('season')
    season = int(season)
    competition = ["-", "1573", "1753", "1755", "6442452699"]
    r = requests.get("http://www.tottenhamhotspur.com/matches/?venue=All&competition={}&season={}%2F{}".format(competition[idx], season, season+1))
    html = r.text
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.select('tbody tr td')

    return render_template('schedule_list.html', tables=tables)

# 사진게시판
@app.route('/photo', methods=['GET', 'POST'])
def photo():
	
	# table : photo, p_id, p_src, p_alt, p_tag
	con=sqlite3.connect('tottenham')
	cur=con.cursor()
	cur.execute('''
		SELECT p_src, p_alt, p_tag FROM photo;
		''')
	photos=cur.fetchall()
	con.commit()
	con.close()

	return url_login('photo.html', None, None, photos)

#-----------------------------------------------------------------
# 로그인 로그아웃 부분
#로그아웃 수행
def logout():
    session.pop('u_num', None)
    session.pop('u_name', None)
    session.pop('rank', None)

#로그인 여부
def isLogin():
    return 'u_num' in session

# 로그인 부분
def url_login(url, title=None, players=None, photos=None, idx=None, season=None):
    u_name = None
    login_error = None

    if isLogin(): #'u_number' in session:   # 로그인 되어 있다면
        return render_template(url, u_name = session['u_name'], login_error=login_error, title=title, players=players, photos=photos, idx=idx, season=season)
    else:                               # 로그인 되어 있지 않다면
        if request.method == 'POST':    # 회원 등록 정보가 넘어오는 경우
            lu_id = request.form['lu_id']
            lpassword = request.form['lpassword']
            params = (lu_id, lpassword)
            app.logger.debug('index() - %s' % str(params))

            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                SELECT u_num, u_name, rank FROM tbuser WHERE u_id=? AND password=? AND use_flag='y';
                ''', params)
            rows=cur.fetchall()
            con.commit()
            con.close()
            app.logger.debug('index() - %s' % str(rows))
            if len(rows) == 1:  # 로그인 정상
                # 세션을 생성하고 다시 리다이렉션
                session['u_num'] = rows[0][0]
                session['u_name'] = rows[0][1]
                session['rank'] = rows[0][2]
                return redirect(url_for('index'))
            else:               # 로그인 오류
                login_error='로그인에 실패하였습니다.'
                return render_template(url, u_name=u_name, login_error=login_error, title=title, players=players, photos=photos, idx=idx, season=season)
        else:                           # 기본 접속 (미 로그인 & GET)
            return render_template(url, u_name=u_name, login_error=login_error, title=title, players=players, photos=photos, idx=idx, season=season)

#-----------------------------------------------------------------

# 회원 기능 - 회원_등록 
@app.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':
        # 입력받은 email, u_name, password, gender, birth_year 를 데이터베이스에 저장한다. 오류 처리는 생략 한다. 
        u_id = request.form['u_id']
        password = request.form['password']
        u_name = request.form['u_name']
        birth= request.form['birth']
        tel = request.form['tel']
        email = request.form['email']
        gender = request.form['gender']
        job = request.form['job']
        address = request.form['address']

        filename = "anonymous.png"
        if 'file' not in request.files:
            app.logger.debug('No file part')
        else:
            file = request.files['p_pic']

            if file.filename == '':
                app.logger.debug('No selected file')
            else:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    send_from_directory(app.config['UPLOAD_FOLDER'], filename)
                    
        params = (u_id, password, u_name, birth, tel, email, gender, job, address, filename)
        app.logger.debug('user_signup() - %s' % str(params))
        
        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
            INSERT INTO tbuser (u_id, password, u_name, birth, tel, email, gender, job, address, p_pic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            ''', params)
        con.commit()
        con.close()
        return redirect(url_for('index'))
    return render_template('user_signup.html', nologin=True)

# 회원 기능 - 로그아웃
@app.route('/user/logout')
def user_logout():
    logout()
    return redirect(url_for('index'))

# 회원 기능 - 프로필사진 체크
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	
# 회원 기능 - 회원_정보보기
@app.route('/user/')
def user_profile():
    user_info = None
    u_num = None

    board_id = request.args.get('board_id')
    app.logger.debug('user() - %s' % str(board_id))
    if board_id != None:
        params = (board_id,)
        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
            SELECT u_num FROM tbboard WHERE b_id=?;
            ''', params)
        rows=cur.fetchall()
        con.close()
        u_num = rows[0][0]


    if isLogin(): #'u_num' in session:   # 로그인 되어 있다면
        if u_num == None:
            u_num = session['u_num']
        params = (u_num,)
        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
            SELECT u_id, password, u_name, birth, tel, email, gender, job, address, add_dt, upd_dt, p_pic FROM tbuser WHERE u_num=?;
            ''', params)
        rows=cur.fetchall()
        app.logger.debug('index() - %s' % str(rows))
        con.close()
        user_info = rows[0]
        if len(rows) == 1:  # 로그인 정상
            return render_template('user_profile.html', user_info=user_info, u_name = session['u_name'])
        else:
            return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯

# 회원 기능 - 회원_수정
@app.route('/user/update', methods=['GET', 'POST'])
def user_update():
    user_info=None
    u_num=session['u_num']
    if isLogin(): #'u_num' in session:   # 로그인 되어 있다면
        if request.method != 'POST':            # 회원 정보를 제공함
            u_num = session['u_num']
            params = (u_num,)
            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                SELECT u_id, password, u_name, birth, tel, email, gender, job, address, add_dt, upd_dt, p_pic FROM tbuser WHERE u_num=?;
                ''', params)
            rows=cur.fetchall()
            app.logger.debug('user_update() - rows: %s' % str(rows))
            con.close()
            user_info = rows[0]
            if len(rows) == 1:  # 로그인 정상
                return render_template('user_update.html', user_info=user_info, u_name = session['u_name'])
            else:
                return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
        else:                           # 회원 정보를 업데이트 함 (POST)
            # 입력받은 email, u_name, password, gender, birth_year 를 데이터베이스에 저장한다. 오류 처리는 생략 한다. 
            password = request.form['password']
            birth= request.form['birth']
            tel = request.form['tel']
            email = request.form['email']
            gender = request.form['gender']
            job = request.form['job']
            address = request.form['address']

            filename = request.form['before_pic']
            if 'p_pic' not in request.files:
                app.logger.debug('No file part')
            else:
                file = request.files['p_pic']

                if file.filename == '':
                    app.logger.debug('No selected file')
                else:
                    if file and allowed_file(file.filename):
                        # sercure_filename 함수가 ASCII로만 문자열을 반환해서 한글로된 파일이름을 사용이 불가능해서 삭제하였음
                        filename = file.filename
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        send_from_directory(app.config['UPLOAD_FOLDER'], filename)
            
            params = (password, birth, tel, email, gender, job, address, filename, u_num)
            app.logger.debug('user_update() - params: %s' % str(params))

            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                UPDATE tbuser SET password=?, birth=?, tel=?, email=?, gender=?, job=?, address=?, upd_dt=DATETIME('now', 'localtime'), p_pic=? WHERE u_num=?
                ''', params)
            con.commit()
            con.close()
            return redirect(url_for('user_profile'))
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯

# 회원 기능 - 회원_탈퇴
@app.route('/user/leave')
def user_leave():
    if isLogin(): #'u_num' in session:   # 로그인 되어 있다면
        u_num = session['u_num']
        params = (u_num,)
        app.logger.debug('user_leave() - params: %s' % str(params))
        
        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
            UPDATE tbuser SET use_flag='n', upd_dt=DATETIME('now', 'localtime') WHERE u_num=?
            ''', params)
        con.commit()
        con.close()
        logout()        # 로그아웃
        return redirect(url_for('index'))
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯

#---------------------------------------------------------------------------------------------------
# 게시판 기능 - 추천
@app.route('/recommend/<int:board_id>')
def recommend(board_id):
    params = (board_id,)
    con=sqlite3.connect('tottenham')
    cur=con.cursor()
    cur.execute('''
        UPDATE tbboard SET b_recommend=b_recommend+1 WHERE b_id=?;
        ''', params)
    con.commit()
    con.close()
    return render_template('recommend.html')

# 게시판 기능 - 게시판
@app.route('/board/', methods=['GET', 'POST'])
def board():
    u_name = None
    login_error = None
    pageNum = None
    pageNumList = None  
    dbNum = None  
    
    pageNum = request.args.get('page')  # http://127.0.0.1:5000/board/?page=1
    if pageNum is None: 
        pageNum = '1'
    pageNum = int(pageNum)
    if pageNum < 1:
        pageNum = 1
    app.logger.debug('board() - pageNum: %d' % pageNum)

    keyword = None
    keyword = request.args.get('keyword')
    app.logger.debug('board() - keyword: %s' % keyword)

    con=sqlite3.connect('tottenham')
    cur=con.cursor()
    if keyword==None:
        cur.execute('''
            SELECT b_id FROM tbboard b WHERE b.use_flag='y';
            ''')
    else:
        params = (keyword, keyword)
        cur.execute('''
            SELECT b_id FROM tbboard b WHERE b.use_flag='y' AND (b.title like '%'||?||'%' OR b.content like '%'||?||'%');
            ''', params)
    rows=cur.fetchall()
    # app.logger.debug('index() - %s' % str(rows))
    con.close()

    dbNum = int(len(rows)/10)+1
    if pageNum > dbNum:
        pageNum = dbNum
    
    startNum, endNum = 0, 0
    if pageNum >= 6:
        startNum = int((pageNum-1)/5)*5 + 1
    else:
        startNum = 1
    endNum = dbNum
    pageNumList = list(range(startNum, endNum+1))
    app.logger.debug('board() - pageNumList: %s' % str(pageNumList))

    if isLogin(): #'u_id' in session:   # 로그인 되어 있다면
        u_name=session['u_name']
        return render_template('board.html', u_name=u_name, login_error=login_error, pageNum=pageNum, pageNumList=pageNumList, keyword=keyword, dbNum=dbNum)
    else:                               # 로그인 되어 있지 않다면
        if request.method == 'POST':    # 회원 등록 정보가 넘어오는 경우
            lu_id = request.form['lu_id']
            lpassword = request.form['lpassword']
            params = (lu_id, lpassword)
            app.logger.debug('board() - %s' % str(params))

            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                SELECT u_num, u_name, rank FROM tbuser WHERE u_id=? AND password=? AND use_flag='y';
                ''', params)
            rows=cur.fetchall()
            con.close()
            app.logger.debug('board() - %s' % str(rows))
            if len(rows) == 1:  # 로그인 정상
                # 세션을 생성하고 다시 리다이렉션
                session['u_num'] = rows[0][0]
                session['u_name'] = rows[0][1]
                session['rank'] = rows[0][2]
                return redirect(url_for('board'))
            else:               # 로그인 오류
                login_error='로그인에 실패하였습니다.'
                return render_template('board.html', u_name=u_name, login_error=login_error, pageNum=pageNum, pageNumList=pageNumList, keyword=keyword, dbNum=dbNum)
        else:                           # 기본 접속 (미 로그인 & GET)
            return render_template('board.html', u_name=u_name, login_error=login_error, pageNum=pageNum, pageNumList=pageNumList, keyword=keyword, dbNum=dbNum)

# 게시판 기능 - 게시판_글목록
@app.route('/board_list/')
def board_list():
    # 조회할 페이지 번호를 가져옴 get query string
    pageNum = request.args.get('page')  # http://127.0.0.1:5000/board/?page=1
    if pageNum is None:
        pageNum = '1'
    pageNum = int(pageNum)
    if pageNum < 1:
        pageNum = 1
    app.logger.debug('board_list() - pageNum: %d' % pageNum)

    keyword = None
    keyword = request.args.get('keyword')   # 검색 키워드를 가져옴
    app.logger.debug('board_list() - keyword: %s' % keyword)

    # DB로 부터 tbboard 게시판 목록을 가져옴
    offset = (pageNum - 1) * 10
    
    con=sqlite3.connect('tottenham')
    cur=con.cursor()
    if keyword==None:
        params = (offset,)
        cur.execute('''
            SELECT b_id, u_name, title, b.add_dt, b_count, b_recommend
            FROM tbboard b INNER JOIN tbuser u
            ON b.u_num = u.u_num
            WHERE b.use_flag='y' ORDER BY b_id DESC LIMIT 10 OFFSET ?;
            ''', params)
    else:
        params = (keyword, keyword, offset)
        cur.execute('''
            SELECT b_id, u_name, title, b.add_dt, b_count, b_recommend
            FROM tbboard b INNER JOIN tbuser u
            ON b.u_num = u.u_num
            WHERE b.use_flag='y' AND (b.title like '%'||?||'%' OR b.content like '%'||?||'%') ORDER BY b_id DESC LIMIT 10 OFFSET ?;
            ''', params)
    rows=cur.fetchall()
    # app.logger.debug('index() - %s' % str(rows))
    con.close()

    return render_template('board_list.html', board_rows=rows)

# 게시판 기능 - 게시판_글등록
@app.route('/board/post', methods=["GET", "POST"])
def board_post():
    if isLogin(): #'u_num' in session:   # 로그인 되어 있다면
        if request.method == 'POST':            
            # 입력받은 title, content 를 데이터베이스에 저장한다. 오류 처리는 생략 한다. 
            u_num = session['u_num']
            title = request.form['title']
            b_password = request.form['b_password']
            content = request.form['content']
            params = (u_num, title, b_password, content)
            app.logger.debug('board_post() - %s' % str(params))
            
            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                INSERT INTO tbboard (u_num, title, b_password, content) 
                VALUES (?, ?, ?, ?);
                ''', params)
            con.commit()
            con.close()            
            return redirect(url_for('board'))
        else:
            u_name=session['u_name']
            return render_template('board_post.html', u_name=u_name)
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯

# 게시판 기능 - 게시판_글수정
@app.route('/board/<int:board_id>/update', methods=["GET", "POST"])
def board_update(board_id):
    if isLogin(): #'u_id' in session:   # 로그인 되어 있다면
        if request.method == 'GET':            # 회원 정보를 제공함 (GET)
            u_num = session['u_num']
            rank = session['rank']
            params = (board_id,)
            app.logger.debug('board_update() - %s' % str(params))
            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
            SELECT b_id, b.u_num, u_name, title, b_password, content, b.add_dt, b.upd_dt
            FROM tbboard b INNER JOIN tbuser u
            ON b.u_num = u.u_num
            WHERE b.use_flag='y' AND b_id=?;
                ''', params)
            rows=cur.fetchall()
            app.logger.debug('board_update() - %s' % str(rows))
            con.close()
            board_view = rows[0]
            if len(rows) == 1:  # 로그인 정상
                u_name=session['u_name']
                if u_num==board_view[1] or rank == 2: # 현재 세션의 유저와 가져온 게시글의 유저가 같은 경우
                    return render_template('board_update.html', board_view=board_view, u_num=u_num, u_name=u_name, rank=rank)
                else:
                    return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
            else:
                return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
        else:                           # 회원 정보를 업데이트 함 (POST)
            # 입력받은 b_id, title, content 를 데이터베이스에 저장한다. 오류 처리는 생략 한다. 
            rank = session['rank']
            u_num = session['u_num']
            b_id = int(request.form['b_id'])
            title = request.form['title']
            b_password = request.form['b_password']            
            content = request.form['content']
            params = (title, b_password, content, b_id, u_num, rank)
            app.logger.debug('board_update() - params: %s' % str(params))

            if b_id!=board_id:  # URL의 게시글 번호와 POST로 넘겨 받은 게시글의 번호가 불일치 하는 경우
                return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
            
            con=sqlite3.connect('tottenham')
            cur=con.cursor()
            cur.execute('''
                UPDATE tbboard SET title=?, b_password=?, content=?, upd_dt=DATETIME('now', 'localtime') WHERE b_id=? AND (u_num=? or ?=2);
                ''', params)
            con.commit()
            con.close()
            return redirect(url_for('board_view', board_id=board_id, rank=rank))
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯

# 게시판 기능 - 게시판_글삭제
@app.route('/board/<int:board_id>/delete')
def board_delete(board_id):
    if isLogin(): #'u_id' in session:   # 로그인 되어 있다면
        u_num = session['u_num']
        rank = session['rank']
        params = (board_id, u_num, rank)
        app.logger.debug('board_delete() - params: %s' % str(params))
        
        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
            UPDATE tbboard SET use_flag='n', upd_dt=DATETIME('now', 'localtime') WHERE b_id=? AND (u_num=? or ?=2);
            ''', params)
        con.commit()
        con.close()
        return redirect(url_for('board'))
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯


# 게시판 기능 - 게시판_글보기
@app.route('/board/<int:board_id>')
def board_view(board_id):
    if isLogin(): #'u_id' in session:   # 로그인 되어 있다면
        u_num = session['u_num']
        params = (board_id,)
        app.logger.debug('board_view() - %s' % str(params))

        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
        UPDATE tbboard SET b_count=b_count+1 WHERE b_id=?;
            ''', params)
        con.commit()
        con.close()

        con=sqlite3.connect('tottenham')
        cur=con.cursor()
        cur.execute('''
        SELECT b_id, b.u_num, u_name, title, content, b.add_dt, b.upd_dt, b_count, b_recommend
        FROM tbboard b INNER JOIN tbuser u
        ON b.u_num = u.u_num
        WHERE b.use_flag='y' AND b_id=?;
            ''', params)
        rows=cur.fetchall()
        app.logger.debug('board_view() - %s' % str(rows))
        con.close()
        board_view = rows[0]
        if len(rows) == 1:  # 로그인 정상
            u_name=session['u_name']
            return render_template('board_view.html', board_view=board_view, u_num=u_num, u_name=u_name, rank=session['rank'])
        else:
            return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯
    else:                               # 로그인 되어 있지 않다면
        return render_template('user_notlogin.html')   # 잘못된 페이지 접근이라고 보여주고 이동해도 될듯


if __name__ == '__main__':
	app.run(debug=True)