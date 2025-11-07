
from flask import Flask, render_template, request, redirect, url_for, session
from models import db, Question, Choice
from datetime import datetime, timedelta

import os

env_path = os.path.join(os.path.dirname(__file__), '.env')
print("Looking for .env at:", env_path)

with open(env_path, 'r', encoding='utf-8') as f:
    print("Raw .env contents:")
    print(f.read())
from dotenv import load_dotenv

# 明示的に .env を読み込む
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

print("DATABASE_URL from env:", os.getenv("DATABASE_URL"))

from urllib.parse import unquote

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # セッション管理用の秘密鍵
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

app.config['SQLALCHEMY_DATABASE_URI']=os.getenv("DATABASE_URL")

  # ← Supabaseの接続情報を環境変数から取得
print("DATABASE_URL:", os.environ.get('DATABASE_URL'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # ← 警告を防ぐための推奨設定

app.config['UPLOAD_FOLDER'] = 'static/images'
db.init_app(app)

ADMIN_PASSWORD = "takafumi_secret_2025"

# 以下、ルート定義はそのままでOK（データ保存先がSupabaseになるだけ）

@app.route('/')
def index():
    three_days_ago = datetime.now() - timedelta(days=14)
    questions = Question.query.filter(
        Question.approved == True,
        Question.created_at >= three_days_ago
    ).order_by(Question.created_at.desc()).all()
    return render_template('index.html', questions=questions)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        text = request.form['text']
        author = request.form['author']
        choices = request.form.getlist('choices')
        image = request.files.get('image')

        image_path = None
        if image and image.filename:
            image_path = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_path))

        question = Question(text=text, author=author, image_path=image_path)
        for choice_text in choices:
            if choice_text.strip():
                question.choices.append(Choice(text=choice_text.strip()))
        db.session.add(question)
        db.session.commit()

        return redirect(url_for('thank_you'))

    return render_template('submit.html')

@app.route('/vote/<int:question_id>', methods=['GET', 'POST'])
def vote(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        choice_id = int(request.form['choice'])
        choice = Choice.query.get(choice_id)
        if choice:
            choice.votes += 1
            db.session.commit()
        return redirect(url_for('result', question_id=question_id))
    return render_template('vote.html', question=question)

@app.route('/result/<int:question_id>')
def result(question_id):
    question = Question.query.get_or_404(question_id)
    return render_template('result.html', question=question)

@app.route('/edit/<int:question_id>', methods=['GET', 'POST'])
def edit(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        question.text = request.form['text']
        question.approved = True
        question.category = request.form.get('category', '').strip()

        image = request.files.get('image')
        if image and image.filename:
            image_path = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_path))
            question.image_path = image_path

        for choice in question.choices:
            field_name = f'choice_{choice.id}'
            if field_name in request.form:
                choice.text = request.form[field_name]

        db.session.commit()
        return redirect(url_for('admin'))  # ✅ 編集後はadminページに戻す
    return render_template('edit.html', question=question)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'logged_in' in session and session['logged_in']:
        unapproved = Question.query.filter_by(approved=False).all()
        approved = Question.query.filter_by(approved=True).all()
        return render_template('admin.html', unapproved=unapproved, approved=approved)
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin'))
        else:
            return "パスワードが違います", 403
    return render_template('admin_login.html')

@app.route('/search')
def search():
    keyword = request.args.get('q', '')
    results = []
    if keyword:
        results = Question.query.filter(Question.text.contains(keyword), Question.approved == True).all()
    return render_template('search.html', keyword=keyword, results=results)

@app.route('/author/<author_name>')
def author_page(author_name):
    questions = Question.query.filter_by(author=author_name, approved=True).all()
    return render_template('author.html', author=author_name, questions=questions)

@app.route('/delete/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)

    for choice in question.choices:
        db.session.delete(choice)

    if question.image_path:
        image_file = os.path.join(app.config['UPLOAD_FOLDER'], question.image_path)
        if os.path.exists(image_file):
            os.remove(image_file)

    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('admin'))  # ✅ 削除後もadminページに戻す

@app.route('/category/<category_name>')
def category_page(category_name):
    decoded_category = unquote(category_name)
    questions = Question.query.filter_by(category=decoded_category).order_by(Question.id.desc()).all()
    return render_template('category.html', category=decoded_category, questions=questions)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/operator')
def operator():
    return render_template('operator.html')

@app.route("/index")
def index_page():
    return render_template("index.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

# ✅ Supabaseにテーブルを作成するための初期化（初回のみ）
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)