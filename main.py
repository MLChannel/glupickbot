import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ⚠️ ЗАМЕНИТЕ ЭТОТ ТОКЕН НА ВАШ НАСТОЯЩИЙ ТОКЕН БОТА! ⚠️
BOT_TOKEN = "8128407049:AAFsLTpYJsqV28zz9eEW8oohgAgxrIKYDQU"  # Замените на ваш токен!

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class QuizGame:
    def __init__(self):
        self.active_question: Optional[Dict] = None
        self.answered_users: set = set()
        self.questions: List[Dict] = self.load_questions()
        self.user_scores: Dict[str, int] = self.load_scores()
        self.current_round_questions: List[Dict] = []
        self.question_counter: int = 0
        self.total_round_questions: int = 10
        self.is_round_active: bool = False
        self.hint_task: Optional[asyncio.Task] = None
        self.current_hint: str = ""
        self.hints_given: int = 0
        self.max_hints: int = 3
        self.skip_votes: set = set()
        self.votes_needed: int = 2
        self.asti_question_active: bool = False  # Флаг для вопроса про Асти

    def load_questions(self) -> List[Dict]:
        try:
            with open('questions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [
                {
                    "id": 1,
                    "question": "Столица Франции?",
                    "answer": "Париж",
                    "author": "Бот",
                    "created_at": "2024-01-15T10:30:00"
                },
                {
                    "id": 2,
                    "question": "Сколько планет в Солнечной системе?",
                    "answer": "8",
                    "author": "Бot",
                    "created_at": "2024-01-15T11:00:00"
                }
            ]

    def save_questions(self):
        with open('questions.json', 'w', encoding='utf-8') as f:
            json.dump(self.questions, f, ensure_ascii=False, indent=2)

    def load_scores(self) -> Dict[str, int]:
        try:
            with open('scores.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_scores(self):
        with open('scores.json', 'w', encoding='utf-8') as f:
            json.dump(self.user_scores, f, ensure_ascii=False, indent=2)

    def add_question(self, question: str, answer: str, author: str) -> bool:
        new_question = {
            "id": len(self.questions) + 1,
            "question": question,
            "answer": answer.lower().strip(),
            "author": author,
            "created_at": datetime.now().isoformat()
        }
        self.questions.append(new_question)
        self.save_questions()
        return True

    def prepare_round(self):
        if len(self.questions) < self.total_round_questions:
            return False
        self.current_round_questions = random.sample(self.questions, self.total_round_questions)
        self.question_counter = 0
        self.is_round_active = True
        return True

    def get_next_question(self) -> Optional[Dict]:
        if not self.is_round_active or self.question_counter >= len(self.current_round_questions):
            return None
        question = self.current_round_questions[self.question_counter]
        self.question_counter += 1
        return question

    def check_answer(self, user_answer: str) -> bool:
        if not self.active_question:
            return False
        return user_answer.lower().strip() == self.active_question['answer'].lower().strip()

    def add_score(self, user_id: str, username: str):
        user_key = f"{username}({user_id})"
        if user_key not in self.user_scores:
            self.user_scores[user_key] = 0
        self.user_scores[user_key] += 1
        self.save_scores()

    def finish_round(self):
        self.is_round_active = False
        self.current_round_questions = []
        self.question_counter = 0
        self.active_question = None
        self.stop_hints()
        self.skip_votes.clear()

    def stop_hints(self):
        """Остановка подсказок"""
        if self.hint_task and not self.hint_task.done():
            self.hint_task.cancel()
        self.current_hint = ""
        self.hints_given = 0

    def generate_hint(self, answer: str, hint_number: int) -> str:
        """Генерация подсказки с открытыми буквами"""
        answer = answer.upper()
        if hint_number == 1:
            return answer[0] + " " * (len(answer) - 1)
        elif hint_number == 2:
            if len(answer) > 1:
                return answer[0] + " " * (len(answer) - 2) + answer[-1]
            else:
                return answer
        elif hint_number == 3:
            hint = ""
            for i, char in enumerate(answer):
                if i % 2 == 0 or i == len(answer) - 1:
                    hint += char
                else:
                    hint += " "
            return hint
        return " " * len(answer)

    async def start_hints(self, chat_id: int):
        """Запуск автоматических подсказок"""
        self.stop_hints()
        self.hints_given = 0

        async def hint_sequence():
            try:
                await asyncio.sleep(15)
                if self.active_question and chat_id:
                    self.hints_given = 1
                    self.current_hint = self.generate_hint(self.active_question['answer'], 1)
                    await bot.send_message(
                        chat_id,
                        f"💡 Подсказка 1/3:\n`{self.current_hint}`\n\n*Прошло 15 секунд*",
                        parse_mode="Markdown"
                    )

                await asyncio.sleep(15)
                if self.active_question and chat_id:
                    self.hints_given = 2
                    self.current_hint = self.generate_hint(self.active_question['answer'], 2)
                    await bot.send_message(
                        chat_id,
                        f"💡 Подсказка 2/3:\n`{self.current_hint}`\n\n*Прошло 30 секунд*",
                        parse_mode="Markdown"
                    )

                await asyncio.sleep(15)
                if self.active_question and chat_id:
                    self.hints_given = 3
                    self.current_hint = self.generate_hint(self.active_question['answer'], 3)
                    await bot.send_message(
                        chat_id,
                        f"💡 Подсказка 3/3:\n`{self.current_hint}`\n\n*Прошло 45 секунд*",
                        parse_mode="Markdown"
                    )

                await asyncio.sleep(15)
                if self.active_question and chat_id:
                    await bot.send_message(
                        chat_id,
                        f"⏰ Время вышло! Правильный ответ: *{self.active_question['answer']}*\n\nСледующий вопрос...",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(3)
                    await ask_next_question(chat_id)

            except asyncio.CancelledError:
                pass

        self.hint_task = asyncio.create_task(hint_sequence())

    def vote_skip(self, user_id: str, username: str) -> tuple[bool, int, int]:
        """Голосование за пропуск вопроса"""
        if user_id in self.skip_votes:
            return False, len(self.skip_votes), self.votes_needed

        self.skip_votes.add(user_id)
        votes_count = len(self.skip_votes)

        if votes_count >= self.votes_needed:
            return True, votes_count, self.votes_needed
        else:
            return False, votes_count, self.votes_needed


# Глобальный объект игры
quiz_game = QuizGame()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
🎯 <b>Бот-Викторина с подсказками</b> 🎯

<b>Доступные команды:</b>
/quiz - Начать викторину (10 вопросов)
/add_question - Добавить свой вопрос
/scores - Показать таблицу лидеров
/stop - Остановить викторину
/hint - Получить подсказку досрочно
/skip - Проголосовать за пропуск вопроса (нужно {} голосов)
/astiquiz - Специальный вопрос про Асти 💖
/help - Справка

<b>Система подсказок:</b>
• Через 15 сек - первая буква
• Через 30 сек - первая и последняя буквы  
• Через 45 сек - дополнительные буквы
• Через 60 сек - автоматически следующий вопрос
    """.format(quiz_game.votes_needed)
    await message.answer(welcome_text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📖 <b>Как пользоваться ботом:</b>

1. Добавьте вопросы командой /add_question
2. Начните викторину командой /quiz
3. Отвечайте на вопросы в чате
4. Используйте /hint для досрочной подсказки
5. Используйте /skip для пропуска сложного вопроса
6. Используйте /astiquiz для специального вопроса 💖
7. Первый правильный ответ получает очко!

<b>Автоматические подсказки:</b>
⏰ 15 сек - показывается первая буква
⏰ 30 сек - первая и последняя буквы
⏰ 45 сек - дополнительные буквы
⏰ 60 сек - автоматически следующий вопрос

<b>Пропуск вопроса:</b>
/skip - нужно {} голосов для пропуска

<b>Специальная команда:</b>
/astiquiz - вопрос про Асти
    """.format(quiz_game.votes_needed)
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("astiquiz"))
async def cmd_astiquiz(message: types.Message):
    """Команда для вопроса про Асти"""
    quiz_game.asti_question_active = True
    question_text = "💖 Кто любит Асти?"
    await message.answer(question_text)


@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    if quiz_game.is_round_active:
        await message.answer("❌ Викторина уже идет! Дождитесь окончания текущего раунда.")
        return

    if len(quiz_game.questions) < quiz_game.total_round_questions:
        await message.answer(
            f"❌ Недостаточно вопросов! Нужно минимум {quiz_game.total_round_questions}, а сейчас {len(quiz_game.questions)}. Добавьте вопросы командой /add_question")
        return

    if not quiz_game.prepare_round():
        await message.answer("❌ Ошибка при подготовке раунда!")
        return

    await ask_next_question(message.chat.id)


@dp.message(Command("skip"))
async def cmd_skip(message: types.Message):
    """Команда для пропуска вопроса"""
    if not quiz_game.active_question:
        await message.answer("❌ Сейчас нет активного вопроса!")
        return

    user_id = str(message.from_user.id)
    username = message.from_user.full_name

    skipped, votes_count, votes_needed = quiz_game.vote_skip(user_id, username)

    if skipped:
        quiz_game.stop_hints()
        quiz_game.skip_votes.clear()

        skip_text = f"""
⏭️ <b>Вопрос пропущен!</b>

Голосов за пропуск: {votes_count}/{votes_needed}
Правильный ответ: {quiz_game.active_question['answer']}

Следующий вопрос через 3 секунды...
        """
        await message.answer(skip_text, parse_mode="HTML")

        await asyncio.sleep(3)
        await ask_next_question(message.chat.id)
    else:
        if votes_count == 1:
            await message.answer(
                f"✅ {username} проголосовал за пропуск вопроса! Нужно еще {votes_needed - votes_count} голос(а) для пропуска.")
        else:
            await message.answer(
                f"✅ Голосов за пропуск: {votes_count}/{votes_needed}. Нужно еще {votes_needed - votes_count} голос(а) для пропуска.")


@dp.message(Command("hint"))
async def cmd_hint(message: types.Message):
    """Команда для досрочного получения подсказки"""
    if not quiz_game.active_question:
        await message.answer("❌ Сейчас нет активного вопроса!")
        return

    if quiz_game.hints_given >= quiz_game.max_hints:
        await message.answer("ℹ️ Все подсказки уже были показаны!")
        return

    next_hint_number = quiz_game.hints_given + 1
    quiz_game.hints_given = next_hint_number
    quiz_game.current_hint = quiz_game.generate_hint(quiz_game.active_question['answer'], next_hint_number)

    time_info = {
        1: "15 секунд",
        2: "30 секунд",
        3: "45 секунд"
    }

    await message.answer(
        f"💡 Подсказка {next_hint_number}/3 (досрочно):\n`{quiz_game.current_hint}`\n\n*Обычно показывается через {time_info[next_hint_number]}*",
        parse_mode="Markdown"
    )


async def ask_next_question(chat_id: int):
    """Задать следующий вопрос"""
    quiz_game.stop_hints()
    quiz_game.skip_votes.clear()
    quiz_game.asti_question_active = False  # Сбрасываем флаг вопроса про Асти

    question = quiz_game.get_next_question()

    if not question:
        await finish_round(chat_id)
        return

    quiz_game.active_question = question
    quiz_game.answered_users.clear()

    quiz_text = f"""
🎲 <b>Вопрос {quiz_game.question_counter}/{quiz_game.total_round_questions}</b> 🎲

{question['question']}

💡 <i>Пишите ответы в чат! Первый правильный ответ получает очко.</i>

⏰ <b>Подсказки появятся автоматически:</b>
• 15 сек - первая буква
• 30 сек - первая и последняя  
• 45 сек - дополнительные буквы
• 60 сек - следующий вопрос

⏭️ <b>Пропуск вопроса:</b> /skip (нужно {quiz_game.votes_needed} голоса)
    """
    await bot.send_message(chat_id, quiz_text, parse_mode="HTML")

    await quiz_game.start_hints(chat_id)


async def finish_round(chat_id: int):
    """Завершение раунда и показ результатов"""
    quiz_game.finish_round()

    round_results = "🏁 <b>Раунд завершен!</b> 🏁\n\n"

    if quiz_game.user_scores:
        sorted_scores = sorted(quiz_game.user_scores.items(), key=lambda x: x[1], reverse=True)
        round_results += "📊 <b>Текущие результаты:</b>\n\n"
        for i, (user_key, score) in enumerate(sorted_scores[:5], 1):
            round_results += f"{i}. {user_key}: {score} очков\n"
    else:
        round_results += "😴 В этом раунде никто не заработал очков..."

    round_results += "\nДля нового раунда используйте /quiz"

    await bot.send_message(chat_id, round_results, parse_mode="HTML")


@dp.message(Command("add_question"))
async def cmd_add_question(message: types.Message):
    args = message.text.split('\n')
    if len(args) < 3:
        await message.answer("""
📝 <b>Формат добавления вопроса:</b>

/add_question
Ваш вопрос?
Правильный ответ

<b>Пример:</b>
/add_question
Столица Франции?
Париж

<b>Сейчас в базе:</b> {}/{} вопросов
        """.format(len(quiz_game.questions), quiz_game.total_round_questions), parse_mode="HTML")
        return

    question_text = args[1].strip()
    answer_text = args[2].strip()

    if quiz_game.add_question(question_text, answer_text, message.from_user.full_name):
        await message.answer(f"✅ Вопрос успешно добавлен! Теперь в базе {len(quiz_game.questions)} вопросов")
    else:
        await message.answer("❌ Ошибка при добавлении вопроса")


@dp.message(Command("scores"))
async def cmd_scores(message: types.Message):
    if not quiz_game.user_scores:
        await message.answer("📊 Пока никто не заработал очков!")
        return

    sorted_scores = sorted(quiz_game.user_scores.items(), key=lambda x: x[1], reverse=True)

    scores_text = "🏆 <b>Таблица лидеров:</b>\n\n"
    for i, (user_key, score) in enumerate(sorted_scores[:10], 1):
        scores_text += f"{i}. {user_key}: {score} очков\n"

    await message.answer(scores_text, parse_mode="HTML")


@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    if not quiz_game.is_round_active:
        await message.answer("❌ Викторина не активна!")
        return

    quiz_game.finish_round()
    await message.answer("⏹ Викторина остановлена! Используйте /quiz для нового раунда.")

@dp.message(Command("love"))
async def cmd_love(message: types.Message):
    await message.answer("Котенок любит мышонка ❤️")


@dp.message()
async def handle_all_messages(message: types.Message):
    """Обработка всех сообщений"""
    if message.text.startswith('/'):
        return

    # Сначала проверяем ответ на вопрос про Асти
    if quiz_game.asti_question_active:
        user_answer = message.text.lower().strip()

        # Проверяем разные варианты правильного ответа
        correct_answers = ["даня", "danja", "danja", "данька", "данечка", "даник"]

        if any(correct_answer in user_answer for correct_answer in correct_answers):
            await message.answer("✅ Верно! Даня любит Асти 💖")
            quiz_game.asti_question_active = False  # Сбрасываем флаг
        else:
            await message.reply("❌ нет")
        return

    # Затем проверяем ответы на обычную викторину
    if not quiz_game.active_question or not quiz_game.is_round_active:
        return

    user_id = str(message.from_user.id)
    if user_id in quiz_game.answered_users:
        return

    user_answer = message.text

    if quiz_game.check_answer(user_answer):
        quiz_game.answered_users.add(user_id)
        quiz_game.add_score(user_id, message.from_user.full_name)
        quiz_game.stop_hints()
        quiz_game.skip_votes.clear()

        winner_text = f"""
🎉 <b>Правильно!</b> 🎉

{message.from_user.full_name} получает очко!
<b>Правильный ответ:</b> {quiz_game.active_question['answer']}

Следующий вопрос через 3 секунды...
        """
        await message.answer(winner_text, parse_mode="HTML")

        await asyncio.sleep(3)
        await ask_next_question(message.chat.id)


async def main():
    print("Бот-викторина с подсказками, пропуском и вопросом про Асти запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())