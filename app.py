import os
import random
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from functools import wraps

from flask import (
    Flask, abort, flash, redirect, render_template, request,
    session, url_for
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "local-development-key-change-before-deploying"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
)
csrf = CSRFProtect(app)


def get_db_connection():
    """Open a connection to the SQLite database configured for this deployment."""
    db_path = os.getenv("DATABASE_PATH", "game.db")
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create application tables on startup; keep the original leaderboard table compatible."""
    with closing(get_db_connection()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_name TEXT NOT NULL,
                score INTEGER NOT NULL CHECK (score >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                score INTEGER NOT NULL,
                rating INTEGER NOT NULL DEFAULT 5
            );

            CREATE INDEX IF NOT EXISTS idx_game_scores_user_date
                ON game_scores(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_game_scores_score
                ON game_scores(score DESC);
            """
        )
        conn.commit()


init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user_id"):
            flash("Đăng nhập để sử dụng tính năng này nhé.", "info")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with closing(get_db_connection()) as conn:
        return conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def save_score(user_id, game_name, score):
    with closing(get_db_connection()) as conn:
        conn.execute(
            "INSERT INTO game_scores (user_id, game_name, score) VALUES (?, ?, ?)",
            (user_id, game_name, max(0, int(score))),
        )
        conn.commit()


@app.route("/")
def home():
    with closing(get_db_connection()) as conn:
        game_count = conn.execute("SELECT COUNT(*) FROM game_scores").fetchone()[0]
        player_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        top_players = conn.execute(
            """
            SELECT u.username, MAX(s.score) AS best_score
            FROM game_scores s JOIN users u ON u.id = s.user_id
            GROUP BY u.id, u.username
            ORDER BY best_score DESC LIMIT 3
            """
        ).fetchall()
    return render_template(
        "index.html",
        game_count=game_count,
        player_count=player_count,
        top_players=top_players,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
            flash("Tên tài khoản cần dài 3–20 ký tự, chỉ gồm chữ, số hoặc dấu gạch dưới.", "error")
        elif len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            flash("Vui lòng nhập địa chỉ email hợp lệ.", "error")
        elif len(password) < 8:
            flash("Mật khẩu cần có ít nhất 8 ký tự.", "error")
        elif password != confirm_password:
            flash("Mật khẩu xác nhận chưa khớp.", "error")
        else:
            try:
                with closing(get_db_connection()) as conn:
                    conn.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                        (username, email, generate_password_hash(password)),
                    )
                    conn.commit()
                flash("Tạo tài khoản thành công. Đăng nhập để bắt đầu chơi!", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Tên tài khoản hoặc email đã được sử dụng.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        with closing(get_db_connection()) as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE",
                (identity, identity),
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            flash(f"Chào mừng trở lại, {user['username']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Thông tin đăng nhập chưa chính xác.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with closing(get_db_connection()) as conn:
        stats = conn.execute(
            """
            SELECT COUNT(*) AS games_played, COALESCE(MAX(score), 0) AS best_score,
                   COALESCE(SUM(score), 0) AS total_score
            FROM game_scores WHERE user_id = ?
            """,
            (user["id"],),
        ).fetchone()
        recent_scores = conn.execute(
            """
            SELECT game_name, score, created_at FROM game_scores
            WHERE user_id = ? ORDER BY id DESC LIMIT 8
            """,
            (user["id"],),
        ).fetchall()
    return render_template("dashboard.html", user=user, stats=stats, recent_scores=recent_scores)


@app.route("/leaderboard")
def leaderboard():
    with closing(get_db_connection()) as conn:
        scores = conn.execute(
            """
            SELECT u.username AS name, s.game_name, s.score, s.created_at
            FROM game_scores s JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC, s.created_at ASC LIMIT 50
            """
        ).fetchall()
        legacy_scores = conn.execute(
            """
            SELECT name, 'Trò chơi cũ' AS game_name, score,
                   CURRENT_TIMESTAMP AS created_at
            FROM leaderboard
            ORDER BY score DESC LIMIT 20
            """
        ).fetchall()
    combined_scores = sorted(
        list(scores) + list(legacy_scores),
        key=lambda row: int(row["score"]),
        reverse=True,
    )[:50]
    return render_template("leaderboard.html", scores=combined_scores)


@app.route("/guess_game", methods=["GET", "POST"])
@login_required
def guess_game():
    if request.method == "POST":
        action = request.form.get("action", "guess")
        if action == "restart":
            session["guess_secret"] = random.randint(1, 100)
            session["guess_attempts"] = 0
            session["guess_completed"] = False
            return redirect(url_for("guess_game"))

        if session.get("guess_completed"):
            flash("Ván này đã kết thúc. Hãy bắt đầu ván mới nhé.", "info")
            return redirect(url_for("guess_game"))

        raw_guess = request.form.get("guess", "")
        try:
            guess = int(raw_guess)
        except (TypeError, ValueError):
            flash("Nhập một số nguyên từ 1 đến 100.", "error")
            return redirect(url_for("guess_game"))

        if not 1 <= guess <= 100:
            flash("Số đoán phải nằm trong khoảng 1–100.", "error")
            return redirect(url_for("guess_game"))

        secret = session.setdefault("guess_secret", random.randint(1, 100))
        attempts = int(session.get("guess_attempts", 0)) + 1
        session["guess_attempts"] = attempts

        if guess == secret:
            score = max(10, 110 - attempts * 10)
            session["guess_completed"] = True
            save_score(session["user_id"], "Đoán số", score)
            flash(f"Chính xác! Bạn tìm ra số sau {attempts} lượt và nhận {score} điểm.", "success")
        elif guess < secret:
            flash("Chưa đúng — số bí mật lớn hơn số bạn vừa nhập.", "info")
        else:
            flash("Chưa đúng — số bí mật nhỏ hơn số bạn vừa nhập.", "info")
        return redirect(url_for("guess_game"))

    if "guess_secret" not in session:
        session["guess_secret"] = random.randint(1, 100)
        session["guess_attempts"] = 0
        session["guess_completed"] = False
    return render_template(
        "guess_game.html",
        attempts=session.get("guess_attempts", 0),
        completed=session.get("guess_completed", False),
    )


@app.route("/golf_game", methods=["GET", "POST"])
@login_required
def golf_game():
    if request.method == "POST":
        action = request.form.get("action", "hit")
        if action == "restart" or "golf_round" not in session or session["golf_round"].get("completed"):
            session["golf_round"] = {"shots": [], "total": 0, "completed": False}
            if action == "restart":
                return redirect(url_for("golf_game"))

        round_data = session["golf_round"]
        if len(round_data["shots"]) < 5:
            yards = random.randint(50, 300)
            round_data["shots"].append(yards)
            round_data["total"] += yards
            if len(round_data["shots"]) == 5:
                round_data["completed"] = True
                save_score(session["user_id"], "Golf mini", round_data["total"])
                flash(f"Hoàn thành 5 cú đánh! Bạn đạt {round_data['total']} điểm.", "success")
            else:
                flash(f"Cú đánh {len(round_data['shots'])}: {yards} yards.", "info")
            session["golf_round"] = round_data
        return redirect(url_for("golf_game"))

    if "golf_round" not in session:
        session["golf_round"] = {"shots": [], "total": 0, "completed": False}
    return render_template("golf_game.html", round_data=session["golf_round"])


@app.route("/feedback", methods=["POST"])
def feedback():
    message = request.form.get("message", "").strip()
    if not message:
        flash("Vui lòng nhập góp ý trước khi gửi.", "error")
    elif len(message) > 1000:
        flash("Góp ý tối đa 1.000 ký tự.", "error")
    else:
        user_id = session.get("user_id")
        with closing(get_db_connection()) as conn:
            conn.execute(
                "INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                (user_id, message),
            )
            conn.commit()
        flash("Cảm ơn bạn đã gửi góp ý!", "success")
    return redirect(request.referrer or url_for("home"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Trang bạn tìm không tồn tại."), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, message="Đã có lỗi xảy ra. Vui lòng thử lại sau."), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
