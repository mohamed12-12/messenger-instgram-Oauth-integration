import os
import json
import uuid
import time
import logging
import hmac
import hashlib
import requests
import secrets

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from dotenv import load_dotenv

# ─── Load Environment ────────────────────────────────────────────────────────
load_dotenv()

# Configuration
META_APP_ID     = os.getenv('META_APP_ID')
META_APP_SECRET = os.getenv('META_APP_SECRET')
REDIRECT_URI    = os.getenv('REDIRECT_URI')
VERIFY_TOKEN    = os.getenv('VERIFY_TOKEN', 'nanovate_messenger_verify_2026')
SECRET_KEY      = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key_123')

# Flask App Initialization
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Facebook Graph API version
GRAPH_VERSION = 'v22.0'
GRAPH_BASE    = f'https://graph.facebook.com/{GRAPH_VERSION}'

# Scopes required for the app review
SCOPES = 'pages_messaging,pages_manage_metadata,pages_read_engagement,pages_show_list'

# ─── Persistent Storage Files ────────────────────────────────────────────────
MESSAGES_FILE = os.path.join(os.path.dirname(__file__), 'recent_messages.json')
CONFIG_FILE   = os.path.join(os.path.dirname(__file__), 'config.json')
TOKEN_FILE    = os.path.join(os.path.dirname(__file__), 'page_tokens.json')

# ─── Storage Helpers ────────────────────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_FILE): return {'auto_response': False}
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return {'auto_response': False}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f)

def save_page_token(page_id, token):
    tokens = {}
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f: tokens = json.load(f)
        except: pass
    tokens[page_id] = token
    try:
        with open(TOKEN_FILE, 'w') as f: json.dump(tokens, f)
    except Exception as e:
        logger.error("Failed to write to token file: %s", e)

def get_page_token(page_id):
    if not os.path.exists(TOKEN_FILE): return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            return tokens.get(page_id)
    except: return None

def load_messages():
    if not os.path.exists(MESSAGES_FILE): return []
    try:
        with open(MESSAGES_FILE, 'r') as f: return json.load(f)
    except: return []

def save_message(msg):
    messages = load_messages()
    messages.insert(0, msg)
    messages = messages[:15] # Keep last 15
    try:
        with open(MESSAGES_FILE, 'w') as f: json.dump(messages, f)
    except Exception as e:
        logger.error("Failed to write to messages file: %s", e)

# ─── Graph API Helpers ───────────────────────────────────────────────────────
def subscribe_page_to_webhook(page_id: str, page_access_token: str) -> bool:
    try:
        resp = requests.post(
            f'{GRAPH_BASE}/{page_id}/subscribed_apps',
            params={
                'subscribed_fields': 'messages,messaging_postbacks,messaging_optins',
                'access_token':      page_access_token,
            },
            timeout=10
        )
        return resp.json().get('success', False)
    except: return False

def send_graph_message(recipient_id: str, text: str, page_access_token: str) -> dict:
    try:
        resp = requests.post(
            f'{GRAPH_BASE}/me/messages',
            params={'access_token': page_access_token},
            json={
                'recipient': {'id': recipient_id},
                'message': {'text': text}
            },
            timeout=10
        )
        return resp.json()
    except Exception as e:
        return {'error': str(e)}

def graph_get(path: str, params: dict) -> dict:
    resp = requests.get(f'{GRAPH_BASE}/{path}', params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect')
def connect():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    fb_url = (
        "https://www.facebook.com/v22.0/dialog/oauth"
        f"?client_id={META_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
        f"&scope={SCOPES}"
    )
    return redirect(fb_url)

@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        return render_template('index.html', error='CSRF Error. Please try again.'), 400
    try:
        token_data = graph_get('oauth/access_token', {
            'client_id':     META_APP_ID,
            'redirect_uri':  REDIRECT_URI,
            'client_secret': META_APP_SECRET,
            'code':          code
        })
        session['user_access_token'] = token_data.get('access_token')
        pages_data = graph_get('me/accounts', {'access_token': session['user_access_token']})
        return render_template('select_page.html', pages=pages_data.get('data', []))
    except Exception as e:
        return render_template('index.html', error=str(e)), 500

@app.route('/connect-page/<page_id>')
def connect_page(page_id):
    user_token = session.get('user_access_token')
    if not user_token: return redirect('/')
    try:
        page_data = graph_get(page_id, {'fields': 'access_token,name', 'access_token': user_token})
        page_token = page_data.get('access_token')
        if subscribe_page_to_webhook(page_id, page_token):
            session['connected_page_id'] = page_id
            session['connected_page_name'] = page_data.get('name')
            session['page_access_token'] = page_token
            try:
                save_page_token(page_id, page_token)
            except: pass
            return redirect(url_for('dashboard'))
        return render_template('index.html', error='Subscription failed'), 500
    except Exception as e:
        return render_template('index.html', error=str(e)), 500

@app.route('/dashboard')
def dashboard():
    page_name = session.get('connected_page_name')
    if not page_name: return redirect('/')
    return render_template('dashboard.html', page_name=page_name)

@app.route('/api/recent-messages')
def get_recent_messages():
    return jsonify(load_messages())

@app.route('/api/toggle-auto-response', methods=['POST'])
def toggle_auto_response():
    cfg = load_config()
    cfg['auto_response'] = not cfg.get('auto_response', False)
    save_config(cfg)
    return jsonify(cfg)

@app.route('/api/config')
def get_config():
    return jsonify(load_config())

@app.route('/send-message', methods=['POST'])
def send_message():
    recipient_id = request.form.get('recipient_id')
    message_text = request.form.get('message')
    token = session.get('page_access_token')
    result = send_graph_message(recipient_id, message_text, token)
    if 'message_id' in result:
        return jsonify({'success': True, 'result': result})
    return jsonify({'success': False, 'error': result}), 400

# ─── WEBHOOKS ───────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['GET'])
@app.route('/messenger', methods=['GET'])
def webhook_verify():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
@app.route('/messenger', methods=['POST'])
def webhook_event():
    # Basic signature validation (Optional but recommended)
    data = request.json
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            page_id = entry.get('id')
            for event in entry.get('messaging', []):
                sender_id = event.get('sender', {}).get('id')
                message = event.get('message', {})
                text = message.get('text')
                if text:
                    save_message({
                        'page_id': page_id,
                        'sender_id': sender_id,
                        'text': text,
                        'timestamp': event.get('timestamp')
                    })
                    # Auto-Responder Logic
                    if load_config().get('auto_response'):
                        token = get_page_token(page_id)
                        if token:
                            reply_text = "hello Iam niva, how can i help? "
                            res = send_graph_message(sender_id, reply_text, token)
                            if 'message_id' in res:
                                save_message({
                                    'page_id': page_id,
                                    'sender_id': 'AUTO_REPLY',
                                    'text': f"NIVA: {reply_text} (ID: {res['message_id']})",
                                    'is_reply': True,
                                    'timestamp': int(time.time() * 1000)
                                })
        return "EVENT_RECEIVED", 200
    return "IGNORED", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
