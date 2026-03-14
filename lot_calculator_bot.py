import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8781866071:AAED1SXfMvrMzj3BjR6xhV5UWnftcOy05KI"
logging.basicConfig(level=logging.INFO)

# Состояния диалога
CHOOSE_PAIR, CHOOSE_LEVERAGE, ENTER_DEPOSIT, CHOOSE_RISK, ENTER_SL = range(5)

PAIR_INFO = {
    "EURUSD": {
        "emoji": "🇪🇺",
        "pip_value": 10.0,
        "pip_desc": "1 пип = 0.0001",
        "example_sl": "10–20 пипов",
        "contract_size": 100_000,
        "price_approx": 1.1,
        "default_lev": 100,
        "lev_options": [50, 100, 200, 500],
    },
    "GBPUSD": {
        "emoji": "🇬🇧",
        "pip_value": 10.0,
        "pip_desc": "1 пип = 0.0001",
        "example_sl": "15–30 пипов",
        "contract_size": 100_000,
        "price_approx": 1.27,
        "default_lev": 200,
        "lev_options": [50, 100, 200, 500],
    },
    "XAUUSD": {
        "emoji": "🥇",
        "pip_value": 1.0,
        "pip_desc": "1 пип = $0.01 (золото)",
        "example_sl": "100–300 пипов",
        "contract_size": 100,
        "price_approx": 2000.0,
        "default_lev": 20,
        "lev_options": [5, 10, 15, 20, 50, 100],
    },
}


# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("🥇 XAUUSD — 1:20",   callback_data="pair_XAUUSD")],
        [InlineKeyboardButton("🇪🇺 EURUSD — 1:100", callback_data="pair_EURUSD"),
         InlineKeyboardButton("🇬🇧 GBPUSD — 1:200", callback_data="pair_GBPUSD")],
    ]
    await update.message.reply_text(
        "👋 *Лот Калькулятор*\n\n"
        "Дефолтные плечи:\n"
        "• 🥇 XAUUSD → *1:20*\n"
        "• 🇪🇺 EURUSD → *1:100*\n"
        "• 🇬🇧 GBPUSD → *1:200*\n\n"
        "Выберите пару:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return CHOOSE_PAIR


# Выбор пары
async def choose_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pair = q.data.replace("pair_", "")
    context.user_data["pair"] = pair
    info = PAIR_INFO[pair]
    context.user_data["leverage"] = info["default_lev"]
    kb = [
        [InlineKeyboardButton(f"✅ Использовать 1:{info['default_lev']}", callback_data="lev_use_default")],
        [InlineKeyboardButton("⚙️ Изменить плечо", callback_data="lev_change")],
    ]
    await q.edit_message_text(
        f"{info['emoji']} Пара: *{pair}*\n"
        f"⚙️ Плечо по умолчанию: *1:{info['default_lev']}*\n\n"
        "Продолжить или изменить плечо?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return CHOOSE_LEVERAGE


# Использовать дефолтное плечо
async def use_default_lev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pair = context.user_data["pair"]
    lev  = context.user_data["leverage"]
    info = PAIR_INFO[pair]
    await q.edit_message_text(
        f"{info['emoji']} *{pair}* | Плечо: *1:{lev}*\n\n"
        "💵 Введите размер депозита в USD:\n"
        "_(например: 400, 1000, 10000)_",
        parse_mode="Markdown",
    )
    return ENTER_DEPOSIT


# Показать список плеч
async def show_lev_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pair    = context.user_data["pair"]
    info    = PAIR_INFO[pair]
    options = info["lev_options"]
    buttons = [InlineKeyboardButton(f"1:{l}", callback_data=f"lev_{l}") for l in options]
    kb_rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    await q.edit_message_text(
        f"{info['emoji']} *{pair}* — выберите плечо:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )
    return CHOOSE_LEVERAGE


# Установить выбранное плечо
async def set_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lev = int(q.data.replace("lev_", ""))
    context.user_data["leverage"] = lev
    pair = context.user_data["pair"]
    info = PAIR_INFO[pair]
    await q.edit_message_text(
        f"{info['emoji']} *{pair}* | Плечо: *1:{lev}*\n\n"
        "💵 Введите размер депозита в USD:\n"
        "_(например: 400, 1000, 10000)_",
        parse_mode="Markdown",
    )
    return ENTER_DEPOSIT


# Ввод депозита
async def enter_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        deposit = float(text)
        if deposit <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректное число. Например: *1000*", parse_mode="Markdown")
        return ENTER_DEPOSIT
    context.user_data["deposit"] = deposit
    kb = [
        [InlineKeyboardButton("1% риск",   callback_data="risk_1"),
         InlineKeyboardButton("1.5% риск", callback_data="risk_1.5"),
         InlineKeyboardButton("2% риск",   callback_data="risk_2")],
        [InlineKeyboardButton("✏️ Свой %", callback_data="risk_custom")],
    ]
    await update.message.reply_text(
        f"✅ Депозит: *${deposit:,.2f}*\n\n"
        "📊 Выберите *риск на сделку*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return CHOOSE_RISK


# Выбор риска (кнопка)
async def choose_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    risk_data = q.data.replace("risk_", "")
    if risk_data == "custom":
        context.user_data["awaiting_custom_risk"] = True
        await q.edit_message_text("✏️ Введите риск в % (например: *0.5* или *3*):", parse_mode="Markdown")
        return CHOOSE_RISK
    context.user_data["risk_pct"] = float(risk_data)
    context.user_data["awaiting_custom_risk"] = False
    pair = context.user_data["pair"]
    info = PAIR_INFO[pair]
    await q.edit_message_text(
        f"✅ Риск: *{risk_data}%*\n\n"
        f"📏 Введите *Stop Loss в пипах*:\n"
        f"_{info['pip_desc']}_\n"
        f"_Обычно для {pair}: {info['example_sl']}_",
        parse_mode="Markdown",
    )
    return ENTER_SL


# Выбор риска (текст — свой %)
async def choose_risk_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_custom_risk"):
        return CHOOSE_RISK
    text = update.message.text.strip().replace(",", ".")
    try:
        risk_pct = float(text)
        if risk_pct <= 0 or risk_pct > 20:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите число от 0.1 до 20. Например: *1.5*", parse_mode="Markdown")
        return CHOOSE_RISK
    context.user_data["risk_pct"] = risk_pct
    context.user_data["awaiting_custom_risk"] = False
    pair = context.user_data["pair"]
    info = PAIR_INFO[pair]
    await update.message.reply_text(
        f"✅ Риск: *{risk_pct}%*\n\n"
        f"📏 Введите *Stop Loss в пипах*:\n"
        f"_{info['pip_desc']}_\n_Обычно для {pair}: {info['example_sl']}_",
        parse_mode="Markdown",
    )
    return ENTER_SL


# Ввод SL → финальный расчёт
async def enter_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        sl_pips = float(text)
        if sl_pips <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректное число пипов. Например: *20*", parse_mode="Markdown")
        return ENTER_SL

    pair     = context.user_data["pair"]
    deposit  = context.user_data["deposit"]
    risk_pct = context.user_data["risk_pct"]
    leverage = context.user_data["leverage"]
    info     = PAIR_INFO[pair]

    # РАСЧЁТ ЛОТА
    # Лот = Риск($) ÷ (SL в пипах × Pip Value)
    risk_usd  = deposit * risk_pct / 100
    lot_size  = risk_usd / (sl_pips * info["pip_value"])
    lot_size  = round(lot_size, 2)

    # РАСЧЁТ МАРЖИ
    # Маржа = (Лот × Размер контракта × Цена) ÷ Плечо
    margin_used = (lot_size * info["contract_size"] * info["price_approx"]) / leverage
    margin_pct  = (margin_used / deposit) * 100

    # TP 1:2
    tp_pips    = sl_pips * 2
    profit_rr2 = risk_usd * 2
    lot_display = max(lot_size, 0.01)

    # Предупреждения
    warnings = ""
    if lot_size < 0.01:
        warnings += "\n⚠️ _Лот меньше минимума 0.01 — увеличь депозит или SL_"
    if margin_pct > 50:
        warnings += f"\n🚨 *Маржа {margin_pct:.1f}% от депозита — опасно!*"
    elif margin_pct > 25:
        warnings += f"\n⚠️ _Маржа {margin_pct:.1f}% от депозита — высоковато_"

    kb = [
        [InlineKeyboardButton("🔄 Новый расчёт", callback_data="restart")],
        [InlineKeyboardButton("↩️ Другая пара",  callback_data="change_pair"),
         InlineKeyboardButton("⚙️ Другое плечо", callback_data=f"reledge_{pair}")],
    ]

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *РЕЗУЛЬТАТ РАСЧЁТА*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Пара:          *{pair}*\n"
        f"  Депозит:      *${deposit:,.2f}*\n"
        f"  Плечо:         *1:{leverage}*\n"
        f"  Риск:           *{risk_pct}%*  =  *${risk_usd:,.2f}*\n"
        f"  Stop Loss:   *{sl_pips} пипов*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Размер лота:  {lot_display:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧮 *Формула:*\n"
        f"_${risk_usd:,.2f} ÷ ({sl_pips} × ${info['pip_value']:.0f}) = {lot_display:.2f} лот_\n\n"
        f"💰 *Маржа под сделку:*\n"
        f"= *${margin_used:,.2f}*  ({margin_pct:.1f}% от депо)\n\n"
        f"📈 *Take Profit 1:2*\n"
        f"  TP: *{tp_pips:.0f} пипов*  →  *+${profit_rr2:,.2f}*\n\n"
        f"💡 _{info['pip_desc']}_"
        f"{warnings}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ConversationHandler.END


# Кнопка "Другое плечо"
async def reledge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pair    = q.data.replace("reledge_", "")
    context.user_data["pair"] = pair
    info    = PAIR_INFO[pair]
    options = info["lev_options"]
    buttons = [InlineKeyboardButton(f"1:{l}", callback_data=f"lev_{l}") for l in options]
    kb_rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    await q.edit_message_text(
        f"{info['emoji']} *{pair}* — выберите плечо:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )
    return CHOOSE_LEVERAGE


# Рестарт
async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("🥇 XAUUSD — 1:20",   callback_data="pair_XAUUSD")],
        [InlineKeyboardButton("🇪🇺 EURUSD — 1:100", callback_data="pair_EURUSD"),
         InlineKeyboardButton("🇬🇧 GBPUSD — 1:200", callback_data="pair_GBPUSD")],
    ]
    await q.edit_message_text(
        "🔄 *Новый расчёт*\n\nВыберите торговую пару:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return CHOOSE_PAIR


# /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Как пользоваться ботом:*\n\n"
        "1️⃣ /start — начать\n"
        "2️⃣ Выбери пару\n"
        "3️⃣ Подтверди или смени плечо\n"
        "4️⃣ Введи депозит в USD\n"
        "5️⃣ Выбери риск\n"
        "6️⃣ Введи Stop Loss *в пипах*\n"
        "7️⃣ Получи размер лота ✅\n\n"
        "⚙️ *Плечи по умолчанию:*\n"
        "• XAUUSD → 1:20\n"
        "• EURUSD → 1:100\n"
        "• GBPUSD → 1:200\n\n"
        "🧮 *Формула:*\n"
        "`Лот = Риск($) ÷ (SL пипов × Pip Value)`\n\n"
        "📌 *Pip Value за 1.0 лот:*\n"
        "• EURUSD: $10 за пип\n"
        "• GBPUSD: $10 за пип\n"
        "• XAUUSD: $1 за пип",
        parse_mode="Markdown",
    )


# MAIN
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(restart_callback, pattern="^restart$"),
            CallbackQueryHandler(restart_callback, pattern="^change_pair$"),
            CallbackQueryHandler(reledge_callback, pattern="^reledge_"),
        ],
        states={
            CHOOSE_PAIR: [
                CallbackQueryHandler(choose_pair, pattern="^pair_"),
            ],
            CHOOSE_LEVERAGE: [
                CallbackQueryHandler(use_default_lev,  pattern="^lev_use_default$"),
                CallbackQueryHandler(show_lev_options, pattern="^lev_change$"),
                CallbackQueryHandler(set_leverage,     pattern="^lev_\\d+$"),
            ],
            ENTER_DEPOSIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_deposit),
            ],
            CHOOSE_RISK: [
                CallbackQueryHandler(choose_risk, pattern="^risk_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_risk_text),
            ],
            ENTER_SL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_sl),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("help", help_cmd))
    print("🤖 Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
