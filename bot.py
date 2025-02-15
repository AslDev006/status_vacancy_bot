import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.state import StateFilter

API_TOKEN ='7786266950:AAEwfWggDmjGkcYSB_-5Nfy39nkMdOoP3Fg'
ADMIN_CHAT_ID =6290849287
SECOND_ADMIN_CHAT_ID =8041065066
# API_TOKEN ='7155692669:AAH-RU3Bs4mqEQrqRZWesuQ08y0hlv7u7N4'
# ADMIN_CHAT_ID =5322589899
# SECOND_ADMIN_CHAT_ID =6575779781
# Bot va Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Holatlar
class Form(StatesGroup):
    name = State()
    surname = State()
    age = State()
    position = State()
    resume = State()
    confirm = State()

# Inline tugmalar
positions = [
    'Director', 'Administrator', 'Operator', 'Manager', 'Marketolog', 'Yurist', 'Buxgalter']

position_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=pos, callback_data=pos)] for pos in positions
])

# SQLite bazasi
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

# /start buyrug'i
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Foydalanuvchini bazaga qo'shish
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()

    await message.answer("Assalomu alaykum, Status akademiyasining vakant botiga xush kelibsiz!")

# /vacancy buyrug'i
async def cmd_vacancy(message: types.Message, state: FSMContext):
    await message.answer("Ismingizni kiriting:")
    await state.set_state(Form.name)

# /cancel buyrug'i
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Jarayon bekor qilindi!")

# Ismni qabul qilish
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Familyangizni kiriting:")
    await state.set_state(Form.surname)

# Familyani qabul qilish
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Yoshingizni kiriting (raqam):")
    await state.set_state(Form.age)

# Yoshni qabul qilish
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Yoshingizni faqat raqam shaklida kiriting.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Lavozimingizni tanlang:", reply_markup=position_kb)
    await state.set_state(Form.position)

# Lavozimni qabul qilish
async def process_position(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(position=callback_query.data)
    await callback_query.message.answer("Resume faylini yuboring (faqat .pdf):")
    await state.set_state(Form.resume)

# Resume qabul qilish
async def process_resume(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer("Iltimos .pdf formatidagi faylni yuboring.")
        return

    if message.document.mime_type not in [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]:
        await message.answer("Faqat .pdf fayl qabul qilinadi.")
        return

    await state.update_data(resume=message.document.file_id, user_id=message.from_user.id)

    user_data = await state.get_data()
    confirmation_text = (
        f"Ism: {user_data['name']}\n"
        f"Familya: {user_data['surname']}\n"
        f"Yosh: {user_data['age']}\n"
        f"Lavozim: {user_data['position']}\n"
        f"Resume yuklangan"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="Qaytadan", callback_data="confirm_no")]
    ])

    await message.answer(confirmation_text, reply_markup=keyboard)
    await state.set_state(Form.confirm)

# Tasdiqlash yoki qaytadan kiritish
async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    
    if callback_query.data == "confirm_yes":
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Taklif etish", callback_data=f"offer_{user_data['user_id']}")],
            [InlineKeyboardButton(text="Rad etish", callback_data=f"reject_{user_data['user_id']}")]
        ])

        # Har ikkita admin uchun xabar yuborish
        for admin_id in [ADMIN_CHAT_ID, SECOND_ADMIN_CHAT_ID]:
            await bot.send_document(
                admin_id,
                document=user_data['resume'],
                caption=(
                    f"Yangi foydalanuvchi ma'lumotlari:\n"
                    f"ID: {user_data['user_id']}\n"
                    f"Ism: {user_data['name']}\n"
                    f"Familya: {user_data['surname']}\n"
                    f"Yosh: {user_data['age']}\n"
                    f"Lavozim: {user_data['position']}"
                ),
                reply_markup=admin_keyboard
            )

        await callback_query.message.answer("Ma'lumotlaringiz adminga yuborildi. Javobni kuting.")
        await state.clear()
    elif callback_query.data == "confirm_no":
        await callback_query.message.answer("Qaytadan ma'lumot kiriting. /vacancy buyrug'ini yuboring.")
        await state.clear()

# Admin xabar yuborish
async def cmd_send_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("Faqat admin xabar yuborishi mumkin.")
        return

    await message.answer("Iltimos, yuboriladigan xabarni kiriting:")
    await state.set_state("waiting_for_message")

# Xabarni yuborish
async def process_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("Faqat admin xabar yuborishi mumkin.")
        return

    text = message.text
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    user_ids = cursor.fetchall()
    conn.close()

    for user_id in user_ids:
        await bot.send_message(chat_id=user_id[0], text=text)

    await message.answer("Xabar barcha foydalanuvchilarga yuborildi.")
    await state.clear()

# Uchrashuv vaqtini belgilash
async def handle_offer(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.data.split("_")[1]  # user_id ni ajratish
    await state.update_data(offered_user_id=user_id)
    await callback_query.message.answer("Iltimos, uchrashuv vaqtini kiriting (masalan, 2025-01-20 14:00):")
    await state.set_state("waiting_for_time")

async def process_meeting_time(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    offered_user_id = user_data.get("offered_user_id")
    if not offered_user_id:
        await message.answer("Xato yuz berdi, foydalanuvchi ID topilmadi.")
        await state.clear()
        return

    # Kiritilgan vaqtni tekshirish
    try:
        meeting_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Iltimos, vaqtni to'g'ri formatda kiriting (masalan, 2025-01-20 14:00).")
        return

    await bot.send_message(
        chat_id=offered_user_id,
        text=f"Biz sizni {meeting_time.strftime('%Y-%m-%d %H:%M')} da mana shu manzilda kutamiz. Iltimos, belgilangan vaqtga kechikmang.\nhttps://maps.google.com/maps?q=39.664203,66.930295&ll=39.664203,66.930295&z=16"
    )
    await message.answer("Uchrashuv vaqti foydalanuvchiga yuborildi.")
    await state.clear()

# Rad etish tugmasini ishlov berish
@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def process_reject(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split("_")[1])
    
    await bot.send_message(
        chat_id=user_id,
        text="Afsus, bizda hozir bu sohada bo'sh vakant mavjud emas. Ammo xavotir aslo xavotir olmang, siz bizga albatta kerak bo'lasiz!"
    )
    
    await callback_query.message.answer("Foydalanuvchiga rad etish xabari yuborildi.")
    await callback_query.answer()

# Handlerlarni ro'yxatdan o'tkazish
def register_handlers():
    dp.message.register(cmd_start, Command(commands="start"))
    dp.message.register(cmd_vacancy, Command(commands="vacancy"))
    dp.message.register(cmd_cancel, Command(commands="cancel")) 
    dp.message.register(process_name, StateFilter(Form.name))
    dp.message.register(process_surname, StateFilter(Form.surname))
    dp.message.register(process_age, StateFilter(Form.age))
    dp.callback_query.register(process_position, StateFilter(Form.position))
    dp.message.register(process_resume, StateFilter(Form.resume))
    dp.callback_query.register(process_confirmation, StateFilter(Form.confirm))
    dp.callback_query.register(handle_offer, lambda c: c.data.startswith("offer_"))
    dp.message.register(process_meeting_time, StateFilter("waiting_for_time"))
    dp.message.register(cmd_send_message, Command(commands="send_message"))
    dp.message.register(process_message, StateFilter("waiting_for_message"))

# Botni ishga tushirish
async def main():
    init_db()  # Ma'lumotlar bazasini tayyorlash
    register_handlers()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())