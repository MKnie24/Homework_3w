from flask import Flask, request, jsonify
import json
import requests
import datetime
from deep_translator import GoogleTranslator
from better_profanity import profanity

# Flask App
app = Flask(__name__)

# Configuration
HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "AI Translator Chat Channel"
CHANNEL_ENDPOINT = "http://localhost:5001"
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'
MESSAGE_LIMIT = 50

FILTERED_WORDS = {"badword1", "badword2"}
profanity.load_censor_words()

LANGUAGES = ["en", "fr", "de", "es", "it", "nl" ,"pt"]

# Welcome Message
WELCOME_MESSAGE = {
    "original": "Welcome to AI Chat! Discuss and chat freely with the available translations!",
    "translations": {lang: "Welcome to AI Chat! Discuss and chat freely with the available translations!" for lang in LANGUAGES},
    "sender": "System",
    "timestamp": datetime.datetime.now().isoformat()
}

# Ensure messages.json exists
def read_messages():
    try:
        with open(CHANNEL_FILE, 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = [WELCOME_MESSAGE]
    return messages[-MESSAGE_LIMIT:]

def save_messages(messages):
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

def translate_message(text, target_lang):
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return "Translation failed"

def generate_reply(content):
    if "hello" in content.lower():
        return "Hi there! Can I help you with translations?"
    return None

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"name": CHANNEL_NAME}), 200

@app.route('/', methods=['GET', 'POST'])
def handle_messages():
    messages = read_messages()

    if request.method == 'GET':
        return jsonify(messages)

    elif request.method == 'POST':
        if request.headers.get('Authorization') != f'authkey {CHANNEL_AUTHKEY}':
            return "Invalid authorization", 400

        data = request.json
        if not data or 'content' not in data or 'sender' not in data:
            return "Invalid message format", 400

        content, sender = data['content'], data['sender']

        if profanity.contains_profanity(content):
            return jsonify({"error": "Message contains inappropriate language", "allow_retry": True}), 400

        translations = {lang: translate_message(content, lang) for lang in LANGUAGES}
        new_message = {
            'original': content,
            'translations': translations,
            'sender': sender,
            'timestamp': datetime.datetime.now().isoformat()
        }

        messages.append(new_message)

    
        bot_reply = generate_reply(content)
        if bot_reply:
            messages.append({
                'original': bot_reply,
                'translations': {lang: translate_message(bot_reply, lang) for lang in LANGUAGES},
                'sender': "AI Bot",
                'timestamp': datetime.datetime.now().isoformat()
            })

        save_messages(messages[-MESSAGE_LIMIT:])
        return jsonify(new_message), 200

@app.cli.command('register')
def register_command():
    response = requests.post(
        f"{HUB_URL}/channels",
        headers={'Authorization': f'authkey {HUB_AUTHKEY}'},
        json={
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY,
            "type_of_service": CHANNEL_TYPE_OF_SERVICE,
        }
    )
    if response.status_code != 200:
        print(f"Error creating channel: {response.status_code}")
        print(response.text)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
