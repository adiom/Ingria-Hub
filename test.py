import requests

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyCTu_alZJ9G2K7Ps8Gi90qCI15uEWwc22A"
payload = {
    "contents": [
        {
            "parts": [
                {"text": "расскажи про себя на раз два три"}
            ]
        }
    ]
}
resp = requests.post(url, json=payload)
print(resp.status_code, resp.text)