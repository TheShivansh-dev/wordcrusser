import random
import string
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup,ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ContextTypes
import openpyxl
from openpyxl import load_workbook, Workbook


CHANNEL_USERNAME = "@iespchannel0404" 
import pandas as pd
import os
ALLOWED_GROUP_IDS = [-1001817635995, -1002114430690]
EXCEL_FILE = "user_scores.xlsx"
TOKEN = "7250203799:AAE0M77UUyArkcfaqkWJHz-URozxGmfNBVQ"
botname = "volara"

def generate_random_letters():
    try:
        vowels = "aeiou"
        consonants = "bcdfghjklmnpqrstvwxyz"
        length = random.randint(6, 15)
        selected_vowels = random.choices(vowels, k=3)
        remaining_letters = random.choices(vowels + consonants, k=length - 2)
        all_letters = selected_vowels + remaining_letters
        random.shuffle(all_letters)
        return "".join(all_letters)
    except Exception as e:
        print("Exception occured")


def is_valid_word(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

 # Replace with your actual channel username

async def start_word_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    user_id = update.message.from_user.id

    # Check if user is a member of the channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            # User is not a member, send join message
            join_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Join Channel", url="https://t.me/iespchannel0404")]
            ])
            try:
                await update.message.reply_text(
                    "⚠️ To start the game, you must join our channel first!",
                    reply_markup=join_button
                )
            except Exception as e:
                await update.message.chat.send_message("⚠️ To start the game, you must join our channel first!",
                    reply_markup=join_button)
            return
    except Exception as e:
        print(e)
        try: 
            await update.message.reply_text("❌ Unable to verify your channel membership. Try again later.")
        except Exception as e:
            await update.message.chat.send_message("❌ Unable to verify your channel membership. Try again later.")
        return

    # Check if a game is already running in the group
    if context.bot_data.get(chat_id, {}).get("game_active", False):
        try:
            await update.message.reply_text("⚠️ A game is already running in this group!")
        except:
            await update.message.chat.send_message("⚠️ A game is already running in this group!")
        return

    # Game round selection buttons
    keyboard = [
        [InlineKeyboardButton("2️⃣ 5️⃣", callback_data=f"{chat_id}:rounds_25")],
        [InlineKeyboardButton("1️⃣ 0️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_100")],
        [InlineKeyboardButton("2️⃣ 5️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_250")],
        [InlineKeyboardButton("5️⃣ 0️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_500")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_text("How many rounds do you want?", reply_markup=reply_markup)
    except:
        await update.message.chat.send_message("How many rounds do you want?", reply_markup=reply_markup)

async def handle_round_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id, rounds = query.data.split(":")[0], int(query.data.split("_")[1])

    if chat_id not in context.bot_data:
        context.bot_data[chat_id] = {"game_active": False, "selected_round": None}

    if context.bot_data[chat_id]["game_active"]:
        return
    
    context.bot_data[chat_id] = {
        "selected_round": rounds,
        "game_active": False
    }

    keyboard = [
    [InlineKeyboardButton("1️⃣ 5️⃣", callback_data=f"{chat_id}:time_15"),
     InlineKeyboardButton("2️⃣ 0️⃣", callback_data=f"{chat_id}:time_20")],
    [InlineKeyboardButton("2️⃣ 5️⃣", callback_data=f"{chat_id}:time_25"),
     InlineKeyboardButton("3️⃣ 0️⃣", callback_data=f"{chat_id}:time_30")]
]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(f"✅ {rounds} Rounds Selected!\n\nNow choose the time in seconds per round:", reply_markup=reply_markup)
    except:
        await update.message.chat.send_message(f"✅ {rounds} Rounds Selected!\n\nNow choose the time in seconds per round:", reply_markup=reply_markup)
    

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id, selected_time = query.data.split(":")[0], int(query.data.split("_")[1])
    
    context.bot_data[chat_id]["selected_time"] = selected_time
    context.bot_data[chat_id]["game_active"] = True
    context.bot_data[chat_id]["user_scores"] = {}

    try:
        await query.edit_message_text(f"✅ Game starting with {context.bot_data[chat_id]['selected_round']} rounds and {selected_time} seconds per round!")
    except:
        await update.message.chat.send_message(f"✅ Game starting with {context.bot_data[chat_id]['selected_round']} rounds and {selected_time} seconds per round!")

    asyncio.create_task(run_multiple_rounds(update, context, chat_id))

async def run_multiple_rounds(update: Update, context: CallbackContext, chat_id: str):
    total_rounds = context.bot_data[chat_id]["selected_round"]
    time_limit = context.bot_data[chat_id]["selected_time"]

    for round_num in range(1, total_rounds + 1):
        if not context.bot_data[chat_id]["game_active"]:
            break

        await start_round(update, context, chat_id, round_num, time_limit)
        await asyncio.sleep(time_limit)  # Round duration

        await end_round(update, context, chat_id)  # End current round
    
    await update.effective_chat.send_message("🎉 Game Over! Thanks for playing!")
    user_scores = context.bot_data[chat_id]["user_scores"]
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})  # Ensure consistent data types
    else:
        df = pd.DataFrame(columns=["sr_no", "chat_id", "user_id", "username", "score"])

    new_data = []
    for user_id, data in user_scores.items():
        username = data["name"]
        score = data["score"]

        # Convert user_id and chat_id to string for consistency in comparison
        user_id = str(user_id)
        chat_id = str(chat_id)

        # Check if the user already exists in the same chat_id
        mask = (df["chat_id"] == chat_id) & (df["user_id"] == user_id)

        if mask.any():
            # Update existing row (add score & update username)
            df.loc[mask, "score"] = df.loc[mask, "score"].astype(int) + score
            df.loc[mask, "username"] = username  # Update username if changed
        else:
            # Add new row if user is in a different chat_id or doesn't exist
            new_data.append([len(df) + len(new_data) + 1, chat_id, user_id, username, score])

    # Append new users if any
    if new_data:
        new_df = pd.DataFrame(new_data, columns=["sr_no", "chat_id", "user_id", "username", "score"])
        df = pd.concat([df, new_df], ignore_index=True)

    # Ensure "sr_no" remains unique and sequential
    df["sr_no"] = range(1, len(df) + 1)

    # Save back to Excel
    df.to_excel(EXCEL_FILE, index=False)
    context.bot_data[chat_id]["game_active"] = False



def create_balanced_keyboard(letters):
    total_letters = len(letters)

    if total_letters <= 8:
        # If 6-8 letters, distribute evenly (or as close as possible)
        first_row_size = total_letters // 2
        second_row_size = total_letters - first_row_size
    else:
        # If more than 8, max 8 in first row, rest in second (max 7)
        first_row_size = 8
        second_row_size = total_letters - first_row_size

    keyboard = []
    index = 0

    # First row
    keyboard.append([InlineKeyboardButton(letters[j].upper(), callback_data=f"letter_{letters[j]}") for j in range(index, index + first_row_size)])
    index += first_row_size

    # Second row (if any letters remain)
    if second_row_size > 0:
        keyboard.append([InlineKeyboardButton(letters[j].upper(), callback_data=f"letter_{letters[j]}") for j in range(index, index + second_row_size)])

    return keyboard


async def start_round(update: Update, context: CallbackContext, chat_id: str, round_num: int, time_limit: int):
    letters = generate_random_letters()
    context.bot_data[chat_id]["current_letters"] = letters
    context.bot_data[chat_id]["used_words"] = set()
    
    keyboard = create_balanced_keyboard(letters)
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔵 Round {round_num}/{context.bot_data[chat_id]['selected_round']} 🔵\n"
                f"Form words using the letters below. You have {time_limit} seconds!",
            reply_markup=reply_markup
        )


async def process_word(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    
    if not context.bot_data.get(chat_id, {}).get("game_active", False):
        return  

    word = update.message.text.lower()
    user_id = update.message.from_user.id
    username = update.message.from_user.first_name

    current_letters = context.bot_data[chat_id]["current_letters"]
    used_words = context.bot_data[chat_id]["used_words"]
    user_scores = context.bot_data[chat_id]["user_scores"]

    if word in used_words:
        #await update.message.reply_text("⚠️ This word has already been used!")
        return  

    if all(current_letters.count(c) >= word.count(c) for c in word) and is_valid_word(word):
        used_words.add(word)  
        user_scores.setdefault(user_id, {"name": username, "score": 0})
        user_scores[user_id]["score"] += len(word)  

    else:
        print("Invalid word")
        
async def cancel_game(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)

    if not context.bot_data.get(chat_id, {}).get("game_active", False):
        try:
            await update.message.reply_text("⚠️ No active game is running in this group!")
        except:
            await update.message.chat.send_message("⚠️ No active game is running in this group!")
        return
    
    # Cancel the game
    context.bot_data[chat_id]["game_active"] = False
    
    try:
        await update.message.reply_text("❌ The game has been canceled!")
    except:
        await update.message.chat.send_message("❌ The game has been canceled!")



async def end_round(update: Update, context: CallbackContext, chat_id: str):
    user_scores = context.bot_data[chat_id]["user_scores"]
    if context.bot_data[chat_id]["game_active"] == False:
        return
    if not user_scores:
        await update.effective_chat.send_message("⏳ Time's up! No valid words submitted this round.")
        return

    # Prepare score results message
    results = "\n".join([f"{data['name']}: {data['score']} points" for data in user_scores.values()])
    await update.effective_chat.send_message(f"⏳ Time's up! Round Over!\n\n🔹 Scores till This Round:\n{results}")

async def my_score(update: Update, context: CallbackContext):
    """Fetches and displays the total score of the user across all groups."""
    user_id = str(update.message.from_user.id)

    if not os.path.exists(EXCEL_FILE):
        try:
            await update.message.reply_text("No game data found yet.")
        except:
            await update.message.chat.send_message("No game data found yet.")
        return

    df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})

    # Filter rows belonging to the user and sum their scores
    user_total_score = df[df["user_id"] == user_id]["score"].sum()

    if user_total_score == 0:
        try:
            await update.message.reply_text("You haven't scored any points yet.")
        except:
            await update.message.chat.send_message("You haven't scored any points yet.")
    else:
        try:
            await update.message.reply_text(f"🏅 Your Total Score: {user_total_score} points")
        except:
            await update.message.chat.send_message(f"🏅 Your Total Score: {user_total_score} points")


async def group_top_10_scorers(update: Update, context: CallbackContext):
    """Fetches and displays the top 10 scorers for the current group."""
    chat_id = str(update.message.chat_id)

    if not os.path.exists(EXCEL_FILE):
        try:
            await update.message.reply_text("No game data found yet.")
        except:
            await update.message.chat.send_message("No game data found yet.")
        return

    df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})

    # Filter for the current group and get top 10 scorers
    group_df = df[df["chat_id"] == chat_id]
    top_scorers = group_df.groupby(["user_id", "username"])["score"].sum().reset_index()
    top_scorers = top_scorers.sort_values(by="score", ascending=False).head(10)

    if top_scorers.empty:
        try:
            await update.message.reply_text("No scores recorded for this group yet.")
        except:
            await update.message.chat.send_message("No scores recorded for this group yet.")
        return

    result_text = "🏆 Top 10 Scorers in This Group 🏆\n\n"
    for index, row in top_scorers.iterrows():
        result_text += f"🔹 {row['username']}: {row['score']} points\n"
    try:
        await update.message.reply_text(result_text)
    except:
        await update.message.chat.send_message(result_text)


async def all_group_top_10(update: Update, context: CallbackContext):
    """Fetches and displays the top 10 scorers across all groups."""
    if not os.path.exists(EXCEL_FILE):
        try:
            await update.message.reply_text("No game data found yet.")
        except:
            await update.message.chat.send_message("No game data found yet.")
        return

    df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})

    # Combine scores across all groups and get top 10 players
    top_scorers = df.groupby(["user_id", "username"])["score"].sum().reset_index()
    top_scorers = top_scorers.sort_values(by="score", ascending=False).head(10)

    if top_scorers.empty:
        try:
            await update.message.reply_text("No scores recorded yet.")
        except:
            await update.message.chat.send_message("No scores recorded yet.")
        return

    result_text = "🌍 Top 10 Players Across All Groups 🌍\n\n"
    for index, row in top_scorers.iterrows():
        result_text += f"🏅 {row['username']}: {row['score']} points\n"

    try:
        await update.message.reply_text(result_text)
    except:
        await update.message.chat.send_message(result_text)


async def download_scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id
        
        # Check if the chat_id (group ID) is in the allowed list
    
        if chat_id not in ALLOWED_GROUP_IDS:
            try:
                await update.message.reply_text("Due to the free service, you are not allowed to start a game in this group. Play there https://t.me/+yVFKtplWZUA0Yzhl or contact @O000000000O00000000O")
            except Exception as e:
                await update.message.chat.send_message("Due to the free service, you are not allowed to start a game in this group. Play there https://t.me/+yVFKtplWZUA0Yzhl or contact @O000000000O00000000O")
            return

        # Check if the file exists
        if os.path.exists(EXCEL_FILE):
            # Send the file to the user
            with open(EXCEL_FILE, 'rb') as file:
                await context.bot.send_document(chat_id=update.message.chat.id, document=file)
        else:
            # Notify the user that the file does not exist
            await update.message.reply_text("Sorry, the score file is not available.")
    except Exception as e:
        # Handle any errors
        await update.message.reply_text(f"An error occurred: {e}")


def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("startgame", start_word_game))
    app.add_handler(CallbackQueryHandler(handle_round_selection, pattern='.*rounds_'))
    app.add_handler(CallbackQueryHandler(handle_time_selection, pattern='.*time_'))
    app.add_handler(CommandHandler("cancelgame", cancel_game))
    app.add_handler(CommandHandler("myscore", my_score))
    app.add_handler(CommandHandler("topgrpscorer", group_top_10_scorers))
    app.add_handler(CommandHandler("alltimetopper", all_group_top_10))
    app.add_handler(CommandHandler('downloadscoreiesp', download_scores_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_word))

    app.run_polling()

if __name__ == '__main__':
    main()
