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
#TOKEN = "7007935023:AAENkGaklw6LMJA_sfhVZhnoAgIjW4lDTBc"
TOKEN = "7250203799:AAE0M77UUyArkcfaqkWJHz-URozxGmfNBVQ"
botname = "volara"
taskcancelcount = 1
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
        print("Exception occured",e)


def is_valid_word(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

 # Replace with your actual channel username

async def start_word_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = str(update.message.chat_id)
        user_id = update.message.from_user.id
        if context.bot_data.get(chat_id, {}).get("game_active", False):
            try:
                await update.message.reply_text("⚠️ A game is already running in this group!")
            except Exception as e:
                await update.message.chat.send_message("⚠️ A game is already running in this group!")
            return

        # Game round selection buttons
        keyboard = [
            [InlineKeyboardButton("2️⃣ 5️⃣", callback_data=f"{chat_id}:rounds_25"),
            InlineKeyboardButton(" 5️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_50")
            ],
            [InlineKeyboardButton("1️⃣ 0️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_100"),
            InlineKeyboardButton("1️⃣ 5️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_150")
            ],
            [ InlineKeyboardButton("2️⃣0️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_200"),
              InlineKeyboardButton("2️⃣ 5️⃣ 0️⃣", callback_data=f"{chat_id}:rounds_250")
            ],
            
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text("How many rounds do you want?", reply_markup=reply_markup)
        except Exception as e:
            await update.message.chat.send_message("How many rounds do you want?", reply_markup=reply_markup)
    except Exception as e:
        print("except Exception as eion occured",e)

async def handle_round_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:

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
        except Exception as e:
            await update.message.chat.send_message(f"✅ {rounds} Rounds Selected!\n\nNow choose the time in seconds per round:", reply_markup=reply_markup)
    except Exception as e:
        print("except Exception as eion occured",e)
    

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        chat_id, selected_time = query.data.split(":")[0], int(query.data.split("_")[1])
        
        context.bot_data[chat_id]["selected_time"] = selected_time
        context.bot_data[chat_id]["game_active"] = True
        context.bot_data[chat_id]["user_scores"] = {}

        try:
            await query.edit_message_text(f"✅ Game starting with {context.bot_data[chat_id]['selected_round']} rounds and {selected_time} seconds per round!")
        except Exception as e:
            await update.message.chat.send_message(f"✅ Game starting with {context.bot_data[chat_id]['selected_round']} rounds and {selected_time} seconds per round!")

        asyncio.create_task(run_multiple_rounds(update, context, chat_id))
    except Exception as e:
        print("except Exception as eion occured",e)

async def run_multiple_rounds(update: Update, context: CallbackContext, chat_id: str):
    try:
        total_rounds = context.bot_data[chat_id]["selected_round"]
        time_limit = context.bot_data[chat_id]["selected_time"]
        global taskcancelcount
        taskcancelcount =1
        for round_num in range(1, total_rounds + 1):
            if not context.bot_data[chat_id]["game_active"]:
                break
            if taskcancelcount > 3:
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
    except Exception as e:
        print("except Exception as eion occured",e)



def create_balanced_keyboard(letters):
    try:
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
    except Exception as e:
        print("except Exception as eion occured",e)


async def start_round(update: Update, context: CallbackContext, chat_id: str, round_num: int, time_limit: int):
    try:
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
    except Exception as e:
        print("except Exception as eion occured",e)


async def process_word(update: Update, context: CallbackContext):
    try:
        chat_id = str(update.message.chat_id)
        
        if not context.bot_data.get(chat_id, {}).get("game_active", False):
            return  

        word = update.message.text.lower()
        user_id = update.message.from_user.id
        user = update.message.from_user
        usershowingname = user.first_name
        username = f"@{user.username}" if user.username else user.first_name


        current_letters = context.bot_data[chat_id]["current_letters"]
        used_words = context.bot_data[chat_id]["used_words"]
        user_scores = context.bot_data[chat_id]["user_scores"]

        if word in used_words:
            #await update.message.reply_text("⚠️ This word has already been used!")
            return  

        if all(current_letters.count(c) >= word.count(c) for c in word) and is_valid_word(word):
            used_words.add(word)  
            user_scores.setdefault(user_id, {"name": username, "score": 0 ,"usershowingname":usershowingname})
            user_scores[user_id]["score"] += len(word)  
            print("this is",user_scores)
        
        else:
            print("Invalid word")
    except Exception as e:
        print("except Exception as eion occured",e)
        
async def cancel_game(update: Update, context: CallbackContext):
    try:
        chat_id = str(update.message.chat_id)

        if not context.bot_data.get(chat_id, {}).get("game_active", False):
            try:
                await update.message.reply_text("⚠️ No active game is running in this group!")
            except Exception as e:
                await update.message.chat.send_message("⚠️ No active game is running in this group!")
            return
        
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
        if new_data:
            new_df = pd.DataFrame(new_data, columns=["sr_no", "chat_id", "user_id", "username", "score"])
            df = pd.concat([df, new_df], ignore_index=True)
        df["sr_no"] = range(1, len(df) + 1)
        df.to_excel(EXCEL_FILE, index=False)
        context.bot_data[chat_id]["game_active"] = False
        
    except Exception as e:
        print("except Exception as eion occured",e)



async def end_round(update: Update, context: CallbackContext, chat_id: str):
    try:
        global taskcancelcount
        user_scores = context.bot_data[chat_id]["user_scores"]
        if context.bot_data[chat_id]["game_active"] == False:
            return
        if not user_scores:
            taskcancelcount = taskcancelcount +1
            await update.effective_chat.send_message("⏳ Time's up! No valid words submitted this round.")
            return
        taskcancelcount = 1
        # Prepare score results message
        results = "\n".join([f"{data['usershowingname']}: {data['score']} points" for data in user_scores.values()])
        await update.effective_chat.send_message(f"⏳ Time's up! Round Over!\n\n🔹 Scores till This Round:\n{results}")
    except Exception as e:
        print("except Exception as eion occured",e)

async def my_score(update: Update, context: CallbackContext):
    try:
        """Fetches and displays the total score of the user across all groups along with their rank."""
        user_id = str(update.message.from_user.id)

        if not os.path.exists(EXCEL_FILE):
            try:
                await update.message.reply_text("No game data found yet.")
            except Exception as e:
                await update.message.chat.send_message("No game data found yet.")
            return

        df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})

        # Calculate total scores for all users
        user_scores = df.groupby("user_id")["score"].sum().reset_index()

        # Sort by score in descending order
        user_scores = user_scores.sort_values(by="score", ascending=False).reset_index(drop=True)

        # Get the rank of the current user
        user_scores["rank"] = user_scores["score"].rank(method="min", ascending=False)
        user_total_score = user_scores[user_scores["user_id"] == user_id]["score"].sum()

        if user_total_score == 0:
            try:
                await update.message.reply_text("You haven't scored any points yet.")
            except Exception as e:
                await update.message.chat.send_message("You haven't scored any points yet.")
        else:
            user_rank = int(user_scores[user_scores["user_id"] == user_id]["rank"].values[0])
            total_players = len(user_scores)
            try:
                await update.message.reply_text(f"🏅 Your Total Score: {user_total_score} points\n"
                                                f"📊 Your Rank: {user_rank} out of {total_players} players")
            except Exception as e:
                await update.message.chat.send_message(f"🏅 Your Total Score: {user_total_score} points\n"
                                                       f"📊 Your Rank: {user_rank} out of {total_players} players")
    except Exception as e:
        print(f"Exception occurred: {e}")


async def group_top_10_scorers(update: Update, context: CallbackContext):
    try:
        """Fetches and displays the top 10 scorers for the current group."""
        chat_id = str(update.message.chat_id)

        if not os.path.exists(EXCEL_FILE):
            try:
                await update.message.reply_text("No game data found yet.")
            except Exception as e:
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
            except Exception as e:
                await update.message.chat.send_message("No scores recorded for this group yet.")
            return

        result_text = "🏆 Top 10 Scorers in This Group 🏆\n\n"
        for index, row in top_scorers.iterrows():
            result_text += f"🔹 {row['username']}: {row['score']} points\n"
        try:
            await update.message.reply_text(result_text)
        except Exception as e:
            await update.message.chat.send_message(result_text)
    except Exception as e:
        print("except Exception as eion occured",e)

async def all_group_top_10(update: Update, context: CallbackContext):
    try:
        """Fetches and displays the top 10 scorers across all groups."""
        if not os.path.exists(EXCEL_FILE):
            try:
                await update.message.reply_text("No game data found yet.")
            except Exception as e:
                await update.message.chat.send_message("No game data found yet.")
            return

        df = pd.read_excel(EXCEL_FILE, dtype={"chat_id": str, "user_id": str})

        # Combine scores across all groups and get top 10 players
        top_scorers = df.groupby(["user_id", "username"])["score"].sum().reset_index()
        top_scorers = top_scorers.sort_values(by="score", ascending=False).head(10)

        if top_scorers.empty:
            try:
                await update.message.reply_text("No scores recorded yet.")
            except Exception as e:
                await update.message.chat.send_message("No scores recorded yet.")
            return

        result_text = "🌍 Top 10 Players Across All Groups 🌍\n\n"
        for index, row in top_scorers.iterrows():
            result_text += f"🏅 {row['username']}: {row['score']} points\n"

        try:
            await update.message.reply_text(result_text)
        except Exception as e:
            await update.message.chat.send_message(result_text)
    except Exception as e:
        print("except Exception as eion occured",e)

async def download_scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id
        if chat_id not in ALLOWED_GROUP_IDS:
            try:
                await update.message.reply_text("Due to the free service, you are not allowed to start a game in this group. Play there https://t.me/+yVFKtplWZUA0Yzhl or contact @O000000000O00000000O")
            except Exception as e:
                await update.message.chat.send_message("Due to the free service, you are not allowed to start a game in this group. Play there https://t.me/+yVFKtplWZUA0Yzhl or contact @O000000000O00000000O")
            return
        if os.path.exists(EXCEL_FILE):
            with open(EXCEL_FILE, 'rb') as file:
                await context.bot.send_document(chat_id=update.message.chat.id, document=file)
        else:
            await update.message.reply_text("Sorry, the score file is not available.")
    except Exception as e:
        print("Exception occured",e)


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
