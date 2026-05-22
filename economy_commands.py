import time
import json
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_balance, update_balance, set_balance,
    get_user_stats, get_locked_savings,
    apply_interest, deposit_tax, get_all_users, get_conn,
    get_bank_balance, get_username, set_bank, db_lock,
    get_ref_reward
)
# Remove 'track_game' from the import if it's not being used
from database import db_lock

import json

with open("config.json", "r") as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]

def setup_bank_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_uid INTEGER,
                created_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_members (
                uid INTEGER PRIMARY KEY,
                bank_id INTEGER,
                joined_at INTEGER
            )
        """)
        conn.commit()


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = int(time.time())

    with get_conn() as conn:
        row = conn.execute("SELECT last_daily FROM users WHERE id = ?", (uid,)).fetchone()
        last = row[0] if row else 0

        if now - last < 86400:
            wait = int((86400 - (now - last)) / 60)
            return await update.message.reply_text(f"ðŸ•’ Already claimed. Try again in {wait} minutes.")

        reward = 100
        update_balance(uid, reward)
        conn.execute("UPDATE users SET last_daily = ? WHERE id = ?", (now, uid))
        conn.commit()

    await update.message.reply_text(f"ðŸŽ You received {reward} coins as your daily reward!")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    if not users:
        return await update.message.reply_text("ðŸ“­ No users found.")

    lines = ["ðŸ† Top Richest Users:"]
    for i, (uid, username, coins) in enumerate(users[:10], start=1):
        name = f"@{username}" if username else f"User {uid}"
        lines.append(f"{i}. {name} â€” {coins} coins")

    await update.message.reply_text("\n".join(lines))

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with get_conn() as conn:
        rows = conn.execute("SELECT username FROM users WHERE referrer_id = ?", (uid,)).fetchall()

    count = len(rows)
    names = [f"@{r[0]}" if r[0] else "Unnamed" for r in rows]
    msg = f"ðŸ‘¥ Youâ€™ve invited {count} user(s).\n" + ("\n".join(names) if names else "No referrals yet.")
    await update.message.reply_text(msg)

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bot_username = "uno_reverse_god_bot"
    link = f"https://t.me/{bot_username}?start={uid}"

    await update.message.reply_text(
        f"ðŸŽ <b>Invite Friends</b>\n"
        f"Share this link:\n<a href='{link}'>{link}</a>\n\n"
        f"ðŸ’° Earn coins when they join!",
        parse_mode="HTML"
    )

async def myreferrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                new_uid INTEGER PRIMARY KEY,
                referrer_uid INTEGER,
                timestamp INTEGER
            )
        """)
        rows = conn.execute("""
            SELECT new_uid FROM referrals WHERE referrer_uid = ?
        """, (uid,)).fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ™ You havenâ€™t invited anyone yet.")

    count = len(rows)
    await update.message.reply_text(
        f"ðŸŽ Youâ€™ve invited <b>{count}</b> users!\nðŸ’° Earned: <b>{count * get_ref_reward()} coins</b>",
        parse_mode="HTML"
    )


async def referrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                new_uid INTEGER PRIMARY KEY,
                referrer_uid INTEGER,
                timestamp INTEGER
            )
        """)

        cursor = conn.execute("""
            SELECT referrer_uid, COUNT(*) as total
            FROM referrals
            GROUP BY referrer_uid
            ORDER BY total DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No referral data found.")
        return

    lines = ["ðŸ† <b>Top Referrers</b>"]
    for i, (uid, total) in enumerate(rows, 1):
        lines.append(f"{i}. <a href='tg://user?id={uid}'>User</a> â€” <b>{total}</b> invites")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


with open("config.json", "r") as f:
    config = json.load(f)
admin_ids = config.get("ADMIN_IDS", [])

async def setrefreward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("ðŸš« Youâ€™re not authorized.")

    try:
        new_value = int(context.args[0])
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES ('ref_reward', ?)
            """, (new_value,))
            conn.commit()

        await update.message.reply_text(f"âœ… Referral reward set to {new_value} coins.")
    except:
        await update.message.reply_text("âš ï¸ Usage: /setrefreward <amount>")


async def referralscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with get_conn() as conn:
        referred = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (uid,)).fetchone()[0]

    total_earned = referred * 100
    await update.message.reply_text(f"ðŸ’° Youâ€™ve earned {total_earned} coins from {referred} referral(s).")

async def referralmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("ðŸš« Admins only.")

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.username, r.username
            FROM users u
            LEFT JOIN users r ON u.referrer_id = r.id
            WHERE u.referrer_id IS NOT NULL
        """).fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ“­ No referral data found.")

    lines = ["ðŸ“Š Referral Map:"]
    for invitee, referrer in rows:
        lines.append(f"ðŸ‘¤ @{invitee} was invited by @{referrer}")
    await update.message.reply_text("\n".join(lines))


async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with get_conn() as conn:
        row = conn.execute("SELECT bank FROM users WHERE id = ?", (uid,)).fetchone()
    bank_balance = row[0] if row else 0
    await update.message.reply_text(f"ðŸ¦ Your bank balance: {bank_balance} coins")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("âš ï¸ Usage: /deposit <amount>")

    amount = int(args[0])
    coins = get_balance(uid)

    if coins < amount:
        return await update.message.reply_text("âŒ Not enough coins to deposit.")

    now = int(time.time())

    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET coins = coins - ?, bank = bank + ?, last_deposit_time = ? WHERE id = ?", (amount, amount, now, uid))
            conn.commit()

    await update.message.reply_text(f"âœ… Deposited â‚¹{amount} into bank.\nâ³ Interest will be claimable after 24 hours using /claiminterest")

async def claiminterest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = int(time.time())

    with get_conn() as conn:
        row = conn.execute("SELECT bank, last_deposit_time FROM users WHERE id = ?", (uid,)).fetchone()
        if not row:
            return await update.message.reply_text("âŒ You donâ€™t have a bank account.")

        bank_balance, last_deposit = row
        if now - last_deposit < 86400:
            remaining = 86400 - (now - last_deposit)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return await update.message.reply_text(f"â³ You can claim interest in {hours}h {minutes}m.")

        interest = int(bank_balance * 0.04)

        with db_lock:
            conn.execute("UPDATE users SET bank = bank + ?, last_deposit_time = ? WHERE id = ?", (interest, now, uid))
            conn.commit()

    await update.message.reply_text(f"âœ… Claimed â‚¹{interest} interest on your bank savings.")


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("âš ï¸ Usage: /withdraw <amount>")

    amount = int(args[0])
    bank_balance = get_bank_balance(uid)

    if bank_balance < amount:
        return await update.message.reply_text("âŒ Not enough bank savings.")

    tax = int(amount * 0.025)
    net = amount - tax

    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET bank = bank - ?, coins = coins + ? WHERE id = ?", (amount, net, uid))
            conn.commit()

    deposit_tax(tax)
    await update.message.reply_text(f"âœ… Withdrawn â‚¹{amount} from bank.\nðŸ’¸ â‚¹{tax} collected as tax.\nðŸ‘œ You received â‚¹{net}")

async def topbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_conn() as conn:
        rows = conn.execute("SELECT username, bank FROM users ORDER BY bank DESC LIMIT 10").fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ“­ No bank data found.")

    lines = ["ðŸ¦ Top Bank Balances:"]
    for i, (username, bank) in enumerate(rows, start=1):
        name = f"@{username}" if username else "Unnamed"
        lines.append(f"{i}. {name} â€” {bank} coins")

    await update.message.reply_text("\n".join(lines))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stats = get_user_stats(uid)
    savings = get_locked_savings(uid)

    await update.message.reply_text(
        f"ðŸ“Š Your Stats:\n"
        f"ðŸ’° Coins: {stats['coins']}\n"
        f"ðŸ§˜ Karma: {stats['karma']}\n"
        f"ðŸ”’ Locked Savings: {savings} coins"
    )

async def taxbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_conn() as conn:
        row = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()
    total_tax = row[0] if row and row[0] else 0
    await update.message.reply_text(f"ðŸ›ï¸ Total tax collected: {total_tax} coins")

async def taxtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.username, SUM(t.amount) as total
            FROM tax_bank t
            JOIN users u ON t.id = u.id
            GROUP BY u.username
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ“­ No tax data found.")

    lines = ["ðŸ† Top Tax Contributors:"]
    for i, (username, total) in enumerate(rows, start=1):
        name = f"@{username}" if username else "Unnamed"
        lines.append(f"{i}. {name} â€” {total} coins")

    await update.message.reply_text("\n".join(lines))


from database import get_conn
import time
import json

with open("config.json", "r") as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]

async def createbank(update, context):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("ðŸš« Only admins can create banks.")

    name = " ".join(context.args)
    if not name:
        return await update.message.reply_text("âš ï¸ Usage: /createbank <name>")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO banks (name, owner_uid, created_at)
            VALUES (?, ?, ?)
        """, (name, uid, int(time.time())))
        conn.commit()

    await update.message.reply_text(f"âœ… Bank <b>{name}</b> created!", parse_mode="HTML")

async def joinbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args:
        return await update.message.reply_text("âš ï¸ Usage: /joinbank <bank_id>")

    bank_id = int(args[0])
    entry_fee = 500

    with get_conn() as conn:
        coins = get_balance(uid)
        if coins < entry_fee:
            return await update.message.reply_text("âŒ Not enough coins to join a bank.")

        conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (entry_fee, uid))
        conn.execute("INSERT OR REPLACE INTO bank_members (uid, bank_id, joined_at) VALUES (?, ?, ?)", (uid, bank_id, int(time.time())))
        conn.commit()

    deposit_tax(entry_fee)
    await update.message.reply_text(f"âœ… Joined bank ID {bank_id}. â‚¹{entry_fee} collected as tax.")



async def mybank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    with get_conn() as conn:
        row = conn.execute("""
            SELECT b.bank_id, b.name, b.owner_uid
            FROM bank_members bm
            JOIN banks b ON bm.bank_id = b.bank_id
            WHERE bm.uid = ?
        """, (uid,)).fetchone()

    if not row:
        return await update.message.reply_text("âŒ You havenâ€™t joined any bank yet.")

    bank_id, name, owner_uid = row
    owner = get_username(owner_uid)

    await update.message.reply_text(
        f"ðŸ¦ <b>Your Bank</b>\n"
        f"â€¢ Name: <b>{name}</b>\n"
        f"â€¢ ID: <code>{bank_id}</code>\n"
        f"â€¢ Owner: ðŸ‘‘ {owner}",
        parse_mode="HTML"
    )

async def bankinfo(update, context):
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("âš ï¸ Usage: /bankinfo <bank_id>")

    with get_conn() as conn:
        bank = conn.execute("SELECT name, owner_uid FROM banks WHERE bank_id = ?", (bank_id,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ Bank not found.")

        members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]

    await update.message.reply_text(
        f"ðŸ¦ <b>{bank[0]}</b>\nðŸ‘‘ Owner: <a href='tg://user?id={bank[1]}'>Admin</a>\nðŸ‘¥ Members: <b>{members}</b>",
        parse_mode="HTML"
    )

async def bankdeposit(update, context):
    uid = update.effective_user.id
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("âš ï¸ Usage: /bankdeposit <amount>")

    with get_conn() as conn:
        user = conn.execute("SELECT coins FROM users WHERE uid = ?", (uid,)).fetchone()
        if not user or user[0] < amount:
            return await update.message.reply_text("âŒ Not enough coins.")

        bank_row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
        if not bank_row:
            return await update.message.reply_text("âŒ You havenâ€™t joined any bank.")

        bank_id = bank_row[0]

        # Deduct from user
        conn.execute("UPDATE users SET coins = coins - ? WHERE uid = ?", (amount, uid))

        # Add to bank reserve (optional: create bank_reserves table)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_reserves (
                bank_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO bank_reserves (bank_id, coins) VALUES (?, 0)
        """, (bank_id,))
        conn.execute("""
            UPDATE bank_reserves SET coins = coins + ? WHERE bank_id = ?
        """, (amount, bank_id))

        conn.commit()

    await update.message.reply_text(f"âœ… Deposited <b>{amount}</b> coins to your bank.", parse_mode="HTML")

async def bankwithdraw(update, context):
    uid = update.effective_user.id
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("âš ï¸ Usage: /bankwithdraw <amount>")

    with get_conn() as conn:
        bank_row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
        if not bank_row:
            return await update.message.reply_text("âŒ You havenâ€™t joined any bank.")

        bank_id = bank_row[0]
        reserve = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()

        if not reserve or reserve[0] < amount:
            return await update.message.reply_text("âŒ Bank doesnâ€™t have enough coins.")

        conn.execute("UPDATE bank_reserves SET coins = coins - ? WHERE bank_id = ?", (amount, bank_id))

        conn.execute("UPDATE users SET coins = coins + ? WHERE uid = ?", (amount, uid))

        conn.commit()

    await update.message.reply_text(f"ðŸ’¸ Withdrawn <b>{amount}</b> coins from your bank.", parse_mode="HTML")

async def bankrank(update, context):
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_reserves (
                bank_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0
            )
        """)
        rows = conn.execute("""
            SELECT b.bank_id, b.name, r.coins
            FROM banks b
            LEFT JOIN bank_reserves r ON b.bank_id = r.bank_id
            ORDER BY r.coins DESC
            LIMIT 10
        """).fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ“‰ No banks with reserves yet.")

    lines = ["ðŸ¦ <b>Top Banks</b>"]
    for i, (bank_id, name, coins) in enumerate(rows, 1):
        coins = coins or 0
        lines.append(f"{i}. <b>{name}</b> â€” ðŸ’° {coins} coins (ID: {bank_id})")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def bankdashboard(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        bank_id, name = bank
        members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]
        coins = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()
        coins = coins[0] if coins else 0

    await update.message.reply_text(
        f"ðŸ“Š <b>Bank Dashboard</b>\nðŸ¦ Name: <b>{name}</b>\nðŸ‘¥ Members: <b>{members}</b>\nðŸ’° Reserve: <b>{coins}</b> coins",
        parse_mode="HTML"
    )

async def transferbank(update, context):
    uid = update.effective_user.id
    try:
        to_bank_id = int(context.args[0])
        amount = int(context.args[1])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("âš ï¸ Usage: /transferbank <to_bank_id> <amount>")

    with get_conn() as conn:
        from_bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not from_bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        from_bank_id = from_bank[0]
        from_reserve = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (from_bank_id,)).fetchone()
        if not from_reserve or from_reserve[0] < amount:
            return await update.message.reply_text("âŒ Not enough reserve in your bank.")

        target = conn.execute("SELECT name FROM banks WHERE bank_id = ?", (to_bank_id,)).fetchone()
        if not target:
            return await update.message.reply_text("âŒ Target bank not found.")

        conn.execute("UPDATE bank_reserves SET coins = coins - ? WHERE bank_id = ?", (amount, from_bank_id))
        conn.execute("INSERT OR IGNORE INTO bank_reserves (bank_id, coins) VALUES (?, 0)", (to_bank_id,))
        conn.execute("UPDATE bank_reserves SET coins = coins + ? WHERE bank_id = ?", (amount, to_bank_id))
        conn.commit()

    await update.message.reply_text(
        f"ðŸ” Transferred <b>{amount}</b> coins to <b>{target[0]}</b> (ID: {to_bank_id})",
        parse_mode="HTML"
    )


async def bankmembers(update, context):
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("âš ï¸ Usage: /bankmembers <bank_id>")

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT uid FROM bank_members WHERE bank_id = ?
        """, (bank_id,)).fetchall()

    if not rows:
        return await update.message.reply_text("âŒ No members found in this bank.")

    lines = [f"ðŸ‘¥ <b>Members of Bank ID {bank_id}</b>"]
    for uid_row in rows:
        uid = uid_row[0]
        lines.append(f"â€¢ <a href='tg://user?id={uid}'>User</a>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def deletebank(update, context):
    uid = update.effective_user.id
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("âš ï¸ Usage: /deletebank <bank_id>")

    with get_conn() as conn:
        bank = conn.execute("SELECT owner_uid FROM banks WHERE bank_id = ?", (bank_id,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ Bank not found.")
        if bank[0] != uid:
            return await update.message.reply_text("ðŸš« You donâ€™t own this bank.")

        conn.execute("DELETE FROM banks WHERE bank_id = ?", (bank_id,))
        conn.execute("DELETE FROM bank_members WHERE bank_id = ?", (bank_id,))
        conn.execute("DELETE FROM bank_reserves WHERE bank_id = ?", (bank_id,))
        conn.execute("DELETE FROM bank_logs WHERE bank_id = ?", (bank_id,))
        conn.commit()

    await update.message.reply_text(f"ðŸ—‘ï¸ Bank ID <b>{bank_id}</b> deleted.", parse_mode="HTML")


async def banklog(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        bank_id = bank[0]
        logs = conn.execute("""
            SELECT uid, action, amount, timestamp FROM bank_logs
            WHERE bank_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (bank_id,)).fetchall()

    if not logs:
        return await update.message.reply_text("ðŸ“­ No recent transactions.")

    lines = [f"ðŸ“œ <b>Recent Transactions for Bank ID {bank_id}</b>"]
    for uid, action, amount, ts in logs:
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        lines.append(f"â€¢ <b>{action.title()}</b> â€” <code>{amount}</code> coins by <a href='tg://user?id={uid}'>User</a> at {time_str}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def bankstats(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        bank_id, name = bank
        members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]
        coins = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()
        coins = coins[0] if coins else 0
        deposits = conn.execute("""
            SELECT SUM(amount) FROM bank_logs WHERE bank_id = ? AND action = 'deposit'
        """, (bank_id,)).fetchone()[0] or 0
        withdrawals = conn.execute("""
            SELECT SUM(amount) FROM bank_logs WHERE bank_id = ? AND action = 'withdraw'
        """, (bank_id,)).fetchone()[0] or 0

    await update.message.reply_text(
        f"ðŸ“Š <b>Bank Stats</b>\nðŸ¦ Name: <b>{name}</b>\nðŸ‘¥ Members: <b>{members}</b>\nðŸ’° Reserve: <b>{coins}</b>\nðŸ“¥ Deposits: <b>{deposits}</b>\nðŸ“¤ Withdrawals: <b>{withdrawals}</b>",
        parse_mode="HTML"
    )


async def bankinvite(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        bank_id = bank[0]

    invite_link = f"https://t.me/{context.bot.username}?start=joinbank_{bank_id}"
    await update.message.reply_text(
        f"ðŸ”— <b>Bank Invite Link</b>\nShare this to invite users to your bank:\n{invite_link}",
        parse_mode="HTML"
    )

async def bankaudit(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
        if not bank:
            return await update.message.reply_text("âŒ You donâ€™t own any bank.")

        bank_id = bank[0]
        logs = conn.execute("""
            SELECT uid, action, amount, timestamp FROM bank_logs
            WHERE bank_id = ? AND amount >= 1000
            ORDER BY timestamp DESC
            LIMIT 10
        """, (bank_id,)).fetchall()

    if not logs:
        return await update.message.reply_text("âœ… No suspicious activity detected.")

    lines = [f"ðŸ•µï¸ <b>Audit Log for Bank ID {bank_id}</b>"]
    for uid, action, amount, ts in logs:
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        lines.append(f"â€¢ <b>{action.title()}</b> â€” <code>{amount}</code> coins by <a href='tg://user?id={uid}'>User</a> at {time_str}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

from database import get_username

async def banklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT bank_id, name, owner_uid FROM banks
            ORDER BY bank_id ASC
        """).fetchall()

    if not rows:
        return await update.message.reply_text("ðŸ“­ No banks have been created yet.")

    lines = ["ðŸ¦ <b>Available Banks</b>\nðŸ’¸ Joining a bank costs <b>500 coins</b>."]
    for bank_id, name, owner_uid in rows:
        owner = get_username(owner_uid)
        lines.append(
            f"â€¢ <b>{name}</b> (ID: {bank_id}) â€” ðŸ‘‘ {owner}\n"
            f"â†ªï¸ <code>/joinbank {bank_id}</code>"
        )

    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")

async def joinbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.username or update.effective_user.full_name or str(uid)

    balance = get_balance(uid)
    tax = 500

    if balance < tax:
        return await update.message.reply_text(f"âŒ You need at least {tax} coins to join the bank system.")

    with get_conn() as conn:
        conn.execute("UPDATE users SET bank = 0 WHERE id = ?", (uid,))
        conn.execute("UPDATE users SET bank = bank - ? WHERE id = ?", (tax, uid))
        conn.execute("""
            INSERT INTO banktax (id, coins)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET coins = coins + ?
        """, (tax, tax))
        conn.commit()

    await update.message.reply_text(f"âœ… @{name}, youâ€™ve joined the bank system!\nðŸ’¸ Entry tax of {tax} coins collected.")



from database import get_username, get_bank_balance

async def leavebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    with get_conn() as conn:
        row = conn.execute("""
            SELECT bm.bank_id, b.name
            FROM bank_members bm
            JOIN banks b ON bm.bank_id = b.bank_id
            WHERE bm.uid = ?
        """, (uid,)).fetchone()

        if not row:
            return await update.message.reply_text("âš ï¸ Youâ€™re not part of any bank.")

        bank_id, bank_name = row
        savings = get_bank_balance(uid)

    await update.message.reply_text(
        f"ðŸ¦ <b>Bank:</b> {bank_name} (ID: {bank_id})\n"
        f"ðŸ’° <b>Your Bank Balance:</b> {savings} coins\n\n"
        f"âš ï¸ If you leave this bank:\n"
        f"â€¢ Your savings will be deleted\n"
        f"â€¢ The coins will be collected as tax\n"
        f"â€¢ You cannot recover them later\n\n"
        f"ðŸ‘‰ To confirm, type <code>/confirmleavebank</code>",
        parse_mode="HTML"
    )


from database import deposit_tax, set_bank

async def confirmleavebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    with get_conn() as conn:
        row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
        if not row:
            return await update.message.reply_text("âš ï¸ Youâ€™re not part of any bank.")

        savings = get_bank_balance(uid)

        if savings > 0:
            deposit_tax(savings)

        conn.execute("DELETE FROM bank_members WHERE uid = ?", (uid,))
        set_bank(uid, 0)
        conn.commit()

    await update.message.reply_text(
        f"âœ… Youâ€™ve left your bank.\nðŸ’¸ {savings} coins were collected as tax.\nYou can join another bank using /banklist.",
        parse_mode="HTML"
    )
