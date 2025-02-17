from flask import Flask
from threading import Thread

app = Flask(__name__)  # แก้ไขจาก flask('') เป็น Flask(__name__)

@app.route('/')
def home():
    return "Server is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def server_on():  # แก้ไขจาก sever_on เป็น server_on
    t = Thread(target=run)
    t.start()