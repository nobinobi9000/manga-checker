import os
import requests

# Secretsから読み込み（前後の空白を完全に除去）
TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()

def test():
    print("--- LINE通知 診断開始 ---")
    print(f"Tokenの長さ: {len(TOKEN)} 文字")
    
    # LINE Notify 公式エンドポイント
    url = "https://notify-api.line.me/api/notify"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    payload = {
        "message": "GitHub Actionsからのテスト通知です。これが届いたら成功です！"
    }

    try:
        # タイムアウトを設定し、POSTで送信
        res = requests.post(url, headers=headers, data=payload, timeout=10)
        
        print(f"HTTPステータス: {res.status_code}")
        
        if res.status_code == 200:
            print("✅ 成功！LINEを確認してください。")
        elif res.status_code == 401:
            print("❌ 認証エラー: トークンが無効です。LINE Notifyで再発行してください。")
        elif res.status_code == 405:
            print("❌ メソッドエラー: URLが間違っている可能性があります。")
        else:
            print(f"⚠️ その他のエラー: {res.text}")

    except Exception as e:
        print(f"‼️ 通信自体に失敗しました: {e}")

if __name__ == "__main__":
    test()
