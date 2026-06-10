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
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE) as f: return json.load(f)

def save(records):
    with open(DATA_FILE,'w') as f: json.dump(records,f,ensure_ascii=False)

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    records = load()
    today = datetime.date.today().isoformat()

    if text == '查詢' or text == '本月':
        now = datetime.date.today()
        month = now.strftime('%Y-%m')
        monthly = [r for r in records if r['date'].startswith(month)]
        income = sum(r['amount'] for r in monthly if r['type']=='收入')
        expense = sum(r['amount'] for r in monthly if r['type']=='支出')
        if not monthly:
            reply = '本月還沒有記錄！\n\n記錄格式：\n支出 金額 分類 備註\n例如：支出 100 餐飲 午餐'
        else:
            details = '\n'.join([f"{'➕' if r['type']=='收入' else '➖'}{r['type']} ${r['amount']} {r['category']} {r['note']} ({r['date']})" for r in monthly[-10:]])
            reply = f"📊 {now.month}月收支\n收入：${income}\n支出：${expense}\n結餘：${income-expense}\n\n最近記錄：\n{details}"
    elif text.startswith('支出') or text.startswith('收入'):
        parts = text.split()
        if len(parts) < 3:
            reply = '格式錯誤！\n請輸入：支出 金額 分類 備註\n例如：支出 100 餐飲 午餐'
        else:
            try:
                rtype = parts[0]
                amount = int(parts[1])
                category = parts[2]
                note = parts[3] if len(parts)>3 else ''
                records.append({'type':rtype,'amount':amount,'category':category,'note':note,'date':today})
                save(records)
                reply = f"✅ 已記錄！\n{rtype} ${amount}\n分類：{category}\n備註：{note}\n日期：{today}"
            except:
                reply = '金額請輸入數字！\n例如：支出 100 餐飲 午餐'
    elif text == '說明' or text == '幫助':
        reply = '📖 使用說明\n\n記錄支出：\n支出 金額 分類 備註\n例：支出 100 餐飲 午餐\n\n記錄收入：\n收入 金額 分類 備註\n例：收入 30000 薪資\n\n查看本月：\n輸入「查詢」或「本月」'
    else:
        reply = '👋 你好！我是記帳小幫手\n\n輸入「說明」查看使用方式'

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
