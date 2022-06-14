import sqlite3
import os
from flask import Flask, render_template, request, g, flash, abort, redirect, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import argparse
import io
import ffmpeg
import os
from PIL import Image
from matplotlib import pyplot as plt
import numpy
import numpy as np
import torch
from flask import Flask, render_template, request, redirect, Response, g, flash, abort, redirect, url_for, make_response
import cv2
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from imutils.video import VideoStream
import threading
import argparse
from datetime import datetime
import time
from flask import session
import flask_paginate
from flask_sqlalchemy import SQLAlchemy, Pagination
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from UserLogin import UserLogin
from werkzeug.security import generate_password_hash, check_password_hash
from FDataBase import FDataBase
import sqlite3

# конфигурация
DATABASE = '/tmp/data/flsite.db'
DEBUG = True
SECRET_KEY = 'fdgfh78@#5?>gfhf89dx,v06k'
MAX_CONTENT_LENGTH = 100024 * 100024

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(f'{app.root_path}/data', 'flsite.db')))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/flsite.db'
app.config['SQLACLHEMY_TRACK_MODIFICATIONS'] = False
db1 = SQLAlchemy(app)

model = torch.hub.load(
    "ultralytics/yolov5", "yolov5s", pretrained=True, force_reload=True, autoshape=True
)
model.eval()


login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "success"


class Video_Name(db1.Model):
    id = db1.Column(db1.Integer, primary_key=True)
    file_name = db1.Column(db1.String(300), nullable=False)
    date = db1.Column(db1.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Video_Name %r>' % self.id

class Photo_Name(db1.Model):
    id = db1.Column(db1.Integer, primary_key=True)
    file_name = db1.Column(db1.String(300), nullable=False)
    date = db1.Column(db1.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Photo_Name %r>' % self.id

class Posts(db1.Model):
    id = db1.Column(db1.Integer, primary_key=True)
    title = db1.Column(db1.Text, nullable=False)
    text = db1.Column(db1.Text, nullable=False)
    url = db1.Column(db1.Text, nullable=False)
    time = db1.Column(db1.Integer, nullable=False)

    def __repr__(self):
        return '<Posts %r>' % self.id

class Users(db1.Model):
    id = db1.Column(db1.Integer, primary_key=True)
    name = db1.Column(db1.Text, nullable=False)
    email = db1.Column(db1.Text, nullable=False)
    is_admin = db1.Column(db1.Boolean, default=0)

    def __repr__(self):
        return '<Users %r>' % self.id


@app.route("/photo", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        try:
            file = request.files["file"]
            img_bytes = file.read()
            photo_name = Photo_Name(file_name=file.filename)
            db1.session.add(photo_name)
            db1.session.commit()
            img = Image.open(io.BytesIO(img_bytes))
            results = model(img, size=640)
            results.render()
            for img in results.imgs:
                img_base64 = Image.fromarray(img)
                img_base64.save(f"static/data/photos/1{file.filename}", format="JPEG")
            return render_template("photo1.html", filename1=f'static/data/photos/1{file.filename}')
        except:
            return render_template('error.html')
    else:
        return render_template("photo.html")


@app.route("/video", methods=["GET", "POST"])
def video():
    if request.method == "POST":
        try:
            file = request.files["file"]
            file.save(f'static/data/videos/{secure_filename(file.filename)}')
            video_name = Video_Name(file_name=file.filename)
            db1.session.add(video_name)
            db1.session.commit()
            cap = cv2.VideoCapture(f'static/data/videos/{file.filename}')
            fourcc = cv2.VideoWriter_fourcc(*'h264')
            out = cv2.VideoWriter((f'static/data/videos/1{file.filename}'), fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))
            duration = 15
            while True:
                start_time = datetime.now()
                diff = (datetime.now() - start_time).seconds
                while (diff <= duration):
                    ret, frame = cap.read()
                    results = model(frame)
                    out.write(np.squeeze(results.render()))
                    diff = (datetime.now() - start_time).seconds
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                cap.release()
                break
            return redirect('video_feed')
        except:
            return render_template('error.html')
    else:
        return render_template('video.html')


@app.route("/video_feed", methods=["GET", "POST"])
def video_feed():
    video_name = (Video_Name.query.all())
    video_name_count = Video_Name.query.count()
    video_n = video_name[video_name_count - 1].file_name
    return render_template('video1.html', filename=f'static/data/videos/1{video_n}')


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    """Вспомогательная функция для создания таблиц БД"""
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def get_db():
    '''Соединение с БД, если оно еще не установлено'''
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


dbase = None


@app.before_request
def before_request():
    """Установление соединения с БД перед выполнением запроса"""
    global dbase
    db = get_db()
    dbase = FDataBase(db)


@app.teardown_appcontext
def close_db(error):
    '''Закрываем соединение с БД, если оно было установлено'''
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.route("/", methods=["POST", "GET"])
def addRequest():
    if request.method == "POST":
        res = dbase.addRequest(request.form['email'])
        if not res:
            flash('Ошибка добавления заявки', category='error')
        else:
            flash('Заявка добавлена успешно', category='success')
    return render_template('index.html')


@app.route("/post")
def posts():
    return render_template('posts.html', menu=dbase.getMenu(), posts=dbase.getPostsAnonce())


@app.route("/add_post", methods=["POST", "GET"])
def addPost():
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['post']) > 10:
            res = dbase.addPost(request.form['name'], request.form['post'], request.form['url'])
            if not res:
                flash('Ошибка добавления статьи', category='error')
            else:
                flash('Статья добавлена успешно', category='success')
        else:
            flash('Ошибка добавления статьи', category='error')

    return render_template('add_post.html', menu=dbase.getMenu(), title="Добавление статьи")


@app.route("/admin", methods=["POST", "GET"])
@login_required
def admin():
    this_user = current_user.getAdmin()
    if this_user == 1:
        return render_template('admin.html', menu=dbase.getMenu(), title="Удаление статьи")
    else:
        return render_template('error.html')


@app.route("/delete_post", methods=["POST", "GET"])
@login_required
def deletePost():
    this_user = current_user.getAdmin()
    if this_user == 1:
        if request.method == "POST":
            res = dbase.deletePost(request.form['url'])
            if not res:
                flash('Ошибка удаления статьи', category='error')
            else:
                flash('Статья удалена успешно', category='success')

        return render_template('delete_post.html', menu=dbase.getMenu(), title="Добавление статьи")
    else:
        return render_template('error.html')


@app.route("/edit_post", methods=["POST", "GET"])
@login_required
def editPost():
    this_user = current_user.getAdmin()
    if this_user == 1:
        if request.method == "POST":
            res = dbase.editPost(request.form['title'], request.form['post'], request.form['url'], request.form['this_url'])
            if not res:
                flash('Ошибка редактирования статьи', category='error')
            else:
                flash('Статья отредактирована успешно', category='success')

        return render_template('edit_post.html', menu=dbase.getMenu(), title="Редактирование статьи")
    else:
        return render_template('error.html')


@app.route("/edit_user", methods=["POST", "GET"])
@login_required
def editUser():
    this_user = current_user.getAdmin()
    if this_user == 1:
        if request.method == "POST":
            res = dbase.editUser(request.form['name'], request.form['email_select'], request.form['is_admin'])
            if not res:
                flash('Ошибка редактирования пользователя', category='error')
            else:
                flash('Пользователь отредактирован успешно', category='success')

        return render_template('edit_user.html', menu=dbase.getMenu(), title="Редактирование пользователя")
    else:
        return render_template('error.html')


@app.route("/settings", methods=["POST", "GET"])
@login_required
def editfromUser():
    if request.method == "POST":
        res = dbase.editfromUser(request.form['name'], request.form['email'], email_select=current_user.getEmail())
        if not res:
            flash('Ошибка редактирования', category='error')
        else:
            flash('Отредактировано успешно', category='success')
    return render_template('settings.html', menu=dbase.getMenu(), title="Редактирование")


@app.route("/delete_user", methods=["POST", "GET"])
@login_required
def deleteUser():
    this_user = current_user.getAdmin()
    if this_user == 1:
        if request.method == "POST":
            res = dbase.deleteUser(request.form['email'])
            if not res:
                flash('Ошибка удаления пользователя', category='error')
            else:
                flash('Пользователь удаленен успешно', category='success')

        return render_template('delete_user.html', menu=dbase.getMenu(), title="Удаление пользователя")
    else:
        return render_template('error.html')


@app.route("/post/<alias>")
@login_required
def showPost(alias):
    title, post = dbase.getPost(alias)
    if not title:
        abort(404)

    return render_template('post.html', menu=dbase.getMenu(), title=title, post=post)


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == "POST":
        user = dbase.getUserByEmail(request.form['email'])
        if user and check_password_hash(user['psw'], request.form['psw']):
            userlogin = UserLogin().create(user)
            rm = True if request.form.get('remainme') else False
            login_user(userlogin, remember=rm)
            return redirect(request.args.get("next") or url_for("profile"))

        flash("Неверная пара логин/пароль", "error")

    return render_template("login.html", menu=dbase.getMenu(), title="Авторизация")


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['email']) > 4 \
                and len(request.form['psw']) > 4 and request.form['psw'] == request.form['psw2']:
            hash = generate_password_hash(request.form['psw'])
            res = dbase.addUser(request.form['name'], request.form['email'], hash)
            if res:
                flash("Вы успешно зарегистрированы", "success")
                return redirect(url_for('login'))
            else:
                flash("Ошибка при добавлении в БД", "error")
        else:
            flash("Неверно заполнены поля", "error")

    return render_template("register.html", menu=dbase.getMenu(), title="Регистрация")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "success")
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", menu=dbase.getMenu(), title="Профиль")


@app.route('/userava')
@login_required
def userava():
    img = current_user.getAvatar(app)
    if not img:
        return ""

    h = make_response(img)
    h.headers['Content-Type'] = 'image/png'
    return h


@app.route('/upload', methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()
                res = dbase.updateUserAvatar(img, current_user.get_id())
                if not res:
                    flash("Ошибка обновления аватара", "error")
                flash("Аватар обновлен", "success")
            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "error")
        else:
            flash("Ошибка обновления аватара", "error")

    return redirect(url_for('profile'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port, debug=True)
