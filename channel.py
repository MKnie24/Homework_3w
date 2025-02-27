## channel.py - AI Chat Channel with Translation

from flask import Flask, request, jsonify
import json
import requests
from deep_translator import GoogleTranslator


# Configuration
class ConfigClass(object):
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'


# Flask App
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "AI Chat Channel"
CHANNEL_ENDPOINT = "http://localhost:5001"
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'
MESSAGE_LIMIT = 50  # Keep only last 50 messages
FILTERED_WORDS = {"badword1", "badword2"}  # Add more words as needed

# List of supported European languages
LANGUAGES = [
    "en", "fr", "de", "es", "pt", "it", "nl", "ru", "pl", "sv", "da", "fi", "no", "el", "cs", "hu", "ro", "bg", "hr",
    "sk", "sl", "et", "lv", "lt", "ga", "mt", "is", "sq", "bs", "mk", "sr", "uk"
]


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


def check_authorization(request):
    return request.headers.get('Authorization') == f'authkey {CHANNEL_AUTHKEY}'


@app.route('/', methods=['GET', 'POST'])
def handle_messages():
    if request.method == 'GET':  # Fetch messages
        if not check_authorization(request):
            return "Invalid authorization", 400
        return jsonify(read_messages())

    elif request.method == 'POST':  # Send a new message
        if not check_authorization(request):
            return "Invalid authorization", 400

        message = request.json
        if not message or 'content' not in message or 'sender' not in message:
            return "Invalid message format", 400

        content = message['content']
        sender = message['sender']

        # Check for profanity
        if any(word in content.lower() for word in FILTERED_WORDS):
            return jsonify({"error": "Message contains forbidden words"}), 400

        # Translate message
        translations = {lang: translate_message(content, lang) for lang in LANGUAGES}

        new_message = {
            'original': content,
            'translations': translations,
            'sender': sender,
            'timestamp': message.get('timestamp'),
        }

        messages = read_messages()
        messages.append(new_message)

        # Keep only last MESSAGE_LIMIT messages
        save_messages(messages[-MESSAGE_LIMIT:])

        return jsonify({
            "original": content,
            "translations": translations
        }), 200


def read_messages():
    try:
        with open(CHANNEL_FILE, 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []

    # Ensure all messages have translations
    for message in messages:
        if "translations" not in message:
            message["translations"] = {lang: translate_message(message.get("content", ""), lang) for lang in LANGUAGES}

    return messages[-MESSAGE_LIMIT:]


def save_messages(messages):
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)


def translate_message(text, target_lang):
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return "Translation failed"


if __name__ == '__main__':
    app.run(port=5001, debug=True)
