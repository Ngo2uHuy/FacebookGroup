import requests
from bs4 import BeautifulSoup
import re

def get_all_joined_groups(cookies_str):
    url = "https://mbasic.facebook.com/groups/?seemore"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Cookie': cookies_str,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'upgrade-insecure-requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if "login.php" in response.url or "checkpoint" in response.url:
            print("Cookie hết hạn hoặc bị Checkpoint khi lấy danh sách nhóm.")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm tất cả link trỏ về các nhóm facebook
        group_links = soup.find_all('a', href=re.compile(r'/groups/(\d+)'))
        
        group_ids = []
        for link in group_links:
            href = link['href']
            match = re.search(r'/groups/(\d+)', href)
            if match:
                gid = match.group(1)
                if gid not in group_ids:
                    group_ids.append(gid)
                    
        return group_ids
    except Exception as e:
        print(f"Lỗi khi lấy danh sách nhóm: {e}")
        return []

def get_latest_post(group_id, cookies_str):
    url = f"https://mbasic.facebook.com/groups/{group_id}?sorting_setting=CHRONOLOGICAL"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Cookie': cookies_str,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'upgrade-insecure-requests': '1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if "login.php" in response.url or "checkpoint" in response.url:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        permalink_elements = soup.find_all('a', href=re.compile(rf'/groups/{group_id}/permalink/'))
        
        if not permalink_elements:
            return None
            
        for post_link_el in permalink_elements:
            href = post_link_el['href']
            match = re.search(r'/permalink/(\d+)/?', href)
            if not match: continue
            
            post_id = match.group(1)
            full_post_url = f"https://www.facebook.com/groups/{group_id}/permalink/{post_id}/"
            
            container = post_link_el.find_parent('table')
            if not container:
                container = post_link_el.find_parent('div', recursive=False)
            if not container:
                container = post_link_el.parent.parent.parent
                
            content_text = ""
            author_name = "Người dùng Facebook"
            author_url = ""
            
            if container:
                links = container.find_all('a')
                for a in links:
                    test_href = a.get('href', '')
                    if 'profile.php' in test_href or ('/' in test_href and 'group' not in test_href and 'permalink' not in test_href and 'mbasic' not in test_href):
                        lbl = a.get_text(strip=True)
                        if lbl and lbl not in ['Thích', 'Bình luận', 'Chia sẻ', 'Lưu', 'Báo cáo', 'Xem thêm']:
                            author_name = lbl
                            author_url = "https://www.facebook.com" + test_href.replace('mbasic.facebook.com', '')
                            break
                
                for script_or_style in container(["script", "style"]):
                    script_or_style.decompose()
                    
                text_content = container.get_text(separator=' \n ', strip=True)
                lines = text_content.split('\n')
                
                ui_words = ['Thích', 'Bình luận', 'Chia sẻ', 'Bày tỏ cảm xúc', 'Lưu bài viết', 'Xem bản dịch', 'Bài viết gốc', author_name, '·']
                filtered_lines = []
                for l in lines:
                    val = l.strip()
                    if not val: continue
                    if val in ui_words: continue
                    if re.search(r'\d+\s*(phút|giờ|ngày)\s*trước', val): continue
                    filtered_lines.append(val)
                    
                content_text = '\n'.join(filtered_lines).strip()
                
            return {
                'post_id': post_id,
                'content': content_text[:3500],
                'author_name': author_name,
                'author_url': author_url,
                'post_url': full_post_url
            }
            
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu group {group_id}: {e}")
        return None
        
    return None
