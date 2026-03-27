from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import csv
import os
import io
import qrcode
from io import BytesIO
from datetime import datetime
from config import Config
from models import db, User, Material, InventoryLog, CompetitionRecord, ChatMessage

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

with app.app_context():
    db.create_all()


def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            flash('需要管理员权限', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        if User.query.filter_by(student_id=student_id).first():
            flash('学号已存在', 'danger')
            return redirect(url_for('register'))
        user = User(
            student_id=student_id,
            name=request.form['name'],
            major=request.form['major'],
            grade=request.form['grade'],
            class_name=request.form['class_name'],
            phone=request.form['phone']
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash('注册成功！请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = request.form['password']
        user = User.query.filter_by(student_id=student_id).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['student_id'] = user.student_id
            session['name'] = user.name
            session['is_admin'] = user.is_admin
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        flash('学号或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/upgrade', methods=['POST'])
@login_required
def upgrade():
    code = request.form['invite_code']
    if code == 'yqj13378151525':
        user = User.query.get(session['user_id'])
        user.is_admin = True
        db.session.commit()
        session['is_admin'] = True
        flash('🎉 恭喜！您已成为管理员', 'success')
    else:
        flash('邀请码错误', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    total_materials = Material.query.count()
    total_logs = InventoryLog.query.count()
    return render_template('dashboard.html', total_materials=total_materials, total_logs=total_logs)


@app.route('/inventory')
@login_required
def inventory():
    materials = Material.query.all()
    return render_template('inventory.html', materials=materials)


@app.route('/claim/<int:material_id>', methods=['POST'])
@login_required
def claim(material_id):
    material = Material.query.get_or_404(material_id)
    amount = int(request.form['amount'])
    purpose = request.form['purpose']
    if material.stock < amount:
        flash('库存不足！', 'danger')
        return redirect(url_for('inventory'))
    material.stock -= amount
    log = InventoryLog(user_id=session['user_id'], material_id=material_id, amount=amount, purpose=purpose)
    db.session.add(log)
    db.session.commit()
    flash(f'领取成功！已扣减 {amount} 件', 'success')
    return redirect(url_for('inventory'))


# --- 核心更新：无视表格前几行废话，智能锁定表头的 CSV 引擎 ---
@app.route('/import_csv', methods=['POST'])
@login_required
@admin_required
def import_csv():
    if 'csv_file' not in request.files:
        flash('请选择文件', 'danger')
        return redirect(url_for('inventory'))

    file = request.files['csv_file']
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('inventory'))

    if file and file.filename.endswith('.csv'):
        try:
            file_content = file.read()
            try:
                text = file_content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = file_content.decode('gbk')

            lines = text.splitlines()
            reader = csv.reader(lines)
            parsed_rows = list(reader)

            header_row = None
            header_index = -1

            # 1. 扫描每一行，直到发现包含“耗材名称”的那一行作为真正的表头
            for i, row in enumerate(parsed_rows):
                clean_row = [str(item).replace(' ', '').strip() for item in row]
                if '耗材名称' in clean_row or '物品名称' in clean_row or '名称' in clean_row:
                    header_row = clean_row
                    header_index = i
                    break

            if not header_row:
                flash('导入失败：没找到名为“耗材名称”的列！请确保表格里有这一列。', 'danger')
                return redirect(url_for('inventory'))

            # 2. 锁定“耗材名称”和“数量”到底在第几列
            name_idx, category_idx, stock_idx = -1, -1, -1
            for i, col_name in enumerate(header_row):
                if col_name in ['耗材名称', '物品名称', '名称', 'name']:
                    name_idx = i
                elif col_name in ['耗材服务活动名称', '分类', '类别', 'category']:
                    category_idx = i
                elif col_name in ['数量', '库存', 'stock']:
                    stock_idx = i

            count = 0
            # 3. 从表头的下一行开始，精准读取物料数据
            for i in range(header_index + 1, len(parsed_rows)):
                row = parsed_rows[i]
                if not row or len(row) <= name_idx:
                    continue

                name = str(row[name_idx]).strip()
                if not name:  # 忽略没有名字的空行
                    continue

                category = str(row[category_idx]).strip() if category_idx != -1 and len(row) > category_idx else '未分类'
                quantity_str = str(row[stock_idx]).strip() if stock_idx != -1 and len(row) > stock_idx else '0'

                # 如果填了未知或空，设定为黄牌状态 (-1)
                if quantity_str in ['未知', '', '无']:
                    stock = -1
                else:
                    try:
                        # 用 float 包裹以防止读取到 '10.0' 这样的格式报错
                        stock = int(float(quantity_str))
                    except ValueError:
                        stock = -1

                material = Material(name=name, category=category, stock=stock)
                db.session.add(material)
                count += 1

            db.session.commit()
            flash(f'✅ 成功跳过学校大标题，智能读取了 {count} 条物料！', 'success')

        except Exception as e:
            flash(f'解析出错: {str(e)}', 'danger')

    return redirect(url_for('inventory'))


@app.route('/api/generate_qr/<int:material_id>')
def generate_qr(material_id):
    target_url = url_for('inventory', _external=True) + f"#mat-{material_id}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00d4aa", back_color="#121212")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/logs')
@login_required
def logs():
    all_logs = InventoryLog.query.order_by(InventoryLog.timestamp.desc()).all()
    return render_template('logs.html', logs=all_logs)


@app.route('/members')
@login_required
@admin_required
def members():
    users = User.query.all()
    return render_template('members.html', users=users)


@app.route('/competitions', methods=['GET', 'POST'])
@login_required
def competitions():
    if request.method == 'POST':
        record = CompetitionRecord(
            user_id=session['user_id'],
            competition_name=request.form['competition_name'],
            award=request.form['award'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        )
        if 'certificate' in request.files:
            cert = request.files['certificate']
            if cert.filename:
                filename = secure_filename(cert.filename)
                cert_path = os.path.join(UPLOAD_FOLDER, filename)
                cert.save(cert_path)
                record.certificate_path = f'uploads/{filename}'
        if 'materials' in request.files:
            mat = request.files['materials']
            if mat.filename:
                filename = secure_filename(mat.filename)
                mat_path = os.path.join(UPLOAD_FOLDER, filename)
                mat.save(mat_path)
                record.materials_path = f'uploads/{filename}'
        db.session.add(record)
        db.session.commit()
        flash('竞赛记录上传成功！', 'success')
    records = CompetitionRecord.query.order_by(CompetitionRecord.timestamp.desc()).all()
    return render_template('competitions.html', records=records)


@app.route('/chat')
@login_required
def chat():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    return render_template('chat.html', messages=messages)


@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    msg = request.form.get('message', '').strip()
    if msg:
        chat_msg = ChatMessage(user_id=session['user_id'], message=msg)
        db.session.add(chat_msg)
        db.session.commit()
    return jsonify(success=True)


@app.route('/get_messages')
@login_required
def get_messages():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    data = [{
        'name': User.query.get(m.user_id).name,
        'is_admin': User.query.get(m.user_id).is_admin,
        'message': m.message,
        'time': m.timestamp.strftime('%H:%M')
    } for m in messages]
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)