import sqlite3

# Kết nối đến cơ sở dữ liệu (tự động tạo file game.db nếu chưa tồn tại)
conn = sqlite3.connect('game.db')

# Tạo con trỏ để thực hiện các lệnh SQL
c = conn.cursor()

# Tạo bảng leaderboard nếu chưa tồn tại
c.execute('''
    CREATE TABLE IF NOT EXISTS leaderboard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- ID tự động tăng
        name TEXT NOT NULL,  -- Tên người chơi
        score INTEGER NOT NULL,  -- Điểm số
        rating INTEGER NOT NULL  -- Đánh giá (1-5)
    )
''')

# Xác nhận thay đổi và lưu vào cơ sở dữ liệu
conn.commit()

# Đóng kết nối sau khi hoàn thành
conn.close()

print("Cơ sở dữ liệu game.db và bảng leaderboard đã được tạo thành công!")
