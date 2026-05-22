import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Update, User, Chat
from telegram.ext import ContextTypes

# =========================================================
# LOGGER CONFIGURATION
# =========================================================

LOGGER_GC_ID = -1003964165574  # Updated logger group ID
ENABLE_LOGGING = True  # Master switch for logging
ENABLE_DEBUG_LOGS = False  # Enable debug-level logging

# Setup logging to file as backup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_logs.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_timestamp(timestamp: int = None) -> str:
    """Format timestamp for consistent display."""
    if timestamp is None:
        timestamp = int(time.time())
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram markdown."""
    if not text:
        return "None"
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def safe_send_message(client, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Safely send a message with error handling."""
    try:
        await client.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.error(f"Failed to send log message: {e}")
        # Try without parse_mode if HTML fails
        try:
            await client.send_message(chat_id=chat_id, text=text, parse_mode=None)
            return True
        except Exception as e2:
            logger.error(f"Failed to send log message even without parse_mode: {e2}")
            return False

# =========================================================
# MAIN LOGGER FUNCTIONS
# =========================================================

async def send_alive_logger(client, bot_name: str = "Itachi Bot"):
    """Send a message to the logger channel when the bot comes online."""
    if not ENABLE_LOGGING:
        return
    
    uptime_text = f"""
ðŸ”¥ <b>BOT IS NOW ONLINE</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ¤– Bot: {escape_markdown(bot_name)}
â° Time: <code>{format_timestamp()}</code>
âš¡ Status: <b>ðŸŸ¢ ACTIVE</b>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, uptime_text)
    logger.info(f"Bot online notification sent to {LOGGER_GC_ID}")

async def send_shutdown_logger(client, bot_name: str = "Itachi Bot"):
    """Send a message when the bot shuts down."""
    if not ENABLE_LOGGING:
        return
    
    shutdown_text = f"""
ðŸ”´ <b>BOT IS SHUTTING DOWN</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ¤– Bot: {escape_markdown(bot_name)}
â° Time: <code>{format_timestamp()}</code>
âš¡ Status: <b>ðŸ”´ OFFLINE</b>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, shutdown_text)
    logger.info(f"Bot shutdown notification sent to {LOGGER_GC_ID}")

async def send_start_logger(client, user: User):
    """Log when a new user starts interacting with the bot."""
    if not ENABLE_LOGGING:
        return
    
    # Check if user is new (you may want to implement this check)
    user_text = f"""
ðŸš€ <b>USER STARTED BOT</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ‘¤ Name: {escape_markdown(user.full_name or 'Unknown')}
ðŸ†” User ID: <code>{user.id}</code>
ðŸ“› Username: @{escape_markdown(user.username) if user.username else 'None'}
ðŸ—“ï¸ First Seen: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, user_text)
    logger.info(f"New user started bot: {user.id} - {user.username}")

async def send_group_logger(client, chat: Chat):
    """Log when the bot is added to a new group."""
    if not ENABLE_LOGGING:
        return
    
    try:
        members = await client.get_chat_members_count(chat.id)
    except Exception as e:
        logger.error(f"Failed to get member count for {chat.id}: {e}")
        members = "Unknown"
    
    group_text = f"""
ðŸ”¥ <b>BOT ADDED TO GROUP</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ·ï¸ Group: {escape_markdown(chat.title or 'Unknown')}
ðŸ†” Chat ID: <code>{chat.id}</code>
ðŸ‘¥ Members: {members}
ðŸ“ Type: {chat.type}
â° Added: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, group_text)
    logger.info(f"Bot added to group: {chat.id} - {chat.title}")

async def send_leave_group_logger(client, chat: Chat):
    """Log when the bot is removed from a group."""
    if not ENABLE_LOGGING:
        return
    
    leave_text = f"""
âš ï¸ <b>BOT REMOVED FROM GROUP</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ·ï¸ Group: {escape_markdown(chat.title or 'Unknown')}
ðŸ†” Chat ID: <code>{chat.id}</code>
â° Removed: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, leave_text)
    logger.info(f"Bot removed from group: {chat.id} - {chat.title}")

async def send_command_logger(client, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log when a user executes a command."""
    if not ENABLE_LOGGING:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    
    if not message or not message.text:
        return
    
    command_text = f"""
âŒ¨ï¸ <b>COMMAND EXECUTED</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ‘¤ User: {escape_markdown(user.full_name or 'Unknown')}
ðŸ†” User ID: <code>{user.id}</code>
ðŸ“› Username: @{escape_markdown(user.username) if user.username else 'None'}

ðŸ’¬ Command: <code>{escape_markdown(message.text[:100])}</code>
ðŸ·ï¸ Chat: {escape_markdown(chat.title or 'Private')}
ðŸ†” Chat ID: <code>{chat.id}</code>

â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, command_text)
    if ENABLE_DEBUG_LOGS:
        logger.debug(f"Command logged: {message.text} from {user.id}")

async def send_error_logger(client, error: Exception, update: Update = None):
    """Log errors that occur in the bot."""
    if not ENABLE_LOGGING:
        return
    
    error_text = f"""
âŒ <b>ERROR OCCURRED</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
âš ï¸ Error: <code>{escape_markdown(str(error)[:200])}</code>
ðŸ“Œ Type: {type(error).__name__}

"""
    
    if update and update.effective_user:
        user = update.effective_user
        error_text += f"""
ðŸ‘¤ User: {escape_markdown(user.full_name or 'Unknown')}
ðŸ†” User ID: <code>{user.id}</code>
"""
    
    if update and update.effective_chat:
        chat = update.effective_chat
        error_text += f"""
ðŸ·ï¸ Chat: {escape_markdown(chat.title or 'Private')}
ðŸ†” Chat ID: <code>{chat.id}</code>
"""
    
    if update and update.effective_message and update.effective_message.text:
        error_text += f"""
ðŸ’¬ Message: <code>{escape_markdown(update.effective_message.text[:100])}</code>
"""
    
    error_text += f"""
â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    
    await safe_send_message(client, LOGGER_GC_ID, error_text)
    logger.error(f"Error logged: {error}")

async def send_bank_transaction_logger(client, user_id: int, username: str, action: str, amount: int, bank_id: int = None):
    """Log bank transactions."""
    if not ENABLE_LOGGING:
        return
    
    transaction_text = f"""
ðŸ’° <b>BANK TRANSACTION</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ‘¤ User: @{escape_markdown(username) if username else str(user_id)}
ðŸ†” User ID: <code>{user_id}</code>
ðŸ’± Action: <b>{action.upper()}</b>
ðŸ’µ Amount: <b>â‚¹{amount:,}</b>
"""
    
    if bank_id:
        transaction_text += f"""
ðŸ¦ Bank ID: <code>{bank_id}</code>
"""
    
    transaction_text += f"""
â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, transaction_text)

async def send_card_draw_logger(client, user_id: int, username: str, card_name: str, card_rarity: str, card_value: int):
    """Log when a user draws a card."""
    if not ENABLE_LOGGING:
        return
    
    card_text = f"""
ðŸŽ´ <b>CARD DRAWN</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ‘¤ User: @{escape_markdown(username) if username else str(user_id)}
ðŸ†” User ID: <code>{user_id}</code>

ðŸƒ Card: <b>{escape_markdown(card_name)}</b>
â­ Rarity: {card_rarity.upper()}
ðŸ’Ž Value: {card_value}

â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, card_text)

async def send_trade_logger(client, sender_id: int, sender_name: str, receiver_id: int, receiver_name: str, amount: int):
    """Log coin transfers/trades between users."""
    if not ENABLE_LOGGING:
        return
    
    trade_text = f"""
ðŸ”„ <b>COIN TRANSFER</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ“¤ Sender: @{escape_markdown(sender_name) if sender_name else str(sender_id)}
ðŸ†” Sender ID: <code>{sender_id}</code>

ðŸ“¥ Receiver: @{escape_markdown(receiver_name) if receiver_name else str(receiver_id)}
ðŸ†” Receiver ID: <code>{receiver_id}</code>

ðŸ’¸ Amount: <b>â‚¹{amount:,}</b>

â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, trade_text)

async def send_duel_logger(client, winner_id: int, winner_name: str, loser_id: int, loser_name: str, reward: int = None):
    """Log duel results."""
    if not ENABLE_LOGGING:
        return
    
    duel_text = f"""
âš”ï¸ <b>DUEL COMPLETED</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ† Winner: @{escape_markdown(winner_name) if winner_name else str(winner_id)}
ðŸ†” Winner ID: <code>{winner_id}</code>

ðŸ’€ Loser: @{escape_markdown(loser_name) if loser_name else str(loser_id)}
ðŸ†” Loser ID: <code>{loser_id}</code>
"""
    
    if reward:
        duel_text += f"""
ðŸ’° Reward: <b>â‚¹{reward:,}</b>
"""
    
    duel_text += f"""
â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, duel_text)

async def send_bot_stats_logger(client, stats: Dict[str, Any]):
    """Send bot statistics periodically."""
    if not ENABLE_LOGGING:
        return
    
    stats_text = f"""
ðŸ“Š <b>BOT STATISTICS</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
ðŸ‘¥ Total Users: {stats.get('total_users', 'Unknown')}
ðŸ’¬ Total Groups: {stats.get('total_groups', 'Unknown')}
ðŸ’° Total Coins in Circulation: â‚¹{stats.get('total_coins', 0):,}
ðŸ¦ Total Tax Collected: â‚¹{stats.get('total_tax', 0):,}
ðŸŽ´ Total Cards in Deck: {stats.get('total_cards', 0)}

â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, stats_text)

# =========================================================
# ADMIN NOTIFICATION FUNCTIONS
# =========================================================

async def send_admin_alert(client, message: str, severity: str = "INFO"):
    """Send an alert to admins."""
    if not ENABLE_LOGGING:
        return
    
    severity_emoji = {
        "INFO": "â„¹ï¸",
        "WARNING": "âš ï¸",
        "ERROR": "âŒ",
        "CRITICAL": "ðŸ”¥"
    }
    
    alert_text = f"""
{severity_emoji.get(severity, 'â„¹ï¸')} <b>ADMIN ALERT</b>

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
{escape_markdown(message)}

â° Time: <code>{format_timestamp()}</code>
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
"""
    await safe_send_message(client, LOGGER_GC_ID, alert_text)

# =========================================================
# BOT EVENT HANDLERS (to be integrated with main bot)
# =========================================================

async def setup_logger_handlers(application):
    """Setup logger handlers for the bot application."""
    
    # Store original handlers if needed
    pass

# =========================================================
# CONFIGURATION FUNCTION
# =========================================================

def configure_logger(logger_id: int = None, enable_debug: bool = False):
    """Configure logger settings."""
    global LOGGER_GC_ID, ENABLE_DEBUG_LOGS
    if logger_id:
        LOGGER_GC_ID = logger_id
    ENABLE_DEBUG_LOGS = enable_debug
    print(f"âœ… Logger configured - Channel ID: {LOGGER_GC_ID}, Debug: {ENABLE_DEBUG_LOGS}")

# =========================================================
# TEST FUNCTION
# =========================================================

async def test_logger(client):
    """Test all logger functions."""
    print("Testing logger functions...")
    
    await send_alive_logger(client, "Test Bot")
    await send_bot_stats_logger(client, {
        'total_users': 100,
        'total_groups': 5,
        'total_coins': 50000,
        'total_tax': 5000,
        'total_cards': 50
    })
    await send_admin_alert(client, "This is a test alert", "INFO")
    
    print("Logger test completed")
