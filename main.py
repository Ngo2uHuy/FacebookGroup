import os
import time
import json
import logging
from dotenv import load_dotenv
import telebot
from keep_alive import keep_alive
from scraper import get_latest_post

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROUP_ID = os.getenv("GROUP_ID")
FB_COOKIE = os.getenv("FACEBOOK_COOKIE")

if not all([TOKEN, CHAT_ID, GROUP_ID, FB_COOKIE]):
    logging.error("Thiếu biến môi trường. Vui lòng kiểm tra file .env hoặc cấu hình Render.")
    exit(1)

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "last_post.json"

def get_last_processed_id():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                return data.get('last_post_id')
            except:
                return None
    return None

def save_last_processed_id(post_id):
    with open(DATA_FILE, 'w') as f:
        json.dump({'last_post_id': post_id}, f)

def escape_markdown_v2(text):
    if not text:
        return ""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)

def send_to_telegram(post_data):
    # Sử dụng HTML parse mode hoặc Markdown. HTML thường dễ hơn và ít lỗi escape
    msg = f"🔔 <b>BÀI VIẾT MỚI TỪ NHÓM</b>\n\n"
    msg += f"👤 <b>Người đăng:</b> <a href='{post_data['author_url']}'>{post_data['author_name']}</a>\n"
    
    if post_data['content']:
        # Escape các thẻ HTML có thể lẫn trong nội dung
        safe_content = post_data['content'].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        msg += f"📝 <b>Nội dung:</b>\n{safe_content}\n\n"
        
    msg += f"🔗 <b>Link bài viết:</b> <a href='{post_data['post_url']}'>Nhấn vào đây để xem</a>"
    
    try:
        bot.send_message(CHAT_ID, msg, parse_mode='HTML', disable_web_page_preview=True)
        logging.info(f"Đã gửi thông báo cho bài viết: {post_data['post_id']}")
    except Exception as e:
        logging.error(f"Lỗi gửi tin nhắn Telegram: {e}")

def main_loop():
    logging.info("Khởi động tiến trình quét Facebook...")
    while True:
        try:
            logging.info("Đang kiểm tra bài viết mới...")
            post_data = get_latest_post(GROUP_ID, FB_COOKIE)
            if post_data:
                last_id = get_last_processed_id()
                if post_data['post_id'] != last_id:
                    logging.info(f"Phát hiện bài mới: {post_data['post_id']}")
                    send_to_telegram(post_data)
                    save_last_processed_id(post_data['post_id'])
                else:
                    logging.info("Không có bài mới (Bài viết đã được gửi trước đó).")
            else:
                logging.info("Không lấy được dữ liệu, hoặc không có bài viết nào.")
        except Exception as e:
            logging.error(f"Lỗi vòng lặp chính: {e}")
            
        time.sleep(300) # Quét 5 phút 1 lần = 300 giây

if __name__ == "__main__":
    # Bật web server cho UptimeRobot
    keep_alive()
    # Chạy vòng lặp quét bài
    main_loop()
