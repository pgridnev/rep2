from flask import Flask
import time

app = Flask(__name__)

@app.route("/")
def hello_world():
    now = str(time.time())
    return f"<b>Time: {now}</b>"

app.run(port=8080)