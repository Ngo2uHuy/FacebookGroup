import requests
from bs4 import BeautifulSoup
import re

def get_latest_post(group_id, cookies_str):
    url = f"https://mbasic.facebook.com/groups/{group_id}?sorting_setting=CHRONOLOGICAL"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Cookie': cookies_str,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'upgrade-insecure-requests': '1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Nếu bị checkpoint hoặc cookie hết hạn, URL sẽ bị redirect
        if "login.php" in response.url or "checkpoint" in response.url:
            print("Cookie hết hạn hoặc tài khoản bị Checkpoint.")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm các link bài viết (permalink)
        # Regex tìm link có chứa /groups/ID/permalink/
        permalink_elements = soup.find_all('a', href=re.compile(rf'/groups/{group_id}/permalink/'))
        
        if not permalink_elements:
            return None
            
        for post_link_el in permalink_elements:
            href = post_link_el['href']
            match = re.search(r'/permalink/(\d+)/?', href)
            if not match: continue
            
            post_id = match.group(1)
            full_post_url = f"https://www.facebook.com/groups/{group_id}/permalink/{post_id}/"
            
            # Tìm container thẻ chứa toàn bộ bài viết (thường cách vài thẻ div/table lên trên)
            container = post_link_el.find_parent('table')
            if not container:
                container = post_link_el.find_parent('div', recursive=False)
            if not container:
                container = post_link_el.parent.parent.parent
                
            content_text = ""
            author_name = "Người dùng Facebook"
            author_url = ""
            
            if container:
                # Tìm thẻ author: thường là thẻ <a> trỏ về profile nhưng không chứa các nút giao diện
                links = container.find_all('a')
                for a in links:
                    test_href = a.get('href', '')
                    if 'profile.php' in test_href or ('/' in test_href and 'group' not in test_href and 'permalink' not in test_href and 'mbasic' not in test_href):
                        # Lọc các nút chức năng
                        lbl = a.get_text(strip=True)
                        if lbl and lbl not in ['Thích', 'Bình luận', 'Chia sẻ', 'Lưu', 'Báo cáo', 'Xem thêm']:
                            author_name = lbl
                            # Build link author gốc
                            author_url = "https://www.facebook.com" + test_href.replace('mbasic.facebook.com', '')
                            break
                
                # Trích xuất nội dung text
                for script_or_style in container(["script", "style"]):
                    script_or_style.decompose()
                    
                # Lấy text và lọc các phần thừa
                text_content = container.get_text(separator=' \n ', strip=True)
                lines = text_content.split('\n')
                
                ui_words = ['Thích', 'Bình luận', 'Chia sẻ', 'Bày tỏ cảm xúc', 'Lưu bài viết', 'Xem bản dịch', 'Bài viết gốc', author_name, '·']
                filtered_lines = []
                for l in lines:
                    val = l.strip()
                    if not val: continue
                    # Bỏ qua dòng nút bấm hoặc thời gian biểu
                    if val in ui_words: continue
                    if re.search(r'\d+\s*(phút|giờ|ngày)\s*trước', val): continue
                    filtered_lines.append(val)
                    
                content_text = '\n'.join(filtered_lines).strip()
                
            return {
                'post_id': post_id,
                'content': content_text[:3500], # Giới hạn ký tự Telegram
                'author_name': author_name,
                'author_url': author_url,
                'post_url': full_post_url
            }
            
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu: {e}")
        return None
        
    return None
