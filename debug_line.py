import os
import requests
import json

# GitHub Secretsから172文字の「チャネルアクセストークン（長期）」を読み込む
TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()

def test_messaging_api():
    print("--- LINE Messaging API 診断開始 ---")
    print(f"トークン長: {len(TOKEN)} 文字")
    
    # 宛先URL（公式アカウントの全登録者にメッセージを送るエンドポイント）
    url = "https://api.line.me/v2/bot/message/broadcast"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    
    # 送信するメッセージ内容
    payload = {
        "messages": [
            {
                "type": "text",
                "text": "テスト通知です！このメッセージが届けば、Messaging APIの設定は正常です。"
            }
        ]
    }

    try:
        # JSON形式でPOST送信
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        
        print(f"HTTPステータス: {res.status_code}")
        print(f"レスポンス内容: {res.text}")
        
        if res.status_code == 200:
            print("✅ 成功！LINE公式アカウントからメッセージが届いているか確認してください。")
        else:
            print(f"❌ エラー: ステータス {res.status_code}。トークンが正しいか、LINE Developersの設定を確認してください。")

    except Exception as e:
        print(f"‼️ 通信エラー: {e}")

if __name__ == "__main__":
    test_messaging_api()
