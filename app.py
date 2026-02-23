import os
import requests
from datetime import datetime, timedelta, timezone
import time

# --- 設定（GitHub Secretsに登録するもの） ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID', '').strip()  # 楽天アフィリエイトID

def get_supabase_data():
    """Supabaseから全ユーザーのマンガリストを取得"""
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def update_supabase_data(row_id, update_data):
    """通知日、ISBN、発売日を更新"""
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{row_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    requests.patch(url, headers=headers, json=update_data)

def check_new_manga():
    jst = timezone(timedelta(hours=+9))
    now_jst = datetime.now(jst)
    today_num = now_jst.strftime('%Y%m%d')
    # 比較用に時間を切り捨てた「今日」のオブジェクト
    today_dt = datetime(now_jst.year, now_jst.month, now_jst.day)
    
    # ユーザーごとに通知をまとめる
    notifications = {}

    for item in manga_list:
        # 予約済み(is_reserved=True)ならスキップ
        if item.get('is_reserved'):
            continue

        user_id = item['user_id']
        row_id = item['id']
        pure_title = item['title_key']
        author_name = item.get('author', '')
        stored_isbn = item.get('isbn', '')
        stored_sales_date = item.get('sales_date', '')
        last_notified = item.get('last_notified', '')

        # 楽天APIで検索
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "format": "json",
            "title": pure_title,
            "author": author_name,
            "sort": "-releaseDate",
            "booksGenreId": "001001"
        }

        try:
            res = requests.get(url, params=params)
            data = res.json()
            if "Items" in data and len(data["Items"]) > 0:
                found = data["Items"][0]["Item"]
                new_isbn = found['isbn']
                raw_date = found['salesDate']
                image_url = found.get('largeImageUrl', found.get('mediumImageUrl', ''))
                
                # 日付変換
                try:
                    sales_date_dt = datetime.strptime(raw_date, '%Y年%m月%d日')
                    sales_date_num = sales_date_dt.strftime('%Y%m%d')
                    days_left = (sales_date_dt - today).days
                except:
                    sales_date_num = ""
                    days_left = 999

                # データ更新チェック（ISBNまたは発売日が変更）
                is_data_updated = (new_isbn != stored_isbn or raw_date != stored_sales_date)
                
                # 通知判定ルール（is_reserved=falseの場合のみ）
                notify_type = None
                if days_left == 30:   notify_type = "📅【30日前】"
                elif days_left == 14: notify_type = "📅【14日前】"
                elif days_left == 7:  notify_type = "📅【7日前】"
                elif days_left == 0:  notify_type = "🔥【本日発売】"

                # 重複通知防止チェック
                should_notify = notify_type and last_notified != today_num
                
                if should_notify:
                    # 通知データを収集（後でカルーセル化）
                    # 通知送信後にDBを更新するようにロジックを移動
                if notify_type and last_notified != today_num:
                    if user_id not in notifications:
                        notifications[user_id] = []
                    
                    notifications[user_id].append({
                        'type': notify_type,
                        'title': found['title'],
                        'sales_date': raw_date,
                        'image_url': image_url,
                        'isbn': new_isbn,
                        'rakuten_url': f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc=https%3A%2F%2Fbooks.rakuten.co.jp%2Frb%2F{new_isbn}%2F" if RAKUTEN_AFFILIATE_ID else f"https://books.rakuten.co.jp/rb/{new_isbn}/",
                        'amazon_url': f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    })
                    
                    # データベース更新（通知はまだしない）
                    update_supabase_data(row_id, {
                        "isbn": new_isbn,
                        "sales_date": raw_date,
                        "last_notified": today_num
                    })
                elif is_data_updated:
                    # データ更新のみ（通知なし）
                    update_supabase_data(row_id, {
                        "isbn": new_isbn,
                        "sales_date": raw_date
                    })
            
            time.sleep(1)  # API負荷軽減
        except Exception as e:
            print(f"❌ Error checking {pure_title}: {e}")
    
    # すべてのマンガをチェックした後、ユーザーごとにカルーセル通知
    for user_id, items in notifications.items():
        if send_line_carousel(user_id, items):
            for item in items:
                update_supabase_data(item['row_id'], {
                    "isbn": item['isbn'],
                    "sales_date": item['sales_date'],
                    "last_notified": today_num
                })
            print(f"✅ カルーセル通知送信: {user_id} ({len(items)}件)")

def send_line_carousel(user_id, items):
    """カルーセル形式でマンガ通知を送信（Flex Message）"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    # Flex Messageのバブル（カルーセルの各カード）を作成
    bubbles = []
    for item in items[:10]:  # 最大10件まで
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": item['image_url'] if item['image_url'] else "https://via.placeholder.com/1040x1040/CCCCCC/FFFFFF?text=No+Image",
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": item['type'],
                        "weight": "bold",
                        "size": "sm",
                        "color": "#FF6B6B"
                    },
                    {
                        "type": "text",
                        "text": item['title'],
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"発売日: {item['sales_date']}",
                        "size": "sm",
                        "color": "#999999",
                        "margin": "sm"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#C8102E",
                        "action": {
                            "type": "uri",
                            "label": "楽天で見る",
                            "uri": item['rakuten_url']
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF9900",
                        "action": {
                            "type": "uri",
                            "label": "Amazonで見る",
                            "uri": item['amazon_url']
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)
    
    # カルーセルメッセージを構築
    messages = [{
        "type": "flex",
        "altText": f"マンガ新刊通知 {len(items)}件",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }]
    
    payload = {
        "to": user_id,
        "messages": messages
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.status_code == 200
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 マンガチェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    check_new_manga()
    print(f"✨ マンガチェック完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

