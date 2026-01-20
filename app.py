import os
import json
import requests
import urllib.parse
from datetime import datetime

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'):
        return
        
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now()
    today_num = today.strftime('%Y%m%d')

    for title_key, info in history.items():
        pure_title = title_key.replace(" 講談社", "").replace("　", " ").split()[0]
        author_name = info.get('author', '')
        publisher_config = info.get('publisher', '')
        
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "format": "json",
            "title": pure_title,
            "author": author_name,
            "sort": "-releaseDate",
            "booksGenreId": "001001",
            "hits": 15
        }
        if publisher_config:
            params["publisherName"] = publisher_config
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            if not data.get('Items') or data.get('count') == 0:
                params["title"] = pure_title[:5]
                res = requests.get(url, params=params, timeout=10)
                data = res.json()

            if data.get('Items'):
                items_list = [entry['Item'] for entry in data['Items']]
                
                legit_items = []
                special_items = []
                exclude_words = ['ポストカード', 'ガイド', 'キャラブック', '画集', 'カレンダー', 'ノベル', 'アニメ']
                priority_exclude = ['特装版', '限定版', '付録', 'セット']

                for item in items_list:
                    item_title = item.get('title', '')
                    if any(w in item_title for w in exclude_words): continue
                    target_a = author_name.replace(' ', '').replace('　', '')
                    item_a = item.get('author', '').replace(' ', '').replace('　', '')
                    if target_a not in item_a: continue
                    
                    if any(w in item_title for w in priority_exclude):
                        special_items.append(item)
                    else:
                        legit_items.append(item)

                found_item = legit_items[0] if legit_items else (special_items[0] if special_items else None)
                if not found_item: continue

                new_isbn = str(found_item.get('isbn'))
                raw_date = found_item.get('salesDate', '')
                current_publisher = found_item.get('publisherName', '')
                sales_date_num = "".join(filter(str.isdigit, raw_date))
                
                # --- 通知・リマインドロジック ---
                stored_isbn = str(info.get('isbn', '0'))
                should_notify = False
                notify_type = ""

                # 発売日までの日数を計算
                days_left = None
                if len(sales_date_num) == 8:
                    try:
                        target_dt = datetime.strptime(sales_date_num, '%Y%m%d')
                        days_left = (target_dt - today).days + 1 # 当日を1日目とする
                    except:
                        pass

                # 条件A: 新しいISBNが見つかった（初回・新刊） かつ 未来の日付
                if new_isbn != stored_isbn and (not sales_date_num or sales_date_num > today_num):
                    should_notify = True
                    notify_type = "【新刊予約開始】"

                # 条件B: すでに知っているISBNだが、特定の「〇日前」になった（リマインド）
                elif days_left is not None:
                    if days_left in [14, 7]:
                        should_notify = True
                        notify_type = f"【発売{days_left}日前リマインド】"

                # 条件C: 発売日が不明な場合（取りこぼし防止）
                elif not sales_date_num:
                    should_notify = True
                    notify_type = "【発売日不明・確認推奨】"

                if should_notify:
                    history[title_key].update({
                        'isbn': new_isbn,
                        'salesDate': raw_date,
                        'last_notified': sales_date_num if sales_date_num else today_num,
                        'publisher': current_publisher
                    })
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"{notify_type}\n『{found_item['title']}』\n著者：{found_item['author']}\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ {notify_type}: {found_item['title']}")

                elif new_isbn != stored_isbn:
                    # 既刊(過去)のデータ更新のみ
                    history[title_key].update({
                        'isbn': new_isbn,
                        'salesDate': raw_date,
                        'last_notified': sales_date_num if sales_date_num else today_num,
                        'publisher': current_publisher
                    })
                    updated = True
                    print(f"⏭️ 既刊データ更新: {found_item['title']}")
                
                else:
                    print(f"💤 通知済み/待機中: {found_item['title']} (あと{days_left}日)")
                    
            else:
                print(f"❓ ヒットなし: {pure_title}")
                
        except Exception as e:
            print(f"‼️ エラー ({title_key}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    payload = {"messages": [{"type": "text", "text": message}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except:
        pass

if __name__ == "__main__":
    check_new_manga()
