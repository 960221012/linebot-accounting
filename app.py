from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os, json, datetime

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
DATA_FILE = 'records.json'

def load():
    if not os.path.exists(DATA_FILE):
        return {'records': [], 'installments': [], 'card_due': 15}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def reply_text(event, msg):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    data = load()
    records = data.get('records', [])
    installments = data.get('installments', [])
    today = datetime.date.today().isoformat()
    now = datetime.date.today()
    month = now.strftime('%Y-%m')

    if text == '說明' or text == '幫助':
        msg = '📖 使用說明\n\n💰 記帳\n支出 金額 分類 備註\n收入 金額 分類 備註\n\n💳 分期\n分期 名稱 總額 期數\n繳期 名稱\n分期查詢\n\n📅 繳費日 15\n\n📊 查詢'
        reply_text(event, msg)

    elif text.startswith('支出') or text.startswith('收入'):
        parts = text.split()
        if len(parts) < 3:
            reply_text(event, '格式：支出 金額 分類 備註\n例：支出 100 餐飲 午餐')
            return
        try:
            rtype = parts[0]
            amount = int(parts[1])
            category = parts[2]
            note = parts[3] if len(parts) > 3 else ''
            records.append({'type': rtype, 'amount': amount, 'category': category, 'note': note, 'date': today})
            data['records'] = records
            save(data)
            reply_text(event, f'✅ 已記錄\n{rtype} ${amount} {category} {note}')
        except:
            reply_text(event, '金額請輸入數字！')

    elif text.startswith('分期') and text != '分期查詢':
        parts = text.split()
        if len(parts) < 4:
            reply_text(event, '格式：分期 名稱 總額 期數\n例：分期 iPhone 30000 12')
            return
        try:
            name = parts[1]
            total = int(parts[2])
            months = int(parts[3])
            per_month = round(total / months)
            installments.append({'name': name, 'total': total, 'months': months, 'paid': 0, 'per_month': per_month, 'start': today})
            data['installments'] = installments
            save(data)
            reply_text(event, f'✅ 分期已記錄\n{name} 共{months}期\n每月 ${per_month}')
        except:
            reply_text(event, '格式錯誤！例：分期 iPhone 30000 12')

    elif text == '分期查詢':
        active = [i for i in installments if i['paid'] < i['months']]
        if not active:
            reply_text(event, '目前沒有進行中的分期')
            return
        lines = ['📋 分期明細\n']
        total_monthly = 0
        for i in active:
            remaining = i['months'] - i['paid']
            total_monthly += i['per_month']
            lines.append(f"🔸 {i['name']}\n每月${i['per_month']} 剩{remaining}期\n還需付${i['per_month']*remaining}\n")
        lines.append(f'💳 本月分期合計：
