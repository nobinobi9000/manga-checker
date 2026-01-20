import os
import requests

TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()

def test():
    print(f"DEBUG: Token length = {len(TOKEN)}")
    res = requests.post(
        "https://notify-bot.line.me/api/notify",
        headers={"Authorization": f"Bearer {TOKEN}"},
        data={"message": "テスト通知です！これが届けば設定は完璧です。"}
    )
    print(f"HTTP Status: {res.status_code}")
    print(f"Response: {res.json()}")

if __name__ == "__main__":
    test()
