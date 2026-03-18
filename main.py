import os
import time
import json
import logging
from dotenv import load_dotenv
import telebot
from keep_alive import keep_alive
from scraper import get_latest_post, get_all_joined_groups

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FB_COOKIE = os.getenv("FACEBOOK_COOKIE")

# Lấy khoảng thời gian delay giữa các lần kiểm tra nhóm, giúp tránh checkpoint/bị khóa mõm
DELAY_BETWEEN_GROUPS = int(os.getenv("DELAY_BETWEEN_GROUPS", 10))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", 300))

if not all([TOKEN, CHAT_ID, FB_COOKIE]):
    logging.error("Thiếu biến môi trường quan trọng: TELEGRAM_TOKEN, CHAT_ID, FACEBOOK_COOKIE.")
    exit(1)

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "last_post.json"

def get_last_processed_ids():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_last_processed_ids(data_dict):
    with open(DATA_FILE, 'w') as f:
        json.dump(data_dict, f)

def send_to_telegram(post_data, group_id):
    msg = f"🔔 <b>BÀI VIẾT MỚI TỪ NHÓM {group_id}</b>\n\n"
    msg += f"👤 <b>Người đăng:</b> <a href='{post_data['author_url']}'>{post_data['author_name']}</a>\n"
    
    if post_data['content']:
        safe_content = post_data['content'].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        msg += f"📝 <b>Nội dung:</b>\n{safe_content}\n\n"
        
    msg += f"🔗 <b>Link bài:</b> <a href='{post_data['post_url']}'>Xem ngay</a>"
    
    try:
        bot.send_message(CHAT_ID, msg, parse_mode='HTML', disable_web_page_preview=True)
        logging.info(f"Đã gửi thông báo cho bài viết: {post_data['post_id']} của group {group_id}")
    except Exception as e:
        logging.error(f"Lỗi gửi tin nhắn Telegram: {e}")

def main_loop():
    logging.info("Khởi động tiến trình quét danh sách tất cả Facebook Group...")
    while True:
        try:
            # 1. Lấy danh sách tất cả các nhóm đã tham gia
            group_ids = get_all_joined_groups(FB_COOKIE)
            if not group_ids:
                logging.warning("Không tìm thấy danh sách nhóm nào. Cookie có thể bị lỗi, hãy kiểm tra lại!")
                time.sleep(60)
                continue
                
            logging.info(f"Đã lấy được {len(group_ids)} nhóm đã tham gia. Bắt đầu quét...")
            
            # Đọc csdl cũ
            processed_data = get_last_processed_ids()
            
            for index, group_id in enumerate(group_ids):
                logging.info(f"[{index+1}/{len(group_ids)}] Đang kiểm tra nhóm {group_id}...")
                post_data = get_latest_post(group_id, FB_COOKIE)
                
                if post_data:
                    last_id = processed_data.get(group_id)
                    if post_data['post_id'] != last_id:
                        logging.info(f"Phát hiện bài mới ở nhóm {group_id}: {post_data['post_id']}")
                        send_to_telegram(post_data, group_id)
                        # Cập nhật và lưu lại ngay lập tức
                        processed_data[group_id] = post_data['post_id']
                        save_last_processed_ids(processed_data)
                    else:
                        pass # Đã xử lý rồi, không cần in
                else:
                    logging.info(f"Nhóm {group_id} không lấy được bài viết mới (hoặc không có quyền truy cập).")
                
                # Sleep một chút giữa các nhóm để FB không khoá (Rate Limit)
                time.sleep(DELAY_BETWEEN_GROUPS)
                
            logging.info(f"Hoàn thành quét {len(group_ids)} nhóm. Nghỉ {SCAN_INTERVAL} giây trước vòng tiếp theo...")
        except Exception as e:
            logging.error(f"Lỗi vòng lặp chính: {e}")
            
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    # Bật web server cho UptimeRobot
    keep_alive()
    # Chạy vòng lặp quét bài
    main_loop()
