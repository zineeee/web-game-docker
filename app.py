from flask import Flask, request, render_template, redirect, url_for
import random
import sqlite3

app = Flask(__name__)

# Hàm kết nối đến cơ sở dữ liệu SQLite
def get_db_connection():
    conn = sqlite3.connect('game.db')  # Kết nối tới file game.db
    conn.row_factory = sqlite3.Row  # Kết quả trả về ở dạng từ điển
    return conn

# Trang chủ, hiển thị giao diện game
@app.route('/')
def home():
    return render_template('index.html')

# Route để thêm điểm vào cơ sở dữ liệu
@app.route('/add_score', methods=['POST'])
def add_score():
    name = request.form['name']
    score = request.form['score']
    rating = request.form['rating']
    conn = get_db_connection()
    conn.execute('INSERT INTO leaderboard (name, score, rating) VALUES (?, ?, ?)', (name, score, rating))
    conn.commit()
    conn.close()
    return redirect(url_for('confirmation', name=name, score=score, rating=rating))

# Trang xác nhận sau khi thêm điểm thành công
@app.route('/confirmation')
def confirmation():
    name = request.args.get('name')
    score = request.args.get('score')
    rating = request.args.get('rating')
    return render_template('confirmation.html', name=name, score=score, rating=rating)

# Hiển thị bảng xếp hạng
@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    scores = conn.execute('SELECT * FROM leaderboard ORDER BY score DESC').fetchall()
    conn.close()
    return render_template('leaderboard.html', scores=scores)

# Gửi góp ý từ người dùng (nếu có tính năng này)
@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_text = request.form['feedback']
    # Bạn có thể lưu góp ý vào cơ sở dữ liệu hoặc xử lý khác
    return "Thank you for your feedback!"

@app.route('/golf_game', methods=['GET', 'POST'])
def golf_game():
    if request.method == 'POST':
        hit = random.randint(1, 300)  # Số lần đánh từ 1 đến 300 yards
        result = f"Bạn đã đánh được {hit} yards!"
        return render_template('golf_game.html', result=result)
    return render_template('golf_game.html')

# Route cho game đoán số
@app.route('/guess_game', methods=['GET', 'POST'])
def guess_number():
    if request.method == 'POST':
        guess = int(request.form['guess'])
        secret_number = random.randint(1, 100)
        if guess < secret_number:
            result = "Số bạn đoán nhỏ hơn!"
        elif guess > secret_number:
            result = "Số bạn đoán lớn hơn!"
        else:
            result = "Chúc mừng! Bạn đã đoán đúng!"
        return render_template('guess_game.html', result=result)
    return render_template('guess_game.html')


# Khởi động ứng dụng
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
