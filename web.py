from flask import Flask

app = Flask(name)


@app.route('/')
def home():
    return "Bot is running"


@app.route('/health')
def health():
    return "OK"
