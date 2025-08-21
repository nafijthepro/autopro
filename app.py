from flask import Flask, render_template, request, Response
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

BINGE_OTP_API = "https://web-api.binge.buzz/api/v3/otp/send/{}"
BIKROY_OTP_API = "https://bikroy.com/data/phone_number_login/verifications/phone_login?phone={}"

def send_single_otp(phone, attempt_number):
    result = {"attempt": attempt_number}
    try:
        # Binge first
        binge_resp = requests.get(BINGE_OTP_API.format(phone), headers={
            "accept": "application/json",
            "device-type": "web",
            "user-agent": "Mozilla/5.0",
            "origin": "https://binge.buzz",
            "referer": "https://binge.buzz/"
        }, timeout=5)
        if binge_resp.status_code == 200:
            result.update({"service": "Binge", "status": "success", "response": binge_resp.json()})
            return result
        else:
            raise Exception("Binge failed")
    except:
        # Fallback to Bikroy
        try:
            bikroy_resp = requests.get(BIKROY_OTP_API.format(phone), headers={
                "accept": "application/json",
                "user-agent": "Mozilla/5.0",
                "referer": "https://bikroy.com/?login-modal=true&redirect-url=/"
            }, timeout=5)
            if bikroy_resp.status_code == 200:
                result.update({"service": "Bikroy", "status": "success", "response": bikroy_resp.json()})
            else:
                result.update({"service": "Bikroy", "status": "failed"})
        except Exception as e:
            result.update({"service": "Bikroy", "status": "error", "error": str(e)})
    return result

def otp_generator(phone, attempts):
    with ThreadPoolExecutor(max_workers=attempts) as executor:
        futures = [executor.submit(send_single_otp, phone, i+1) for i in range(attempts)]
        for future in as_completed(futures):
            yield f"data: {json.dumps(future.result())}\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send-live-otp', methods=['POST'])
def send_live_otp():
    phone = request.form.get('phone')
    attempts = int(request.form.get('attempts', 1))
    if not phone:
        return "Phone number required", 400
    if attempts < 1 or attempts > 10:
        return "Attempts must be 1-10", 400

    return Response(otp_generator(phone, attempts), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
