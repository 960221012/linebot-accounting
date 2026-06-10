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
    if not os.path.exists(DATA_FILE): return {'records':[],'installments':[],'card_due':15}
    with open(DATA_FILE) as f: return json.load(f)

def save(data):
    with open(DATA_FILE,'w') as f: json.dump(data,f,ensure_ascii=False)

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
    data = load()
    records = data.get('records',[])
    installments = data.get('installments',[])
    today = datetime.date.today().isoformat()
    now = datetime.date.today()
    month = now.strftime('%Y-%m')

    # 記錄支出/收入
    if text.startswith('支出') or text.startswith('收入'):
        parts = text.split()
        if len(parts) < 3:
            reply = '格式：支出 金額 分類 備註\n例：支出 100 餐飲 午餐'
        else:
            try:
                rtype = parts[0]
                amount = int(parts[1])
                category = parts[2]
                note = parts[3] if len(parts)>3 else ''
                records.append({'type':rtype,'amount':amount,'category':category,'note':note,'date':today})
                data['records'] = records
                save(data)
                reply = f"✅ 已記錄！\n{rtype} ${amount}\n分類：{category}\n備註：{note}"
            except:
                reply = '金額請輸入數字！'

    # 新增分期
    elif text.startswith('分期'):
        parts = text.split()
        if len(parts) < 4:
            reply = '格式：分期 商品名稱 總金額 期數\n例：分期 iPhone 30000 12'
        else:
            try:
                name = parts[1]
                total = int(parts[2])
                months = int(parts[3])
                per_month = round(total / months)
                installments.append({
                    'name': name,
                    'total': total,
                    'months': months,
                    'paid': 0,
                    'per_month': per_month,
                    'start': today
                })
                data['installments'] = installments
                save(data)
                reply = f"✅ 分期已記錄！\n商品：{name}\n總金額：${total}\n期數：{months}期\n每月：${per_month}"
            except:
                reply = '格式錯誤！\n例：分期 iPhone 30000 12'

    # 查詢分期
    elif text == '分期查詢' or text == '我的分期':
        active = [i for i in installments if i['paid'] < i['months']]
        if not active:
            reply = '目前沒有進行中的分期 😊'
        else:
            lines = ['📋 分期明細：\n']
            total_monthly = 0
            for i in active:
                remaining = i['months'] - i['paid']
                total_monthly += i['per_month']
                lines.append(f"🔸 {i['name']}\n   每月 ${i['per_month']}｜剩 {remaining} 期\n   還需付 ${i['per_month']*remaining}")
            lines.append(f"\n💳 本月分期合計：${total_monthly}")
            reply = '\n'.join(lines)

    # 繳一期
    elif text.startswith('繳期'):
        parts = text.split()
        if len(parts) < 2:
            reply = '格式：繳期 商品名稱\n例：繳期 iPhone'
        else:
            name = parts[1]
            found = False
            for i in installments:
                if i['name'] == name and i['paid'] < i['months']:
                    i['paid'] += 1
                    found = True
                    remaining = i['months'] - i['paid']
                    reply = f"✅ {name} 已繳第 {i['paid']} 期\n剩餘 {remaining} 期"
                    break
            if not found:
                reply = f'找不到「{name}」的分期記錄'
            data['installments'] = installments
            save(data)

    # 設定繳費日
    elif text.startswith('繳費日'):
        parts = text.split()
        if len(parts) < 2:
