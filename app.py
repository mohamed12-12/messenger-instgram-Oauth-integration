"""Core Flask application for Meta Messenger and Instagram integration.

This file is intentionally organized into clear sections so the team can
integrate or split features later without changing behavior:
- environment and app setup
- persistent storage helpers
- Graph API and messaging helpers
- Flask routes grouped by domain
- compliance endpoints
"""

import os
import json
import uuid
import time
import logging
import hashlib
import requests
import secrets

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from collections import deque
import hmac as hmac_module
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Environment and application setup
# -----------------------------------------------------------------------------
load_dotenv()

# Runtime configuration
META_APP_ID     = os.getenv('META_APP_ID')
META_APP_SECRET = os.getenv('META_APP_SECRET')
REDIRECT_URI    = os.getenv('REDIRECT_URI')
VERIFY_TOKEN    = os.getenv('VERIFY_TOKEN', 'nanovate_messenger_verify_2026')
SECRET_KEY      = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key_123')

# Instagram-specific configuration
INSTAGRAM_REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI')
INSTAGRAM_SCOPES = 'instagram_basic,instagram_manage_messages,instagram_manage_comments,pages_messaging,pages_read_engagement,pages_show_list,pages_manage_metadata,business_management'

# WhatsApp-specific configuration
WHATSAPP_APP_ID = os.getenv('WHATSAPP_APP_ID')
WHATSAPP_APP_SECRET = os.getenv('WHATSAPP_APP_SECRET')
WHATSAPP_REDIRECT_URI = os.getenv('WHATSAPP_REDIRECT_URI')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', 'nanovate_whatsapp_verify_2026')
WHATSAPP_SCOPES = 'business_management,whatsapp_business_management,whatsapp_business_messaging'

# Flask app initialization
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Meta Graph API constants
GRAPH_VERSION = 'v22.0'
GRAPH_BASE    = f'https://graph.facebook.com/{GRAPH_VERSION}'

# OAuth scopes required by the app
SCOPES = 'pages_messaging,pages_manage_metadata,pages_read_engagement,pages_read_user_content,pages_show_list,business_management'
NO_BUSINESS_PORTFOLIO_MESSAGE = (
    'No Business Portfolio was returned by Meta for this user. '
    'Please set up a Business Manager / Business Portfolio first, make sure you are an admin, '
    'then reconnect Nanovate and approve the business_management permission.'
)

# -----------------------------------------------------------------------------
# Persistent storage paths
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
MESSAGES_FILE = os.path.join(BASE_DIR, 'recent_messages.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'page_tokens.json')
LEGACY_INSTAGRAM_MESSAGES_FILE = os.path.join(BASE_DIR, 'instagram_messages.json')
WEBHOOK_DEBUG_FILE = os.path.join(BASE_DIR, 'webhook_debug.json')
WHATSAPP_CONNECTION_FILE = os.path.join(BASE_DIR, 'whatsapp_connection.json')
WHATSAPP_WEBHOOK_DEBUG_FILE = os.path.join(BASE_DIR, 'whatsapp_webhook_debug.json')
WHATSAPP_MESSAGES_FILE = os.path.join(BASE_DIR, 'whatsapp_messages.json')

# In-memory storage for recent Instagram messages if the file does not exist
instagram_messages = []

# In-memory webhook hit tracking for debug endpoints
webhook_hits_log = deque(maxlen=10)
last_webhook_info = {
    'timestamp': None,
    'object_type': None,
    'entry_id': None,
    'sender_id': None
}

# -----------------------------------------------------------------------------
# Storage helpers
# -----------------------------------------------------------------------------
def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f)

def save_connected_page_context(page_id, page_name):
    cfg = load_config()
    pages = cfg.setdefault('pages', {})
    pages[str(page_id)] = {'name': page_name}
    save_config(cfg)

def get_connected_page_context():
    return session.get('connected_page_id'), session.get('connected_page_name')

def save_instagram_account_context(ig_account_id, username):
    cfg = load_config()
    accounts = cfg.setdefault('instagram_accounts', {})
    accounts[str(ig_account_id)] = {'username': username}
    save_config(cfg)

def get_saved_page_name(page_id):
    if not page_id:
        return None
    if session.get('connected_page_id') == page_id and session.get('connected_page_name'):
        return session.get('connected_page_name')
    cfg = load_config()
    return ((cfg.get('pages') or {}).get(str(page_id)) or {}).get('name')

def get_saved_instagram_username(ig_account_id):
    if not ig_account_id:
        return None
    if session.get('instagram_account_id') == ig_account_id and session.get('instagram_username'):
        return session.get('instagram_username')
    cfg = load_config()
    return ((cfg.get('instagram_accounts') or {}).get(str(ig_account_id)) or {}).get('username')

def get_messages_file(page_id=None):
    if page_id:
        return os.path.join(os.path.dirname(__file__), f'messages_{page_id}.json')
    return MESSAGES_FILE

def build_instagram_messages_file(ig_account_id):
    return os.path.join(BASE_DIR, f'instagram_messages_{ig_account_id}.json')

def build_page_webhook_debug_file(page_id):
    return os.path.join(BASE_DIR, f'webhook_{page_id}.json')

def load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_json_list(path, items):
    with open(path, 'w') as f:
        json.dump(items, f)

def load_json_object(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_json_object(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)

def save_page_webhook_debug(page_id, endpoint, data, headers):
    if not page_id:
        return
    try:
        with open(build_page_webhook_debug_file(page_id), 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'endpoint': endpoint,
                'page_id': page_id,
                'headers': headers,
                'data': data
            }, f)
    except Exception as e:
        logger.error(f"Page webhook debug write failed for {page_id}: {e}")

def load_page_webhook_debug(page_id):
    if not page_id:
        return None
    path = build_page_webhook_debug_file(page_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def iter_storage_files(prefix):
    for filename in os.listdir(BASE_DIR):
        if filename.startswith(prefix) and filename.endswith('.json'):
            yield os.path.join(BASE_DIR, filename)

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

def load_messages(page_id=None):
    f = get_messages_file(page_id)
    if not os.path.exists(f): return []
    try:
        with open(f, 'r') as fp: return json.load(fp)
    except: return []

def get_messages_for_page(page_id):
    if not page_id:
        return []
    messages = load_messages(page_id)
    messages.sort(key=lambda msg: msg.get('timestamp', 0), reverse=True)
    return messages[:15]

def get_recent_global_messages():
    messages = load_messages()
    messages.sort(key=lambda msg: msg.get('timestamp', 0), reverse=True)
    return messages[:25]

def save_message(msg):
    page_id = msg.get('page_id')
    logger.info(f"💾 save_message called: page_id={msg.get('page_id')}, text={msg.get('text', '')[:30]}")
    if page_id:
        logger.info(f"💾 Writing to messages_{page_id}.json")
        f = get_messages_file(page_id)
        messages = load_messages(page_id)
        messages.insert(0, msg)
        messages = messages[:15]
        try:
            with open(f, 'w') as fp: json.dump(messages, fp)
        except Exception as e:
            logger.error(f"Failed to write page messages: {e}")
    else:
        logger.warning("⚠️ save_message called WITHOUT page_id!")
    messages = load_messages()
    messages.insert(0, msg)
    messages = messages[:15]
    try:
        with open(MESSAGES_FILE, 'w') as fp: json.dump(messages, fp)
    except Exception as e:
        logger.error(f"Failed to write global messages: {e}")

def record_messenger_text_event(page_id, sender_id, text, ts, source, asset_type='page'):
    save_message({
        'page_id': page_id,
        'asset_id': page_id,
        'asset_type': asset_type,
        'sender_id': sender_id,
        'text': text,
        'timestamp': ts,
        'source': source
    })

    logger.info("Saved %s message from %s for page %s", source, sender_id, page_id)

def save_instagram_message(msg, ig_account_id=None):
    ig_account_id = ig_account_id or msg.get('page_id') or msg.get('asset_id')
    if not ig_account_id:
        logger.warning("Skipping Instagram message save because page/account id is missing: %s", msg)
        return
    messages = load_instagram_messages(ig_account_id)
    messages.insert(0, msg)
    messages = messages[:20] # Keep last 20
    try:
        save_json_list(build_instagram_messages_file(ig_account_id), messages)
    except Exception as e:
        logger.error("Failed to write to instagram messages file: %s", e)

def load_instagram_messages(ig_account_id=None):
    if ig_account_id:
        return load_json_list(build_instagram_messages_file(ig_account_id))

    messages = []
    for path in iter_storage_files('instagram_messages_'):
        messages.extend(load_json_list(path))

    if not messages and os.path.exists(LEGACY_INSTAGRAM_MESSAGES_FILE):
        messages = load_json_list(LEGACY_INSTAGRAM_MESSAGES_FILE)

    return messages

def save_whatsapp_connection(data):
    save_json_object(WHATSAPP_CONNECTION_FILE, data)

def load_whatsapp_connection():
    return load_json_object(WHATSAPP_CONNECTION_FILE)

def get_whatsapp_connection():
    return load_whatsapp_connection()

def normalize_whatsapp_timestamp(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(time.time())

def load_whatsapp_messages(limit=25):
    messages = load_json_list(WHATSAPP_MESSAGES_FILE)
    messages.sort(key=lambda msg: normalize_whatsapp_timestamp(msg.get('timestamp')), reverse=True)
    return messages[:limit]

def save_whatsapp_inbound_message(msg):
    messages = load_json_list(WHATSAPP_MESSAGES_FILE)
    raw_webhook_id = msg.get('raw_webhook_id')
    if raw_webhook_id and any(item.get('raw_webhook_id') == raw_webhook_id for item in messages):
        logger.info("WhatsApp inbound message already saved: raw_webhook_id=%s", raw_webhook_id)
        return False

    messages.insert(0, msg)
    messages = messages[:50]
    save_json_list(WHATSAPP_MESSAGES_FILE, messages)
    logger.info(
        "WhatsApp inbound message saved: raw_webhook_id=%s wa_id=%s",
        raw_webhook_id,
        msg.get('wa_id')
    )
    return True

def extract_whatsapp_inbound_messages(data):
    inbound_messages = []
    for entry in data.get('entry', []) or []:
        for change in entry.get('changes', []) or []:
            value = change.get('value') or {}
            contacts = {}
            for contact in value.get('contacts', []) or []:
                wa_id = contact.get('wa_id')
                if wa_id:
                    contacts[wa_id] = contact

            for message in value.get('messages', []) or []:
                sender_phone_number = message.get('from') or ''
                contact = contacts.get(sender_phone_number) or {}
                sender_name = ((contact.get('profile') or {}).get('name') or '')
                message_type = message.get('type') or ''
                text_body = ''
                if message_type == 'text':
                    text_body = ((message.get('text') or {}).get('body') or '')

                inbound_messages.append({
                    'timestamp': normalize_whatsapp_timestamp(message.get('timestamp')),
                    'wa_id': contact.get('wa_id') or sender_phone_number,
                    'sender_phone_number': sender_phone_number,
                    'sender_name': sender_name,
                    'message_type': message_type,
                    'text_body': text_body,
                    'raw_webhook_id': message.get('id') or ''
                })

    return inbound_messages

# ─── Graph API Helpers ───────────────────────────────────────────────────────
def subscribe_page_to_webhook(page_id: str, page_access_token: str) -> bool:
    if not page_access_token:
        logger.error("Cannot subscribe page %s without a page access token.", page_id)
        return False
    try:
        subscribed_fields = (
            'messages,messaging_postbacks,messaging_optins,'
            'message_reads,message_deliveries,message_echoes,'
            'messaging_handovers,standby'
        )
        # Added message_reads, message_deliveries for better event tracking
        resp = requests.post(
            f'{GRAPH_BASE}/{page_id}/subscribed_apps',
            params={
                'subscribed_fields': subscribed_fields,
                'access_token':      page_access_token,
            },
            timeout=10
        )
        payload = resp.json()
        if resp.ok and payload.get('success', False):
            logger.info("Subscribed page %s to webhook successfully.", page_id)
            return True

        logger.error(
            "Webhook subscription failed for page %s. status=%s payload=%s",
            page_id,
            resp.status_code,
            payload
        )
    except Exception:
        logger.exception("Webhook subscription crashed for page %s.", page_id)
    return False

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

def graph_post(path: str, params: dict = None, data: dict = None) -> dict:
    resp = requests.post(
        f'{GRAPH_BASE}/{path}',
        params=params or {},
        data=data or {},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

def graph_delete(path: str, params: dict = None) -> dict:
    resp = requests.delete(
        f'{GRAPH_BASE}/{path}',
        params=params or {},
        timeout=15
    )
    if resp.content:
        data = resp.json()
    else:
        data = {'success': resp.ok}
    if not resp.ok:
        message = data.get('error', {}).get('message', 'Unknown Graph delete error')
        raise requests.HTTPError(message, response=resp)
    return data

def graph_post_json(path: str, access_token: str, payload: dict) -> dict:
    resp = requests.post(
        f'{GRAPH_BASE}/{path}',
        headers={'Authorization': f'Bearer {access_token}'},
        json=payload,
        timeout=15
    )
    if not resp.ok:
        try:
            data = resp.json()
        except ValueError:
            data = {'error': {'message': resp.text or 'Unknown Graph error'}}
        raise requests.HTTPError(
            data.get('error', {}).get('message', 'Unknown Graph error'),
            response=resp
        )
    return resp.json()

def format_graph_api_error(exc: Exception, default_message: str) -> tuple[str, int]:
    response = getattr(exc, 'response', None)
    if response is None:
        logger.exception("Graph API request failed without HTTP response.")
        return default_message, 500

    try:
        payload = response.json()
    except ValueError:
        logger.error("Graph API returned non-JSON error response: %s", response.text)
        return default_message, response.status_code or 500

    error = payload.get('error', {})
    code = error.get('code')
    subcode = error.get('error_subcode')
    message = error.get('message', default_message)
    lowered = message.lower()

    logger.error(
        "Graph API error. status=%s code=%s subcode=%s message=%s",
        response.status_code,
        code,
        subcode,
        message
    )

    if code == 190:
        return 'Meta access token is missing or expired. Please reconnect this integration.', 401
    if code in (10, 200):
        return 'Missing required Meta permissions for this action. Please reconnect the integration with the required scopes approved.', 403
    if code == 100:
        return 'Meta rejected one of the provided IDs or parameters.', 400
    if code in (4, 17, 32, 613) or 'rate limit' in lowered or 'too many calls' in lowered:
        return 'Meta rate limit reached. Please try again shortly.', 429

    return message or default_message, response.status_code or 500

def extract_graph_api_error_payload(exc: Exception) -> dict:
    response = getattr(exc, 'response', None)
    if response is None:
        return {}
    try:
        return response.json()
    except ValueError:
        return {'raw_response': response.text}

def extract_graph_api_error_message(exc: Exception) -> str:
    payload = extract_graph_api_error_payload(exc)
    if payload.get('error', {}).get('message'):
        return payload['error']['message']
    if payload.get('raw_response'):
        return payload['raw_response']
    return str(exc)

def fetch_instagram_media_comments(ig_account_id: str, page_access_token: str) -> list:
    logger.info("Instagram comments fetch started for account %s", ig_account_id)

    media_params = {
        'fields': 'id,media_type,media_url,thumbnail_url,timestamp',
        'limit': 5,
        'access_token': page_access_token
    }
    media_url = f'{GRAPH_BASE}/{ig_account_id}/media'

    logger.info("Graph GET start: %s params=%s", media_url, {'fields': media_params['fields'], 'limit': media_params['limit']})
    try:
        media_response = requests.get(media_url, params=media_params, timeout=15)
    except requests.Timeout:
        logger.error("Graph GET timeout while fetching media for account %s", ig_account_id)
        raise

    logger.info("Graph GET end: %s status=%s", media_url, media_response.status_code)
    media_response.raise_for_status()
    media_payload = media_response.json()
    logger.info(
        "Media fetch response for %s: data_count=%s paging_next=%s",
        ig_account_id,
        len(media_payload.get('data', [])),
        bool(media_payload.get('paging', {}).get('next'))
    )

    media_items = media_payload.get('data', [])[:5]
    if not media_items:
        logger.info("No media found for Instagram account %s", ig_account_id)
        return []

    comments = []
    for media in media_items:
        media_id = media.get('id')
        if not media_id:
            logger.warning("Skipping media item without id for account %s: %s", ig_account_id, media)
            continue

        logger.info("Fetching comments for media %s", media_id)
        next_url = f'{GRAPH_BASE}/{media_id}/comments'
        next_params = {
            'fields': 'id,text,username,timestamp,hidden',
            'access_token': page_access_token
        }
        seen_comment_pages = set()
        page_index = 0
        media_comment_count = 0

        while next_url and page_index < 10:
            page_index += 1
            page_key = next_url
            if page_key in seen_comment_pages:
                logger.warning("Stopping comment pagination loop for media %s due to repeated next URL: %s", media_id, next_url)
                break
            seen_comment_pages.add(page_key)

            logger.info(
                "Graph GET start: %s params=%s page=%s media_id=%s",
                next_url,
                {'fields': next_params.get('fields')} if next_params else {},
                page_index,
                media_id
            )
            try:
                comments_response = requests.get(next_url, params=next_params, timeout=15)
            except requests.Timeout:
                logger.error("Graph GET timeout while fetching comments for media %s page %s", media_id, page_index)
                raise

            logger.info(
                "Graph GET end: %s status=%s page=%s media_id=%s",
                next_url,
                comments_response.status_code,
                page_index,
                media_id
            )
            comments_response.raise_for_status()
            comments_payload = comments_response.json()

            page_comments = comments_payload.get('data', [])
            logger.info(
                "Comments fetch response for media %s: page=%s data_count=%s paging_next=%s",
                media_id,
                page_index,
                len(page_comments),
                bool(comments_payload.get('paging', {}).get('next'))
            )

            if not page_comments:
                logger.info("No comments returned for media %s on page %s", media_id, page_index)
                break

            for comment in page_comments:
                if not comment.get('id'):
                    logger.warning("Skipping malformed comment for media %s: %s", media_id, comment)
                    continue
                comments.append({
                    'comment_id': comment.get('id'),
                    'media_id': media_id,
                    'media_type': media.get('media_type'),
                    'media_url': media.get('media_url'),
                    'thumbnail_url': media.get('thumbnail_url'),
                    'comment_text': comment.get('text', ''),
                    'username': comment.get('username', 'unknown'),
                    'timestamp': comment.get('timestamp'),
                    'hidden': bool(comment.get('hidden', False))
                })
                media_comment_count += 1

            next_url = comments_payload.get('paging', {}).get('next')
            next_params = None
            logger.info(
                "Comments pagination status for media %s: next_url_present=%s accumulated_comments=%s",
                media_id,
                bool(next_url),
                media_comment_count
            )

        if page_index >= 10 and next_url:
            logger.warning("Stopped comment pagination for media %s after reaching page safety cap", media_id)

        if media_comment_count == 0:
            logger.info("Media %s has no accessible comments or comments may be disabled", media_id)

    comments.sort(key=lambda item: item.get('timestamp') or '', reverse=True)
    logger.info("Instagram comments fetch completed for account %s with %s comments", ig_account_id, len(comments))
    return comments

def fetch_instagram_comments(ig_account_id: str, page_access_token: str) -> list:
    return fetch_instagram_media_comments(ig_account_id, page_access_token)

def format_oauth_exchange_error(exc: Exception, platform_name: str) -> str:
    default_msg = f'{platform_name} login failed. Please click Connect again and do not refresh the callback page.'
    response = getattr(exc, 'response', None)
    if response is None:
        return default_msg

    try:
        payload = response.json()
    except ValueError:
        logger.error("%s OAuth exchange failed with non-JSON response: %s", platform_name, response.text)
        return default_msg

    error = payload.get('error', {})
    message = error.get('message', '')
    code = error.get('code')
    subcode = error.get('error_subcode')

    logger.error(
        "%s OAuth exchange failed. status=%s code=%s subcode=%s message=%s",
        platform_name,
        response.status_code,
        code,
        subcode,
        message
    )

    lowered = message.lower()
    if 'authorization code' in lowered or 'verification code' in lowered or 'code has been used' in lowered:
        return f'{platform_name} login code expired or was already used. Please click Connect again and complete the login flow once.'

    return default_msg

def graph_get_all_items(path: str, params: dict) -> list:
    items = []
    next_url = f'{GRAPH_BASE}/{path}'
    next_params = dict(params)

    while next_url:
        resp = requests.get(next_url, params=next_params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        items.extend(payload.get('data', []))
        next_url = payload.get('paging', {}).get('next')
        next_params = None

    return items

def get_user_pages(user_access_token: str) -> list:
    return graph_get_all_items('me/accounts', {'access_token': user_access_token})

def get_user_businesses(user_access_token: str) -> list:
    return graph_get_all_items('me/businesses', {
        'fields': 'id,name',
        'access_token': user_access_token
    })

def get_business_owned_pages(business_id: str, user_access_token: str) -> list:
    return graph_get_all_items(f'{business_id}/owned_pages', {
        'fields': 'id,name,access_token',
        'access_token': user_access_token
    })

def build_business_options(businesses: list) -> list:
    return [
        {'id': business.get('id'), 'name': business.get('name') or f"Business {business.get('id')}"}
        for business in businesses
        if business.get('id')
    ]

def build_page_options(pages: list) -> list:
    return [
        {
            'id': page.get('id'),
            'name': page.get('name') or f"Page {page.get('id')}",
            'access_token': page.get('access_token')
        }
        for page in pages
        if page.get('id')
    ]

def get_selected_business_context():
    return session.get('selected_business_id'), session.get('selected_business_name')

def find_business_or_none(user_access_token: str, business_id: str):
    businesses = get_user_businesses(user_access_token)
    return next((business for business in businesses if business.get('id') == business_id), None)

def get_page_assets_for_selected_business(user_access_token: str) -> list:
    business_id, _ = get_selected_business_context()
    if not business_id:
        return get_user_pages(user_access_token)

    business_pages = get_business_owned_pages(business_id, user_access_token)

    # Some owned_pages responses omit page access tokens. Merge with /me/accounts
    # so the selected asset can still be subscribed and used for messaging.
    pages_with_tokens = {
        page.get('id'): page
        for page in get_user_pages(user_access_token)
        if page.get('id')
    }
    for page in business_pages:
        token = page.get('access_token')
        if not token and page.get('id') in pages_with_tokens:
            page['access_token'] = pages_with_tokens[page.get('id')].get('access_token')
    return business_pages

def fetch_page_user_content(page_id: str, page_access_token: str) -> list:
    feed = graph_get(f'{page_id}/feed', {
        'fields': 'id,message,story,created_time,from,permalink_url',
        'limit': 10,
        'access_token': page_access_token
    })

    items = []
    for post in feed.get('data', []):
        post_id = post.get('id')
        comments = []
        comment_fetch_error = None

        if post_id:
            try:
                comment_payload = graph_get(f'{post_id}/comments', {
                    'fields': 'id,message,from,created_time,permalink_url',
                    'limit': 25,
                    'access_token': page_access_token
                })
            except requests.HTTPError as exc:
                logger.warning("Retrying comments fetch without permalink_url for post %s: %s", post_id, exc)
                try:
                    comment_payload = graph_get(f'{post_id}/comments', {
                        'fields': 'id,message,from,created_time',
                        'limit': 25,
                        'access_token': page_access_token
                    })
                except Exception as retry_exc:
                    comment_payload = {'data': []}
                    comment_fetch_error = str(retry_exc)
            except Exception as exc:
                comment_payload = {'data': []}
                comment_fetch_error = str(exc)

            for comment in comment_payload.get('data', []):
                comments.append({
                    'id': comment.get('id'),
                    'message': comment.get('message') or '',
                    'from_name': (comment.get('from') or {}).get('name') or 'Unknown',
                    'created_time': comment.get('created_time'),
                    'permalink_url': comment.get('permalink_url')
                })

        items.append({
            'id': post_id,
            'message': post.get('message') or '',
            'story': post.get('story') or '',
            'from_name': (post.get('from') or {}).get('name') or 'Unknown',
            'created_time': post.get('created_time'),
            'permalink_url': post.get('permalink_url'),
            'comments': comments,
            'comment_fetch_error': comment_fetch_error
        })

    return items

def build_page_comment_moderation_items(posts: list, page_id: str, page_name: str) -> list:
    moderation_items = []
    for post in posts:
        post_text = post.get('message') or post.get('story') or '[no post text]'
        for comment in post.get('comments', []):
            moderation_items.append({
                'page_id': page_id,
                'page_name': page_name,
                'post_id': post.get('id'),
                'post_text': post_text,
                'post_created_time': post.get('created_time'),
                'post_permalink_url': post.get('permalink_url'),
                'comment_id': comment.get('id'),
                'comment_text': comment.get('message') or '[no comment text]',
                'comment_author': comment.get('from_name') or 'Unknown',
                'comment_created_time': comment.get('created_time'),
                'comment_permalink_url': comment.get('permalink_url') or post.get('permalink_url'),
                'status': 'Needs review',
                'assigned_to': 'Unassigned',
                'sentiment': classify_comment_sentiment(comment.get('message') or '')
            })

    moderation_items.sort(key=lambda item: item.get('comment_created_time') or '', reverse=True)
    return moderation_items

def classify_comment_sentiment(text: str) -> str:
    lowered = text.lower()
    negative_terms = ('bad', 'angry', 'hate', 'issue', 'problem', 'refund', 'broken', 'not working')
    positive_terms = ('thanks', 'thank you', 'great', 'love', 'good', 'excellent', 'amazing')

    if any(term in lowered for term in negative_terms):
        return 'Negative'
    if any(term in lowered for term in positive_terms):
        return 'Positive'
    return 'Neutral'

def build_instagram_asset_options(pages: list) -> list:
    assets = []
    for page in pages:
        page_id = page.get('id')
        page_name = page.get('name') or f"Page {page_id}"
        page_token = page.get('access_token')
        asset = {
            'page_id': page_id,
            'page_name': page_name,
            'instagram_id': None,
            'username': None,
            'connectable': False,
            'reason': None
        }

        if not page_id:
            continue
        if not page_token:
            asset['reason'] = 'Meta did not return a Page access token for this asset.'
            assets.append(asset)
            continue

        try:
            page_info = graph_get(page_id, {
                'fields': 'instagram_business_account,name',
                'access_token': page_token
            })
            ig_account = page_info.get('instagram_business_account')
            if not ig_account:
                asset['reason'] = 'No Instagram Business account is linked to this Page.'
                assets.append(asset)
                continue

            ig_id = ig_account.get('id')
            ig_info = graph_get(ig_id, {'fields': 'username', 'access_token': page_token})
            asset.update({
                'instagram_id': ig_id,
                'username': ig_info.get('username') or ig_id,
                'connectable': bool(ig_id)
            })
        except requests.HTTPError as exc:
            logger.warning("Could not inspect Instagram asset for page %s: %s", page_id, exc)
            asset['reason'] = 'Meta rejected the Instagram asset lookup for this Page.'
        except Exception as exc:
            logger.warning("Could not inspect Instagram asset for page %s: %s", page_id, exc)
            asset['reason'] = 'This Page could not be inspected for a linked Instagram account.'

        assets.append(asset)
    return assets

def get_business_selection_template(flow: str, businesses: list, error: str = None, status_code: int = 200):
    business_options = build_business_options(businesses)
    return render_template(
        'select_business.html',
        flow=flow,
        businesses=business_options,
        error=error,
        no_businesses=not business_options,
        messenger_scopes=SCOPES,
        instagram_scopes=INSTAGRAM_SCOPES,
        graph_version=GRAPH_VERSION
    ), status_code

def get_connected_page_token(page_id=None):
    page_id = page_id or session.get('connected_page_id')
    if page_id and session.get('connected_page_id') == page_id and session.get('page_access_token'):
        return session.get('page_access_token')
    return get_page_token(page_id) if page_id else None

def get_instagram_page_token(ig_account_id=None):
    ig_account_id = ig_account_id or session.get('instagram_account_id')
    if ig_account_id and session.get('instagram_account_id') == ig_account_id and session.get('instagram_page_token'):
        return session.get('instagram_page_token')
    return get_page_token(ig_account_id) if ig_account_id else None

def send_instagram_message(recipient_id: str, text: str, page_access_token: str):
    return send_graph_message(recipient_id, text, page_access_token)

def get_whatsapp_app_id():
    return WHATSAPP_APP_ID or META_APP_ID

def get_whatsapp_app_secret():
    return WHATSAPP_APP_SECRET or META_APP_SECRET

def get_whatsapp_redirect_uri():
    return WHATSAPP_REDIRECT_URI or url_for('whatsapp_callback', _external=True)

def get_whatsapp_businesses(user_access_token: str) -> list:
    return graph_get_all_items('me/businesses', {
        'fields': 'id,name',
        'access_token': user_access_token
    })

def get_whatsapp_business_accounts(business_id: str, user_access_token: str) -> list:
    for edge in ('owned_whatsapp_business_accounts', 'client_whatsapp_business_accounts'):
        try:
            accounts = graph_get_all_items(
                f'{business_id}/{edge}',
                {'fields': 'id,name', 'access_token': user_access_token}
            )
            if accounts:
                return accounts
        except requests.HTTPError:
            logger.warning("Failed to fetch WhatsApp accounts from edge %s for business %s", edge, business_id)
    return []

def get_whatsapp_phone_numbers(waba_id: str, user_access_token: str) -> list:
    return graph_get_all_items(
        f'{waba_id}/phone_numbers',
        {'fields': 'id,display_phone_number,verified_name', 'access_token': user_access_token}
    )

def fetch_whatsapp_connection_data(user_access_token: str) -> dict:
    businesses = get_whatsapp_businesses(user_access_token)
    logger.info("WhatsApp OAuth retrieved %s businesses from Meta.", len(businesses))

    for business in businesses:
        business_id = business.get('id')
        if not business_id:
            continue

        wabas = get_whatsapp_business_accounts(business_id, user_access_token)
        logger.info("Business %s returned %s WhatsApp Business Accounts.", business_id, len(wabas))

        for waba in wabas:
            waba_id = waba.get('id')
            if not waba_id:
                continue

            phone_numbers = get_whatsapp_phone_numbers(waba_id, user_access_token)
            logger.info("WABA %s returned %s phone numbers.", waba_id, len(phone_numbers))
            if not phone_numbers:
                continue

            phone = phone_numbers[0]
            return {
                'business_id': business_id,
                'waba_id': waba_id,
                'phone_number_id': phone.get('id'),
                'display_phone_number': phone.get('display_phone_number') or phone.get('verified_name') or 'Unknown',
                'access_token': user_access_token,
                'connected_at': int(time.time())
            }

    raise ValueError(
        'No WhatsApp Business Account with an attached phone number was returned by Meta. '
        'Make sure the user has access to the Business Manager, WABA, and phone number.'
    )

def send_whatsapp_message(phone_number_id: str, to_number: str, text: str, access_token: str) -> dict:
    return graph_post_json(
        f'{phone_number_id}/messages',
        access_token=access_token,
        payload={
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'template',
            'template': {
                'name': 'hello_world',
                'language': {'code': 'en_US'}
            }
        }
    )

# -----------------------------------------------------------------------------
# Flask routes
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meta-oauth-debug')
def meta_oauth_debug():
    business_id, business_name = get_selected_business_context()
    return jsonify({
        'graph_version': GRAPH_VERSION,
        'messenger_scopes': SCOPES.split(','),
        'instagram_scopes': INSTAGRAM_SCOPES.split(','),
        'messenger_business_management_requested': 'business_management' in SCOPES.split(','),
        'messenger_pages_read_user_content_requested': 'pages_read_user_content' in SCOPES.split(','),
        'instagram_business_management_requested': 'business_management' in INSTAGRAM_SCOPES.split(','),
        'selected_business_id': business_id,
        'selected_business_name': business_name,
        'has_user_access_token_in_session': bool(session.get('user_access_token')),
        'expected_consent': 'Meta should show a Business Portfolio selection screen before the Page selection screen when the test user has Business access.'
    })

@app.route('/connect')
def connect():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    session.pop('selected_business_id', None)
    session.pop('selected_business_name', None)
    logger.info(
        "Messenger OAuth start. graph_version=%s requested_scopes=%s business_management_requested=%s redirect_uri=%s",
        GRAPH_VERSION,
        SCOPES,
        'business_management' in SCOPES.split(','),
        REDIRECT_URI
    )
    fb_url = (
        "https://www.facebook.com/v22.0/dialog/oauth"
        f"?client_id={META_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
        f"&scope={SCOPES}"
        "&response_type=code"
        "&auth_type=rerequest"
    )
    return redirect(fb_url)

@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')
    expected_state = session.pop('oauth_state', None)

    if not state or not expected_state or state != expected_state:
        # Senior Fix: If user hits 'Back' and is already connected, just go to dashboard
        if session.get('connected_page_id'):
            return redirect(url_for('dashboard', page_id=session.get('connected_page_id')))
        return render_template('index.html', error='CSRF Error. Please try again.'), 400
    if error:
        return render_template('index.html', error=error_description or error), 400
    if not code:
        return render_template('index.html', error='Missing Facebook login code. Please click Connect again.'), 400
    try:
        token_data = graph_get('oauth/access_token', {
            'client_id':     META_APP_ID,
            'redirect_uri':  REDIRECT_URI,
            'client_secret': META_APP_SECRET,
            'code':          code
        })
        session['user_access_token'] = token_data.get('access_token')
        if not session['user_access_token']:
            raise ValueError('Meta did not return a Facebook access token. Please reconnect and try again.')
        businesses = get_user_businesses(session['user_access_token'])
        logger.info(
            "Messenger OAuth retrieved %s businesses from Meta after requesting business_management. business_ids=%s",
            len(businesses),
            [business.get('id') for business in businesses if business.get('id')]
        )
        if not businesses:
            return get_business_selection_template(
                'messenger',
                [],
                error=NO_BUSINESS_PORTFOLIO_MESSAGE,
                status_code=400
            )

        return get_business_selection_template('messenger', businesses)
    except requests.HTTPError as e:
        logger.exception("Messenger auth callback token exchange failed.")
        return render_template('index.html', error=format_oauth_exchange_error(e, 'Facebook')), 400
    except ValueError as e:
        logger.warning("Messenger auth callback validation failed: %s", e)
        return render_template('index.html', error=str(e)), 400
    except Exception as e:
        logger.exception("Messenger auth callback failed.")
        return render_template('index.html', error='Facebook login failed unexpectedly. Please try connecting again.'), 500

@app.route('/select-business/<business_id>')
def select_business(business_id):
    user_token = session.get('user_access_token')
    if not user_token:
        return redirect('/')

    try:
        business = find_business_or_none(user_token, business_id)
        if not business:
            businesses = get_user_businesses(user_token)
            return get_business_selection_template(
                'messenger',
                businesses,
                error='The selected Business Portfolio was not returned by Meta. Reconnect and select the Business again.',
                status_code=400
            )

        session['selected_business_id'] = business.get('id')
        session['selected_business_name'] = business.get('name') or f"Business {business_id}"
        pages = get_page_assets_for_selected_business(user_token)
        page_options = build_page_options(pages)
        logger.info(
            "Messenger selected business %s returned %s owned page assets.",
            business_id,
            len(page_options)
        )
        if not page_options:
            return render_template(
                'select_page.html',
                pages=[],
                business=business,
                error='No owned Facebook Pages were returned for this Business Portfolio. Add a Page to Business Manager or select a different Business.'
            ), 400

        return render_template('select_page.html', pages=page_options, business=business)
    except requests.HTTPError as e:
        logger.exception("Fetching Messenger business assets failed.")
        return get_business_selection_template(
            'messenger',
            get_user_businesses(user_token),
            error=format_oauth_exchange_error(e, 'Facebook'),
            status_code=400
        )
    except Exception:
        logger.exception("Selecting Messenger business %s failed.", business_id)
        return render_template('index.html', error='Could not load assets for that Business Portfolio. Please reconnect and try again.'), 500

@app.route('/connect-page/<page_id>')
def connect_page(page_id):
    user_token = session.get('user_access_token')
    if not user_token: return redirect('/')
    try:
        pages = get_page_assets_for_selected_business(user_token)
        page_data = next((page for page in pages if page.get('id') == page_id), None)
        page_options = build_page_options(pages)
        business_id, business_name = get_selected_business_context()

        if not page_data:
            return render_template(
                'select_page.html',
                pages=page_options,
                business={'id': business_id, 'name': business_name} if business_id else None,
                error='The selected page was not returned by Meta. Reconnect and make sure that page is selected in the Facebook dialog.'
            ), 400

        page_token = page_data.get('access_token')
        page_name = page_data.get('name') or page_id
        if not page_token:
            logger.error("Meta returned page %s without an access token. payload=%s", page_id, page_data)
            return render_template(
                'select_page.html',
                pages=page_options,
                business={'id': business_id, 'name': business_name} if business_id else None,
                error=f"Meta did not return a page access token for '{page_name}'. Reconnect and verify the granted Page permissions."
            ), 502

        if subscribe_page_to_webhook(page_id, page_token):
            session['connected_page_id'] = page_id
            session['connected_page_name'] = page_name
            session['page_access_token'] = page_token
            save_connected_page_context(page_id, page_name)
            try:
                save_page_token(page_id, page_token)
            except: pass
            return render_template(
                'success.html',
                page_id=page_id,
                page_name=page_name,
                business_id=business_id,
                business_name=business_name
            )
        return render_template(
            'select_page.html',
            pages=page_options,
            business={'id': business_id, 'name': business_name} if business_id else None,
            error=f"Meta rejected the webhook subscription for '{page_name}'. Check that this page is granted to the app, then reconnect and try again."
        ), 502
    except Exception as e:
        logger.exception("Connecting page %s failed.", page_id)
        return render_template('select_page.html', pages=[], error=str(e)), 500

@app.route('/dashboard')
@app.route('/dashboard/<page_id>')
def dashboard(page_id=None):
    # If page_id in URL, use it directly (no session needed)
    if page_id:
        page_token = get_page_token(page_id)
        page_name = session.get('connected_page_name', f'Page {page_id}')
        return render_template('dashboard.html', 
                               page_name=page_name,
                               page_id=page_id,
                               has_token=bool(page_token))
    # Fallback to session
    page_name = session.get('connected_page_name')
    page_id = session.get('connected_page_id')
    if not page_name: return redirect('/')
    return render_template('dashboard.html', 
                           page_name=page_name,
                           page_id=page_id,
                           has_token=True)

# -----------------------------------------------------------------------------
# Instagram routes
# -----------------------------------------------------------------------------

@app.route('/instagram')
@app.route('/instagram/connect')
def instagram_connect():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    session.pop('selected_business_id', None)
    session.pop('selected_business_name', None)
    logger.info(
        "Instagram OAuth start. graph_version=%s requested_scopes=%s business_management_requested=%s redirect_uri=%s",
        GRAPH_VERSION,
        INSTAGRAM_SCOPES,
        'business_management' in INSTAGRAM_SCOPES.split(','),
        INSTAGRAM_REDIRECT_URI
    )
    # Added auth_type=rerequest to force the page selection dialog if they skipped it before
    fb_url = (
        "https://www.facebook.com/v22.0/dialog/oauth"
        f"?client_id={META_APP_ID}"
        f"&redirect_uri={INSTAGRAM_REDIRECT_URI}"
        f"&state={state}"
        f"&scope={INSTAGRAM_SCOPES}"
        "&auth_type=rerequest"
    )
    return redirect(fb_url)

@app.route('/instagram/auth/callback')
def instagram_auth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')
    expected_state = session.pop('oauth_state', None)

    if not state or not expected_state or state != expected_state:
        # Senior Fix: If user hits 'Back' and is already connected, just go to dashboard
        if session.get('instagram_account_id'):
            return redirect(url_for('instagram_dashboard_page', ig_account_id=session.get('instagram_account_id')))
        return render_template('instagram_index.html', error='CSRF Error. Please try again.'), 400
    if error:
        return render_template('instagram_index.html', error=error_description or error), 400
    if not code:
        return render_template('instagram_index.html', error='Missing Facebook login code. Please click Connect again.'), 400
    try:
        # 1. Exchange code for user access token
        token_data = graph_get('oauth/access_token', {
            'client_id':     META_APP_ID,
            'redirect_uri':  INSTAGRAM_REDIRECT_URI,
            'client_secret': META_APP_SECRET,
            'code':          code
        })
        user_access_token = token_data.get('access_token')
        if not user_access_token:
            raise ValueError('Meta did not return an Instagram access token. Please reconnect and try again.')
        session['user_access_token'] = user_access_token

        businesses = get_user_businesses(user_access_token)
        logger.info(
            "Instagram OAuth retrieved %s businesses from Meta after requesting business_management. business_ids=%s",
            len(businesses),
            [business.get('id') for business in businesses if business.get('id')]
        )
        if not businesses:
            response, _ = get_business_selection_template(
                'instagram',
                [],
                error=NO_BUSINESS_PORTFOLIO_MESSAGE,
                status_code=400
            )
            return response, 400

        return get_business_selection_template('instagram', businesses)
    except requests.HTTPError as e:
        logger.exception("Instagram auth callback token exchange failed.")
        return render_template('instagram_index.html', error=format_oauth_exchange_error(e, 'Instagram')), 400
    except ValueError as e:
        logger.warning("Instagram auth callback validation failed: %s", e)
        return render_template('instagram_index.html', error=str(e)), 400
    except Exception as e:
        logger.exception("IG OAuth error")
        return render_template('instagram_index.html', error='Instagram login failed unexpectedly. Please try connecting again.'), 500

@app.route('/instagram/select-business/<business_id>')
def instagram_select_business(business_id):
    user_token = session.get('user_access_token')
    if not user_token:
        return redirect(url_for('instagram_connect'))

    try:
        business = find_business_or_none(user_token, business_id)
        if not business:
            businesses = get_user_businesses(user_token)
            return get_business_selection_template(
                'instagram',
                businesses,
                error='The selected Business Portfolio was not returned by Meta. Reconnect and select the Business again.',
                status_code=400
            )

        session['selected_business_id'] = business.get('id')
        session['selected_business_name'] = business.get('name') or f"Business {business_id}"
        pages = get_page_assets_for_selected_business(user_token)
        assets = build_instagram_asset_options(pages)
        connectable_count = len([asset for asset in assets if asset.get('connectable')])
        logger.info(
            "Instagram selected business %s returned %s page assets and %s connectable Instagram assets.",
            business_id,
            len(assets),
            connectable_count
        )

        error_msg = None
        if not pages:
            error_msg = 'No owned Facebook Pages were returned for this Business Portfolio. Add a Page to Business Manager or select a different Business.'
        elif connectable_count == 0:
            error_msg = 'This Business Portfolio has no Pages linked to an Instagram Business account. Link Instagram to a Page in Business Settings, then reconnect.'

        return render_template(
            'select_instagram_asset.html',
            business=business,
            assets=assets,
            error=error_msg
        ), 400 if error_msg else 200
    except requests.HTTPError as e:
        logger.exception("Fetching Instagram business assets failed.")
        return get_business_selection_template(
            'instagram',
            get_user_businesses(user_token),
            error=format_oauth_exchange_error(e, 'Instagram'),
            status_code=400
        )
    except Exception:
        logger.exception("Selecting Instagram business %s failed.", business_id)
        return render_template('instagram_index.html', error='Could not load Instagram assets for that Business Portfolio. Please reconnect and try again.'), 500

@app.route('/instagram/connect-page/<page_id>')
def instagram_connect_page(page_id):
    user_token = session.get('user_access_token')
    if not user_token:
        return redirect(url_for('instagram_connect'))

    try:
        pages = get_page_assets_for_selected_business(user_token)
        page_data = next((page for page in pages if page.get('id') == page_id), None)
        business_id, business_name = get_selected_business_context()
        business = {'id': business_id, 'name': business_name} if business_id else None
        assets = build_instagram_asset_options(pages)

        if not page_data:
            return render_template(
                'select_instagram_asset.html',
                business=business,
                assets=assets,
                error='The selected Page was not returned for this Business Portfolio. Select another asset or reconnect.'
            ), 400

        page_token = page_data.get('access_token')
        if not page_token:
            return render_template(
                'select_instagram_asset.html',
                business=business,
                assets=assets,
                error='Meta did not return a Page access token for the selected asset. Reconnect and verify the granted permissions.'
            ), 502

        page_info = graph_get(page_id, {
            'fields': 'instagram_business_account,name',
            'access_token': page_token
        })
        instagram_account = page_info.get('instagram_business_account')
        if not instagram_account or not instagram_account.get('id'):
            return render_template(
                'select_instagram_asset.html',
                business=business,
                assets=assets,
                error='The selected Page is not linked to an Instagram Business account.'
            ), 400

        ig_id = instagram_account.get('id')
        ig_info = graph_get(ig_id, {'fields': 'username', 'access_token': page_token})
        username = ig_info.get('username') or ig_id
        subscribe_page_to_webhook(page_id, page_token)

        session['instagram_account_id'] = ig_id
        session['instagram_username'] = username
        session['instagram_page_token'] = page_token
        session['instagram_page_id'] = page_id

        save_page_token(ig_id, page_token)
        save_instagram_account_context(ig_id, username)

        return render_template(
            'instagram_success.html',
            account_id=ig_id,
            username=username,
            business_id=business_id,
            business_name=business_name,
            page_id=page_id,
            page_name=page_data.get('name')
        )
    except requests.HTTPError as e:
        logger.exception("Connecting Instagram asset for page %s failed.", page_id)
        business_id, business_name = get_selected_business_context()
        pages = get_page_assets_for_selected_business(user_token)
        return render_template(
            'select_instagram_asset.html',
            business={'id': business_id, 'name': business_name} if business_id else None,
            assets=build_instagram_asset_options(pages),
            error=format_oauth_exchange_error(e, 'Instagram')
        ), 400
    except Exception:
        logger.exception("Connecting Instagram asset for page %s failed.", page_id)
        return render_template('instagram_index.html', error='Instagram connection failed unexpectedly. Please reconnect and try again.'), 500

# -----------------------------------------------------------------------------
# WhatsApp routes
# -----------------------------------------------------------------------------

@app.route('/whatsapp/connect')
def whatsapp_connect():
    state = secrets.token_urlsafe(16)
    session['whatsapp_oauth_state'] = state
    redirect_uri = get_whatsapp_redirect_uri()
    whatsapp_app_id = get_whatsapp_app_id()
    if not whatsapp_app_id:
        return render_template('index.html', error='WhatsApp app ID is missing. Set WHATSAPP_APP_ID or META_APP_ID.'), 500
    fb_url = (
        "https://www.facebook.com/v22.0/dialog/oauth"
        f"?client_id={whatsapp_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={WHATSAPP_SCOPES}"
        "&response_type=code"
        "&auth_type=rerequest"
    )
    return redirect(fb_url)

@app.route('/whatsapp/callback')
def whatsapp_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')
    expected_state = session.pop('whatsapp_oauth_state', None)

    if not state or not expected_state or state != expected_state:
        if load_whatsapp_connection():
            return redirect(url_for('whatsapp_dashboard'))
        return render_template('index.html', error='WhatsApp CSRF validation failed. Please try again.'), 400

    if error:
        return render_template('index.html', error=error_description or error), 400
    if not code:
        return render_template('index.html', error='Missing WhatsApp login code. Please click Connect again.'), 400

    try:
        redirect_uri = get_whatsapp_redirect_uri()
        whatsapp_app_id = get_whatsapp_app_id()
        whatsapp_app_secret = get_whatsapp_app_secret()
        if not whatsapp_app_id or not whatsapp_app_secret:
            raise ValueError('WhatsApp app credentials are missing. Set WHATSAPP_APP_ID and WHATSAPP_APP_SECRET for a separate WhatsApp app.')
        token_data = graph_get('oauth/access_token', {
            'client_id': whatsapp_app_id,
            'redirect_uri': redirect_uri,
            'client_secret': whatsapp_app_secret,
            'code': code
        })
        user_access_token = token_data.get('access_token')
        if not user_access_token:
            raise ValueError('Meta did not return a WhatsApp access token.')

        connection = fetch_whatsapp_connection_data(user_access_token)
        session['whatsapp_access_token'] = user_access_token
        save_whatsapp_connection(connection)
        return redirect(url_for('whatsapp_dashboard'))
    except requests.HTTPError as e:
        logger.exception("WhatsApp auth callback token exchange failed.")
        return render_template('index.html', error=format_oauth_exchange_error(e, 'WhatsApp')), 400
    except ValueError as e:
        logger.warning("WhatsApp connection setup failed: %s", e)
        return render_template('index.html', error=str(e)), 400
    except Exception:
        logger.exception("WhatsApp auth callback failed.")
        return render_template('index.html', error='WhatsApp login failed unexpectedly. Please try connecting again.'), 500

@app.route('/whatsapp/dashboard')
def whatsapp_dashboard():
    connection = get_whatsapp_connection()
    if not connection:
        return redirect(url_for('index'))
    messages = load_whatsapp_messages()
    return render_template('whatsapp_dashboard.html', connection=connection, messages=messages)

@app.route('/whatsapp/send', methods=['POST'])
def whatsapp_send():
    connection = get_whatsapp_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No connected WhatsApp Business Account found. Please connect first.'}), 401

    phone_number_id = connection.get('phone_number_id')
    access_token = connection.get('access_token')
    to_number = (request.form.get('to_number') or '').strip()
    message_text = (request.form.get('message') or '').strip()

    if not phone_number_id:
        return jsonify({'success': False, 'error': 'Missing WhatsApp phone number ID in saved connection.'}), 400
    if not access_token:
        return jsonify({'success': False, 'error': 'Missing WhatsApp access token. Please reconnect the account.'}), 401
    if not to_number:
        return jsonify({'success': False, 'error': 'Recipient phone number is required.'}), 400
    if not message_text:
        return jsonify({'success': False, 'error': 'Message text is required.'}), 400

    try:
        result = send_whatsapp_message(phone_number_id, to_number, message_text, access_token)
        return jsonify({'success': True, 'result': result})
    except requests.HTTPError as e:
        raw_error = extract_graph_api_error_payload(e)
        logger.error(
            "WhatsApp send Meta error phone_number_id=%s to=%s payload=%s",
            phone_number_id,
            to_number,
            raw_error
        )
        error_message, status_code = format_graph_api_error(e, 'Failed to send WhatsApp message.')
        return jsonify({'success': False, 'error': error_message, 'meta_error': raw_error}), status_code
    except Exception:
        logger.exception("Unexpected error while sending WhatsApp message.")
        return jsonify({'success': False, 'error': 'Failed to send WhatsApp message.'}), 500

@app.route('/whatsapp/webhook', methods=['GET'])
def whatsapp_webhook_verify():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route('/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook_event():
    data = request.get_json(force=True, silent=True) or {}

    signature = request.headers.get('X-Hub-Signature-256')
    whatsapp_app_secret = get_whatsapp_app_secret()
    if signature and whatsapp_app_secret:
        try:
            expected = 'sha256=' + hmac_module.new(
                whatsapp_app_secret.encode('utf-8'),
                request.data,
                hashlib.sha256
            ).hexdigest()
            if hmac_module.compare_digest(signature, expected):
                logger.info("WhatsApp webhook signature verified.")
            else:
                logger.warning("WhatsApp webhook signature mismatch.")
        except Exception as e:
            logger.error("WhatsApp webhook HMAC verification failed: %s", e)

    try:
        save_json_object(WHATSAPP_WEBHOOK_DEBUG_FILE, {
            'timestamp': time.time(),
            'headers': dict(request.headers),
            'data': data
        })
    except Exception as e:
        logger.error("WhatsApp webhook debug write failed: %s", e)

    logger.info("WhatsApp webhook received: object=%s", data.get('object'))
    inbound_messages = extract_whatsapp_inbound_messages(data)
    if inbound_messages:
        logger.info("WhatsApp inbound messages received: count=%s", len(inbound_messages))
        for msg in inbound_messages:
            logger.info(
                "WhatsApp inbound message received: raw_webhook_id=%s from=%s type=%s",
                msg.get('raw_webhook_id'),
                msg.get('sender_phone_number'),
                msg.get('message_type')
            )
            save_whatsapp_inbound_message(msg)

    return "EVENT_RECEIVED", 200

@app.route('/instagram/webhook', methods=['GET'])
def instagram_webhook_verify():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route('/instagram/webhook', methods=['POST'])
def instagram_webhook_event():
    # Verify HMAC signature
    signature = request.headers.get('X-Hub-Signature-256')
    if signature:
        try:
            expected = 'sha256=' + hmac_module.new(
                META_APP_SECRET.encode('utf-8'),
                request.data,
                hashlib.sha256
            ).hexdigest()
            if not hmac_module.compare_digest(signature, expected):
                logger.warning(f"Signature mismatch! Meta sent {signature}, we expected {expected}")
            else:
                logger.info("✅ Signature verified correctly.")
        except Exception as e:
            logger.error(f"HMAC verification crashed: {e}")
    else:
        logger.warning("No X-Hub-Signature-256 found in headers.")

    data = request.get_json(force=True)
    
    # Store for debug endpoint
    webhook_hits_log.append({
        'endpoint': '/instagram/webhook',
        'timestamp': time.time(),
        'object': data.get('object'),
        'payload': data
    })
    
    last_webhook_info['timestamp'] = time.time()
    last_webhook_info['object_type'] = data.get('object')

    # RAW DEBUG LOGGING — saves every incoming payload for diagnosis
    try:
        with open(WEBHOOK_DEBUG_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'headers': dict(request.headers), 'data': data}, f)
    except Exception as e:
        logger.error(f"Debug write failed: {e}")

    logger.info(f"📥 Instagram Webhook hit — object='{data.get('object')}'")
    
    # Detailed logging for EVERY hit
    for entry in data.get('entry', []):
        entry_id = entry.get('id')
        last_webhook_info['entry_id'] = entry_id
        save_page_webhook_debug(entry_id, '/instagram/webhook', data, dict(request.headers))
        for messaging in entry.get('messaging', []):
            sender_id = messaging.get('sender', {}).get('id')
            last_webhook_info['sender_id'] = sender_id
            
            # CRITICAL META FIX: Ignore echoes (messages sent BY the page/IG account)
            # Both entry_id and instagram_account_id represent 'US'
            my_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
            if sender_id == entry_id or (my_id and sender_id == my_id):
                logger.info(f"⏭️ Skipping webhook echo from ourselves (Sender: {sender_id})")
                continue

            if 'message' in messaging:
                event_type = 'message'
                raw_text = messaging['message'].get('text')
                text = raw_text or '[no text]'
            elif 'read' in messaging:
                event_type = 'read'
                raw_text = None
                text = '[message read]'
            elif 'delivery' in messaging:
                event_type = 'delivery'
                raw_text = None
                text = '[message delivered]'
            else:
                event_type = 'unknown'
                raw_text = None
                text = str(messaging)

            # Save incoming message to UI feed
            save_message({
                'page_id': entry_id,
                'asset_id': entry_id,
                'asset_type': 'instagram',
                'sender_id': sender_id,
                'text': text,
                'event_type': event_type,
                'timestamp': messaging.get('timestamp', int(time.time() * 1000)),
                'source': 'instagram_webhook'
            })

            if event_type != 'message' or not raw_text:
                continue

            save_instagram_message({
                'page_id': entry_id,
                'asset_id': entry_id,
                'asset_type': 'instagram',
                'sender_id': sender_id,
                'text': raw_text,
                'timestamp': messaging.get('timestamp', int(time.time() * 1000)),
                'direction': 'inbound',
                'source': 'instagram_webhook'
            }, ig_account_id=entry_id)
            logger.info(f"✅ Saved inbound message from {sender_id}: '{raw_text}'")

    return "EVENT_RECEIVED", 200

@app.route('/instagram/dashboard')
def instagram_dashboard():
    ig_id = session.get('instagram_account_id')
    if not ig_id:
        return redirect(url_for('instagram_connect'))
    return redirect(url_for('instagram_dashboard_page', ig_account_id=ig_id))

@app.route('/instagram/dashboard/<ig_account_id>')
def instagram_dashboard_page(ig_account_id):
    ig_username = get_saved_instagram_username(ig_account_id) or "Unknown"
    token = get_instagram_page_token(ig_account_id)

    token_error = None
    if token and token.startswith('IGAA'):
        token_error = "CRITICAL: You are using an Instagram Basic Display token. This TOKEN DOES NOT SUPPORT MESSAGING. Please reconnect using the OAuth flow to get a proper Page Access Token (starting with EA...)."
    elif not token:
        token_error = "No Access Token found. Please connect your account first."

    session['instagram_account_id'] = ig_account_id
    session['instagram_username'] = ig_username

    msgs = load_instagram_messages(ig_account_id)
    return render_template('instagram_dashboard.html',
                         username=ig_username,
                         account_id=ig_account_id,
                         messages=msgs,
                         token_error=token_error,
                         last_hit=last_webhook_info)

@app.route('/instagram/comments/<ig_account_id>')
def instagram_comments_page(ig_account_id):
    ig_username = get_saved_instagram_username(ig_account_id) or "Unknown"
    token = get_instagram_page_token(ig_account_id)

    token_error = None
    if token and token.startswith('IGAA'):
        token_error = "CRITICAL: You are using an Instagram Basic Display token. This token cannot manage Instagram comments. Please reconnect using the Page-based OAuth flow."
    elif not token:
        token_error = "No Access Token found. Please connect your account first."

    session['instagram_account_id'] = ig_account_id
    session['instagram_username'] = ig_username

    return render_template(
        'instagram_comments.html',
        username=ig_username,
        account_id=ig_account_id,
        token_error=token_error
    )

@app.route('/api/instagram/comments')
def instagram_comments_api():
    ig_account_id = request.args.get('ig_account_id') or session.get('instagram_account_id')
    if not ig_account_id:
        return jsonify({'success': False, 'error': 'Missing Instagram account ID.'}), 400

    token = get_instagram_page_token(ig_account_id)
    if not token:
        logger.warning("Instagram comments fetch failed: missing token for account %s", ig_account_id)
        return jsonify({'success': False, 'error': 'No Instagram page token found. Please reconnect your account.'}), 401

    try:
        logger.info("Handling /api/instagram/comments for account %s", ig_account_id)
        comments = fetch_instagram_comments(ig_account_id, token)
        if not comments:
            logger.info("No comments found for account %s", ig_account_id)
            return jsonify({'success': True, 'comments': [], 'message': 'No comments found'})
        logger.info("Returning %s comments for account %s", len(comments), ig_account_id)
        return jsonify({'success': True, 'comments': comments})
    except requests.HTTPError as e:
        logger.exception("Meta Graph HTTP error while fetching comments for %s", ig_account_id)
        error_message, status_code = format_graph_api_error(e, 'Failed to fetch Instagram comments.')
        return jsonify({'success': False, 'error': error_message}), status_code
    except requests.Timeout:
        logger.exception("Meta Graph timeout while fetching comments for %s", ig_account_id)
        return jsonify({'success': False, 'error': 'Meta request timed out while fetching Instagram comments.'}), 504
    except Exception:
        logger.exception("Unexpected error while fetching Instagram comments for %s", ig_account_id)
        return jsonify({'success': False, 'error': 'Failed to fetch Instagram comments.'}), 500

@app.route('/api/instagram/reply-comment', methods=['POST'])
def instagram_reply_comment():
    data = request.get_json(silent=True) or request.form
    ig_account_id = data.get('ig_account_id') or session.get('instagram_account_id')
    comment_id = (data.get('comment_id') or '').strip()
    message = (data.get('message') or '').strip()

    if not ig_account_id:
        return jsonify({'success': False, 'error': 'Missing Instagram account ID.'}), 400
    if not comment_id:
        return jsonify({'success': False, 'error': 'Comment ID is required.'}), 400
    if not message:
        return jsonify({'success': False, 'error': 'Reply message is required.'}), 400

    token = get_instagram_page_token(ig_account_id)
    if not token:
        logger.warning("Instagram comment reply failed: missing token for account %s", ig_account_id)
        return jsonify({'success': False, 'error': 'No Instagram page token found. Please reconnect your account.'}), 401

    try:
        result = graph_post(
            f'{comment_id}/replies',
            params={'access_token': token},
            data={'message': message}
        )
        logger.info("Instagram comment reply sent for account %s comment %s", ig_account_id, comment_id)
        return jsonify({'success': True, 'result': result})
    except requests.HTTPError as e:
        error_message, status_code = format_graph_api_error(e, 'Failed to reply to Instagram comment.')
        return jsonify({'success': False, 'error': error_message}), status_code
    except Exception:
        logger.exception("Unexpected error while replying to Instagram comment %s", comment_id)
        return jsonify({'success': False, 'error': 'Failed to reply to Instagram comment.'}), 500

@app.route('/api/instagram/hide-comment', methods=['POST'])
def instagram_hide_comment():
    data = request.get_json(silent=True) or request.form
    ig_account_id = data.get('ig_account_id') or session.get('instagram_account_id')
    comment_id = (data.get('comment_id') or '').strip()

    if not ig_account_id:
        return jsonify({'success': False, 'error': 'Missing Instagram account ID.'}), 400
    if not comment_id:
        return jsonify({'success': False, 'error': 'Comment ID is required.'}), 400

    token = get_instagram_page_token(ig_account_id)
    if not token:
        logger.warning("Instagram hide comment failed: missing token for account %s", ig_account_id)
        return jsonify({'success': False, 'error': 'No Instagram page token found. Please reconnect your account.'}), 401

    try:
        logger.info("Instagram hide comment request account=%s comment_id=%s", ig_account_id, comment_id)
        result = graph_post(
            comment_id,
            params={
                'access_token': token,
                'hide': 'true'
            }
        )
        logger.info("Instagram comment hidden for account %s comment %s", ig_account_id, comment_id)
        return jsonify({'success': True, 'result': result})
    except requests.HTTPError as e:
        raw_error = extract_graph_api_error_payload(e)
        logger.error(
            "Instagram hide comment Meta error account=%s comment_id=%s payload=%s",
            ig_account_id,
            comment_id,
            raw_error
        )
        error_message, status_code = format_graph_api_error(e, 'Failed to hide Instagram comment.')
        return jsonify({'success': False, 'error': error_message, 'meta_error': raw_error}), status_code
    except Exception:
        logger.exception("Unexpected error while hiding Instagram comment %s", comment_id)
        return jsonify({'success': False, 'error': 'Failed to hide Instagram comment.'}), 500

@app.route('/api/instagram/delete-comment', methods=['POST'])
def instagram_delete_comment():
    data = request.get_json(silent=True) or request.form
    ig_account_id = data.get('ig_account_id') or session.get('instagram_account_id')
    comment_id = (data.get('comment_id') or '').strip()

    if not ig_account_id:
        return jsonify({'success': False, 'error': 'Missing Instagram account ID.'}), 400
    if not comment_id:
        return jsonify({'success': False, 'error': 'Comment ID is required.'}), 400

    token = get_instagram_page_token(ig_account_id)
    if not token:
        logger.warning("Instagram delete comment failed: missing token for account %s", ig_account_id)
        return jsonify({'success': False, 'error': 'No Instagram page token found. Please reconnect your account.'}), 401

    try:
        logger.info("Instagram delete comment request account=%s comment_id=%s", ig_account_id, comment_id)
        result = graph_delete(
            comment_id,
            params={'access_token': token}
        )
        logger.info("Instagram comment deleted for account %s comment %s", ig_account_id, comment_id)
        return jsonify({'success': True, 'result': result})
    except requests.HTTPError as e:
        raw_error = extract_graph_api_error_payload(e)
        logger.error(
            "Instagram delete comment Meta error account=%s comment_id=%s payload=%s",
            ig_account_id,
            comment_id,
            raw_error
        )
        error_message, status_code = format_graph_api_error(e, 'Failed to delete Instagram comment.')
        return jsonify({'success': False, 'error': error_message, 'meta_error': raw_error}), status_code
    except Exception:
        logger.exception("Unexpected error while deleting Instagram comment %s", comment_id)
        return jsonify({'success': False, 'error': 'Failed to delete Instagram comment.'}), 500

@app.route('/instagram/send', methods=['POST'])
def instagram_send():
    recipient_psid = request.form.get('recipient_psid')
    message_text = request.form.get('message')
    ig_id = request.form.get('page_id') or session.get('instagram_account_id')
    token = get_instagram_page_token(ig_id)

    if not token:
        return jsonify({'success': False, 'error': 'No page token found'}), 401

    result = send_graph_message(recipient_psid, message_text, token)
    
    if 'message_id' in result:
        save_instagram_message({
            'page_id': ig_id,
            'asset_id': ig_id,
            'sender_id': 'YOU',
            'text': message_text,
            'timestamp': int(time.time() * 1000),
            'direction': 'outbound',
            'source': 'instagram_manual_reply'
        }, ig_account_id=ig_id)
        return jsonify({'success': True, 'result': result})
    return jsonify({'success': False, 'error': result}), 400

@app.route('/api/recent-messages')
def get_recent_messages():
    page_id = request.args.get('page_id')
    logger.info(f"📖 /api/recent-messages called: page_id={page_id}")
    messages = load_messages(page_id)
    logger.info(f"📖 Returning {len(messages)} messages")
    return jsonify(messages)

@app.route('/api/test-save/<page_id>')
def test_save(page_id):
    save_message({
        'page_id': page_id,
        'sender_id': 'TEST',
        'text': 'Test message from /api/test-save',
        'timestamp': int(time.time() * 1000),
        'event_type': 'message',
        'asset_type': 'facebook'
    })
    saved = load_messages(page_id)
    return jsonify({
        'saved_count': len(saved),
        'first_message': saved[0] if saved else None,
        'file': f'messages_{page_id}.json'
    })

@app.route('/api/messages')
def get_messages_api():
    return jsonify(get_recent_global_messages())

@app.route('/api/recent-instagram-messages')
def get_recent_instagram_messages():
    ig_account_id = request.args.get('page_id') or session.get('instagram_account_id')
    return jsonify(load_instagram_messages(ig_account_id))

@app.route('/api/webhook-last-hit')
def get_webhook_last_hit():
    return jsonify(list(webhook_hits_log))

@app.route('/api/debug/<page_id>')
def debug_page(page_id):
    page_token = get_page_token(page_id)
    page_name = get_saved_page_name(page_id) or session.get('connected_page_name') or f'Page {page_id}'
    page_messages = load_messages(page_id)
    global_messages = load_messages()
    page_hit = load_page_webhook_debug(page_id)
    last_hit_matches = bool(last_webhook_info['entry_id'] == page_id)
    if not page_token:
        return jsonify({
            'connected_page_id': page_id,
            'connected_page_name': page_name,
            'subscribed_fields': [],
            'page_token_exists': False,
            'message_count': len(global_messages),
            'page_message_count': len(page_messages),
            'last_entry_id': last_webhook_info['entry_id'],
            'last_object_type': last_webhook_info['object_type'],
            'last_hit_matches_connected_page': last_hit_matches,
            'page_last_webhook_timestamp': (page_hit or {}).get('timestamp'),
            'page_last_webhook_endpoint': (page_hit or {}).get('endpoint'),
            'page_has_webhook_hit': bool(page_hit),
            'warning': 'Page connected, but no webhook received yet for this page.' if not page_hit else None,
            'error': 'No token saved for this page_id. Reconnect via OAuth.'
        })
    try:
        apps_data = graph_get(f'{page_id}/subscribed_apps', {
            'access_token': page_token
        })
        subscribed_fields = []
        for app_item in apps_data.get('data', []):
            subscribed_fields = app_item.get('subscribed_fields', [])
        
        return jsonify({
            'connected_page_id': page_id,
            'connected_page_name': page_name,
            'subscribed_fields': subscribed_fields,
            'is_subscribed': len(subscribed_fields) > 0,
            'page_token_exists': True,
            'message_count': len(global_messages),
            'page_message_count': len(page_messages),
            'last_entry_id': last_webhook_info['entry_id'],
            'last_object_type': last_webhook_info['object_type'],
            'last_hit_matches_connected_page': last_hit_matches,
            'page_last_webhook_timestamp': (page_hit or {}).get('timestamp'),
            'page_last_webhook_endpoint': (page_hit or {}).get('endpoint'),
            'page_has_webhook_hit': bool(page_hit),
            'warning': 'Page connected, but no webhook received yet for this page.' if not page_hit else None,
            'subscription_error': None
        })
    except Exception as e:
        return jsonify({
            'connected_page_id': page_id,
            'connected_page_name': page_name,
            'subscribed_fields': [],
            'page_token_exists': True,
            'message_count': len(global_messages),
            'page_message_count': len(page_messages),
            'last_entry_id': last_webhook_info['entry_id'],
            'last_object_type': last_webhook_info['object_type'],
            'last_hit_matches_connected_page': last_hit_matches,
            'page_last_webhook_timestamp': (page_hit or {}).get('timestamp'),
            'page_last_webhook_endpoint': (page_hit or {}).get('endpoint'),
            'page_has_webhook_hit': bool(page_hit),
            'warning': 'Page connected, but no webhook received yet for this page.' if not page_hit else None,
            'subscription_error': str(e)
        })

@app.route('/api/page-webhook-status/<page_id>')
def page_webhook_status(page_id):
    page_hit = load_page_webhook_debug(page_id)
    return jsonify({
        'page_id': page_id,
        'has_webhook_hit': bool(page_hit),
        'last_hit': page_hit,
        'page_message_count': len(load_messages(page_id)),
        'matches_last_global_hit': bool(last_webhook_info['entry_id'] == page_id)
    })

@app.route('/api/messenger-debug')
def messenger_debug():
    page_id = request.args.get('page_id') or session.get('connected_page_id')
    page_name = get_saved_page_name(page_id)
    user_token = session.get('user_access_token')
    token = get_connected_page_token(page_id)

    debug_info = {
        'connected_page_id': page_id,
        'connected_page_name': page_name,
        'has_saved_page_token': bool(token),
        'message_count': len(get_recent_global_messages()),
        'page_message_count': len(get_messages_for_page(page_id)),
        'last_webhook_hit_timestamp': last_webhook_info['timestamp'],
        'last_object_type': last_webhook_info['object_type'],
        'last_entry_id': last_webhook_info['entry_id'],
        'last_sender_id': last_webhook_info['sender_id'],
        'last_hit_matches_connected_page': bool(page_id and last_webhook_info['entry_id'] == page_id),
        'is_subscribed': None,
        'subscribed_fields': [],
        'subscription_error': None
    }

    if not page_id:
        return jsonify(debug_info)

    try:
        page_token = token
        if user_token and not page_token:
            pages = get_user_pages(user_token)
            page_data = next((page for page in pages if page.get('id') == page_id), None)
            page_token = (page_data or {}).get('access_token')

        if page_token:
            subs = graph_get(f'{page_id}/subscribed_apps', {'access_token': page_token})
            subscribed_fields = []
            for sub in subs.get('data', []):
                subscribed_fields = sub.get('subscribed_fields', [])

            debug_info['is_subscribed'] = len(subscribed_fields) > 0
            debug_info['subscribed_fields'] = subscribed_fields

        else:
            debug_info['subscription_error'] = 'No page access token found for the connected page.'
    except Exception as e:
        debug_info['subscription_error'] = str(e)

    return jsonify(debug_info)

@app.route('/api/page-user-content')
def page_user_content_api():
    page_id = request.args.get('page_id') or session.get('connected_page_id')
    page_token = get_connected_page_token(page_id)

    if not page_id:
        return jsonify({'success': False, 'error': 'No connected page_id was provided.'}), 400
    if not page_token:
        return jsonify({'success': False, 'error': 'No connected page token found. Please reconnect the page.'}), 401

    try:
        content = fetch_page_user_content(page_id, page_token)
        page_name = get_saved_page_name(page_id) or f'Page {page_id}'
        return jsonify({
            'success': True,
            'page_id': page_id,
            'page_name': page_name,
            'items': content,
            'comments': build_page_comment_moderation_items(content, page_id, page_name),
            'permission_used': 'pages_read_user_content',
            'graph_edge': f'/{page_id}/feed',
            'synced_at': int(time.time())
        })
    except requests.HTTPError as e:
        message, status_code = format_graph_api_error(
            e,
            'Could not read Page user content from Meta.'
        )
        return jsonify({
            'success': False,
            'error': message,
            'details': extract_graph_api_error_message(e),
            'permission_used': 'pages_read_user_content',
            'raw_graph_error': extract_graph_api_error_payload(e)
        }), status_code
    except Exception as e:
        logger.exception("Reading Page user content failed for page %s.", page_id)
        return jsonify({
            'success': False,
            'error': 'Could not read Page user content.',
            'details': str(e),
            'permission_used': 'pages_read_user_content'
        }), 500

@app.route('/api/instagram-debug')
def instagram_debug():
    ig_account_id = request.args.get('page_id') or session.get('instagram_account_id')
    msgs = load_instagram_messages(ig_account_id)
    return jsonify({
        'last_webhook_hit_timestamp': last_webhook_info['timestamp'],
        'last_object_type': last_webhook_info['object_type'],
        'last_entry_id': last_webhook_info['entry_id'],
        'last_hit_matches_current_account': bool(ig_account_id and last_webhook_info['entry_id'] == ig_account_id),
        'message_count': len(msgs),
        'last_3_raw_messages': msgs[:3]
    })

@app.route('/api/config')
def get_config():
    return jsonify(load_config())

@app.route('/api/webhook-debug')
def get_webhook_debug():
    if not os.path.exists(WEBHOOK_DEBUG_FILE):
        return jsonify({'error': 'No debug logs found yet. Webhook hasn\'t been hit.'})
    try:
        with open(WEBHOOK_DEBUG_FILE, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/check-subscription')
def check_subscription():
    # CRITICAL: me/accounts requires a USER access token, NOT a page/IG token
    user_token = session.get('user_access_token')
    
    if not user_token:
        return jsonify({
            'success': False, 
            'error': 'No user session found. You MUST reconnect via the OAuth button — manually pasting an IGAA token does not work for this check.'
        })
    
    # Detect wrong token type early
    if user_token.startswith('IGAA'):
        return jsonify({
            'success': False,
            'error': 'Wrong token type (IGAA = Basic Display). You must reconnect via the Instagram OAuth flow to get an EAA... Page Access Token.'
        })
    
    try:
        # me/accounts returns all Facebook Pages the user manages
        pages_data = graph_get('me/accounts', {'access_token': user_token})
        page_status = []
        
        for page in pages_data.get('data', []):
            p_id = page.get('id')
            p_token = page.get('access_token')
            # Check what fields this page is subscribed to
            try:
                subs = graph_get(f'{p_id}/subscribed_apps', {'access_token': p_token})
                subscribed_fields = []
                for sub in subs.get('data', []):
                    subscribed_fields = sub.get('subscribed_fields', [])
                page_status.append({
                    'page_name': page.get('name'),
                    'page_id': p_id,
                    'subscribed_fields': subscribed_fields,
                    'is_subscribed': len(subscribed_fields) > 0
                })
            except Exception as sub_err:
                page_status.append({
                    'page_name': page.get('name'),
                    'page_id': p_id,
                    'subscribed_fields': [],
                    'is_subscribed': False,
                    'error': str(sub_err)
                })
            
        return jsonify({'success': True, 'pages_found': len(page_status), 'data': page_status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/send-message', methods=['POST'])
def send_message():
    recipient_id = request.form.get('recipient_id')
    message_text = request.form.get('message')
    page_id = request.form.get('page_id') or session.get('connected_page_id')
    token = get_connected_page_token(page_id)

    if not token:
        return jsonify({'success': False, 'error': 'No connected page token found. Please reconnect the page.'}), 401

    result = send_graph_message(recipient_id, message_text, token)
    if 'message_id' in result:
        save_message({
            'page_id': page_id,
            'asset_id': page_id,
            'asset_type': 'page',
            'sender_id': 'MANUAL_REPLY',
            'text': f"{message_text} (ID: {result['message_id']})",
            'is_reply': True,
            'timestamp': int(time.time() * 1000),
            'source': 'messenger_manual_reply'
        })
        return jsonify({'success': True, 'result': result})
    return jsonify({'success': False, 'error': result}), 400

# -----------------------------------------------------------------------------
# Messenger and Instagram webhook handlers
# -----------------------------------------------------------------------------
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
    data = request.get_json(force=True)

    # RAW DEBUG — also log here so we can see if Instagram DMs arrive at this endpoint
    # Store for debug endpoint
    webhook_hits_log.append({
        'endpoint': '/webhook',
        'timestamp': time.time(),
        'object': data.get('object'),
        'payload': data
    })

    try:
        with open(WEBHOOK_DEBUG_FILE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'endpoint': '/webhook',
                'headers': dict(request.headers),
                'data': data
            }, f)
    except Exception as e:
        logger.error(f"Messenger debug write failed: {e}")
    
    last_webhook_info['timestamp'] = time.time()
    last_webhook_info['object_type'] = data.get('object')

    # Verify HMAC signature (non-blocking)
    signature = request.headers.get('X-Hub-Signature-256')
    if signature:
        try:
            expected = 'sha256=' + hmac_module.new(
                META_APP_SECRET.encode('utf-8'),
                request.data,
                hashlib.sha256
            ).hexdigest()
            if hmac_module.compare_digest(signature, expected):
                logger.info("✅ /webhook Signature verified.")
            else:
                logger.warning(f"/webhook Signature mismatch! Meta: {signature}, Expected: {expected}")
        except Exception as e:
            logger.error(f"/webhook HMAC error: {e}")

    logger.info(f"📥 /webhook hit — object='{data.get('object')}'")

    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            page_id = entry.get('id')
            last_webhook_info['entry_id'] = page_id
            save_page_webhook_debug(page_id, '/webhook', data, dict(request.headers))
            handled_entry = False

            for channel_name, source_name in (
                ('messaging', 'messenger_webhook'),
                ('standby', 'messenger_standby')
            ):
                for event in entry.get(channel_name, []):
                    handled_entry = True
                    sender_id = event.get('sender', {}).get('id')
                    last_webhook_info['sender_id'] = sender_id

                    # Skip echo: only filter if sender is the page itself (page echoing its own messages)
                    if sender_id == page_id:
                        logger.info("Skipping Messenger echo from page itself: %s", sender_id)
                        continue

                    if 'message' in event:
                        event_type = 'message'
                        raw_text = event['message'].get('text')
                        text = raw_text or '[no text]'
                    elif 'read' in event:
                        event_type = 'read'
                        raw_text = None
                        text = '[message read]'
                    elif 'delivery' in event:
                        event_type = 'delivery'
                        raw_text = None
                        text = '[message delivered]'
                    else:
                        event_type = 'unknown'
                        raw_text = None
                        text = str(event)

                    ts = event.get('timestamp', int(time.time() * 1000))
                    save_message({
                        'page_id': page_id,
                        'asset_id': page_id,
                        'asset_type': 'facebook',
                        'sender_id': sender_id,
                        'text': text,
                        'event_type': event_type,
                        'timestamp': ts,
                        'source': source_name
                    })

                    if event_type != 'message' or not raw_text:
                        continue

                    logger.info("Saved %s message from %s for page %s", source_name, sender_id, page_id)

            if handled_entry:
                continue
        return "EVENT_RECEIVED", 200

    # Also handle instagram object type here (fallback)
    if data.get('object') == 'instagram':
        for entry in data.get('entry', []):
            entry_id = entry.get('id')
            last_webhook_info['entry_id'] = entry_id
            save_page_webhook_debug(entry_id, '/webhook', data, dict(request.headers))
            for messaging in entry.get('messaging', []):
                sender_id = messaging.get('sender', {}).get('id')
                last_webhook_info['sender_id'] = sender_id
                if 'message' in messaging:
                    event_type = 'message'
                    raw_text = messaging['message'].get('text')
                    text = raw_text or '[no text]'
                elif 'read' in messaging:
                    event_type = 'read'
                    raw_text = None
                    text = '[message read]'
                elif 'delivery' in messaging:
                    event_type = 'delivery'
                    raw_text = None
                    text = '[message delivered]'
                else:
                    event_type = 'unknown'
                    raw_text = None
                    text = str(messaging)

                if sender_id:
                    save_message({
                        'page_id': entry_id,
                        'asset_id': entry_id,
                        'asset_type': 'instagram',
                        'sender_id': sender_id,
                        'text': text,
                        'event_type': event_type,
                        'timestamp': messaging.get('timestamp', int(time.time() * 1000)),
                        'source': 'messenger_webhook_ig'
                    })
                    if event_type == 'message' and raw_text:
                        msg_ts = messaging.get('timestamp', int(time.time() * 1000))
                        save_instagram_message({
                            'page_id': entry_id,
                            'asset_id': entry_id,
                            'asset_type': 'instagram',
                            'sender_id': sender_id,
                            'text': raw_text,
                            'timestamp': msg_ts,
                            'direction': 'inbound',
                            'source': 'messenger_webhook_ig'
                        }, ig_account_id=entry_id)
                    logger.info(f"✅ Saved Instagram event from {sender_id}: {event_type}")
        return "EVENT_RECEIVED", 200
    return "IGNORED", 200

# -----------------------------------------------------------------------------
# Compliance endpoints
# -----------------------------------------------------------------------------
@app.route('/instagram/deauth', methods=['POST'])
def instagram_deauth():
    """Facebook/Instagram App Deauthorization Callback"""
    logger.warning("App deauthorized by a user.")
    return jsonify({'success': True}), 200

@app.route('/instagram/data-deletion', methods=['POST'])
def instagram_data_deletion():
    """Facebook/Instagram Data Deletion Request Callback"""
    logger.warning("Data deletion requested.")
    # In a real app, you would handle the deletion logic here
    # and return a confirmation code/URL
    return jsonify({
        'url': 'https://messenger-integration.nanovate.io/instagram/data-deletion-status',
        'confirmation_code': str(uuid.uuid4())
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
