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
SIMULATED_BALANCE = 500.0
COPY_PERCENT = 0.05
MAX_PER_TRADE = 100

# Load or create simulation data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"balance": SIMULATED_BALANCE, "trades": []}

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
running = True
seen = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("▶️ Start Bot", callback_data="start"),
         InlineKeyboardButton("⏹️ Stop Bot", callback_data="stop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🦈 Whale Copier Bot with Simulation\nFake $500 account • 5% sizing", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global running

    if query.data == "status":
        copy_size = min(data["balance"] * COPY_PERCENT, MAX_PER_TRADE)
        await query.edit_message_text(
            f"📊 **Simulated Account**\n"
            f"Balance: **${data['balance']:.2f}**\n"
            f"Copy Size: **${copy_size:.2f}**\n"
            f"Bot: {'🟢 RUNNING' if running else '⭕ STOPPED'}\n"
            f"Watching 10 whales"
        )
    elif query.data == "history":
        if data["trades"]:
            msg = "📜 Last 5 simulated trades:\n\n"
            for t in data["trades"][-5:]:
                msg += f"{t['timestamp']} | {t['market']} | ${t['amount']:.2f} | {t['result']} (${t['pnl']:.2f})\n"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("No trades yet. Bot is watching whales...")
    elif query.data == "start":
        running = True
        await query.edit_message_text("🚀 Bot Started (simulation active)")
    elif query.data == "stop":
        running = False
        await query.edit_message_text("⏹️ Bot Stopped")

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def polling_loop():
    global running
    while True:
        if not running:
            time.sleep(5)
            continue
        try:
            for whale in WHALES:
                r = requests.get(f"https://data-api.polymarket.com/trades?user={whale}&limit=8")
                if not r.ok: continue
                for trade in r.json():
                    tid = trade.get("id") or trade.get("tx_hash")
                    if tid in seen: continue
                    if trade.get("side") == "BUY" and float(trade.get("size", 0)) >= MIN_SIZE:
                        amt = min(data["balance"] * COPY_PERCENT, MAX_PER_TRADE)
                        market = trade.get("market_slug", "unknown")
                        
                        # Simulate realistic result
                        is_win = random.random() < 0.60
                        pnl = round(amt * (0.25 if is_win else -0.75), 2)
                        data["balance"] = round(data["balance"] + pnl, 2)
                        
                        trade_entry = {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "market": market,
                            "amount": amt,
                            "result": "WIN" if is_win else "LOSS",
                            "pnl": pnl
                        }
                        data["trades"].append(trade_entry)
                        save_data()
                        
                        msg = f"🟢 SIMULATED COPY!\nMarket: {market}\nAmount: ${amt:.2f}\nResult: {trade_entry['result']} (${pnl:.2f})\nNew Balance: ${data['balance']:.2f}"
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                        seen.add(tid)
            time.sleep(12)
        except:
            time.sleep(10)

if __name__ == "__main__":
    print("🚀 Starting Telegram Whale Bot with Full Simulation...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    
    import threading
    threading.Thread(target=polling_loop, daemon=True).start()
    
    app.run_polling()