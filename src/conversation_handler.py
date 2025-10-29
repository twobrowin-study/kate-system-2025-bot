from telegram import Bot, Message, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from src.config import NodeCode, settings
from src.minio_client import minio


class ConversationEnum:
    CodeAwait = 1
    PersonalAwait = 2


async def default_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    await update.message.reply_markdown(settings.default_message)


async def node_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    assert update.message.text
    node_code = settings.get_node_by_key(update.message.text)

    if not node_code:
        await default_handler(update, context)
        return ConversationHandler.END

    if node_code.code is None:
        await reply_node_content(update.message, node_code, context)
        return ConversationHandler.END

    context.chat_data["node_code"] = node_code  # type: ignore

    await update.message.reply_markdown(node_code.message, reply_markup=ReplyKeyboardMarkup([[settings.back_button]]))

    return ConversationEnum.CodeAwait


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message

    context.chat_data.clear()  # pyright: ignore[reportOptionalMemberAccess]

    await update.message.reply_markdown(settings.back_message, reply_markup=settings.get_node_codes_reply_markup())

    return ConversationHandler.END


async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    assert update.message.text
    assert update.effective_user
    assert context.chat_data
    assert type(context.chat_data["node_code"]) is NodeCode

    bot: Bot = context.application.bot

    node_code: NodeCode = context.chat_data["node_code"]

    if node_code.code != update.message.text:
        await default_handler(update, context)
        return ConversationEnum.CodeAwait

    context.chat_data.clear()

    msg: str = f"User @{update.effective_user.username} (`{update.effective_user.id}`) found code `{node_code.code}` for node `{node_code.name}`"
    await bot.send_message(settings.tg_admin_chat, msg, parse_mode=ParseMode.MARKDOWN)

    await reply_node_content(update.message, node_code, context)

    return ConversationHandler.END


async def reply_node_content(message: Message, node_code: NodeCode, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = settings.get_node_codes_reply_markup()

    if node_code.type == "text":
        await message.reply_markdown(node_code.content, reply_markup=reply_markup)
    else:
        if node_code.content in context.bot_data:
            content = context.bot_data[node_code.content]
        else:
            content, _ = await minio.download(settings.minio_bucket, node_code.content)

        if node_code.type == "photo":
            photo_message = await message.reply_photo(content, reply_markup=reply_markup)
            context.bot_data[node_code.content] = photo_message.photo[-1].file_id

        if node_code.type == "voice":
            voice_message = await message.reply_voice(content, reply_markup=reply_markup)
            assert voice_message.voice
            context.bot_data[node_code.content] = voice_message.voice.file_id


async def help_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    await update.message.reply_markdown(
        settings.help_message, reply_markup=ReplyKeyboardMarkup([[settings.back_button]])
    )
    return ConversationEnum.PersonalAwait


async def personal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    assert update.message.text

    if update.message.text not in settings.personal:
        await default_handler(update, context)
    else:
        await update.message.reply_markdown(settings.personal[update.message.text])

    return ConversationEnum.PersonalAwait
