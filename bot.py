import os
import time
import json
import random
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

# ====================== SIMULATION CONFIG ======================
DATA_FILE = "simulation.json"
WHALES = [
    "0xa5ea13a81d2b7e8e424b182bdc1db08e756bd96a",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",
    "0x9f2fe025f84839ca81dd8e0338892605702d2ca8",
    "0x492442eab586f242b53bda933fd5de859c8a3782",
    "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee",
    "0x204f72f35326db932158cba6adff0b9a1da95e14",
    "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",
    "0x241f846866c2de4fb67cdb0ca6b963d85e56ef50",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2"
]
MIN_SIZE = 20

# Load simulation data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"balance": 500.0, "trades": []}

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
running = True
seen = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("▶️ Start", callback_data="start"),
         InlineKeyboardButton("⏹️ Stop", callback_data="stop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🦈 Whale Copier Bot\nFake $500 Account • 5% Sizing", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global running

    if query.data == "status":
        copy_size = min(data["balance"] * 0.05, 100)
        await query.edit_message_text(
            f"📊 **Simulated Balance**\n"
            f"Balance: **${data['balance']:.2f}**\n"
            f"Copy Size: **${copy_size:.2f}**\n"
            f"Status: {'🟢 RUNNING' if running else '⭕ STOPPED'}"
        )
    elif query.data == "history":
        msg = "📜 Last trades:\n\n"
        for t in data["trades"][-5:]:
            msg += f"{t['timestamp']} | {t['market']} | ${t['amount']:.2f} | {t['result']} (${t['pnl']:.2f})\n"
        await query.edit_message_text(msg if data["trades"] else "No trades yet.")
    elif query.data == "start":
        running = True
        await query.edit_message_text("🚀 Simulation Started")
    elif query.data == "stop":
        running = False
        await query.edit_message_text("⏹️ Simulation Stopped")

def polling_loop():
    global running
    while True:
        if not running:
            time.sleep(5)
            continue
        try:
            for whale in WHALES:
                r = requests.get(f"https://data-api.polymarket.com/trades?user={whale}&limit=8", timeout=10)
                if not r.ok: continue
                for trade in r.json():
                    tid = trade.get("id") or trade.get("tx_hash")
                    if tid in seen: continue
                    if trade.get("side") == "BUY" and float(trade.get("size", 0)) >= MIN_SIZE:
                        amt = min(data["balance"] * 0.05, 100)
                        market = trade.get("market_slug", "unknown")
                        
                        is_win = random.random() < 0.60
                        pnl = round(amt * (0.25 if is_win else -0.75), 2)
                        data["balance"] = round(data["balance"] + pnl, 2)
                        
                        data["trades"].append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "market": market,
                            "amount": amt,
                            "result": "WIN" if is_win else "LOSS",
                            "pnl": pnl
                        })
                        with open(DATA_FILE, "w") as f:
                            json.dump(data, f)
                        
                        msg = f"🟢 SIMULATED COPY\nMarket: {market}\nAmount: ${amt:.2f}\nResult: { 'WIN' if is_win else 'LOSS'} (${pnl})\nBalance: ${data['balance']:.2f}"
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                        seen.add(tid)
            time.sleep(12)
        except:
            time.sleep(10)

if __name__ == "__main__":
    print("🚀 Starting Telegram Whale Bot...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    
    import threading
    threading.Thread(target=polling_loop, daemon=True).start()
    
    app.run_polling()