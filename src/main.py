from loguru import logger
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)
from telegram.ext.filters import TEXT, Text

from src.config import settings
from src.conversation_handler import (
    ConversationEnum,
    back_handler,
    code_handler,
    help_handler,
    node_handler,
    personal_handler,
)
from src.error_handler import error_handler


async def post_init(app: Application) -> None:  # pyright: ignore[reportMissingTypeArgument]
    bot: Bot = app.bot
    bot_name = await bot.get_my_name()
    if bot_name.name != settings.name:
        await bot.set_my_name(settings.name)


async def start_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    await update.message.reply_markdown(settings.start_message, reply_markup=settings.get_node_codes_reply_markup())


if __name__ == "__main__":
    logger.info("Starting...")

    app = Application.builder().token(settings.tg_token).post_init(post_init).build()
    app.add_error_handler(error_handler, block=False)

    app.add_handler(CommandHandler("start", start_handler, block=False))

    app.add_handler(
        ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters=TEXT & ~Text([settings.help_button, settings.back_button]), callback=node_handler
                ),
                MessageHandler(filters=Text([settings.back_button]), callback=back_handler),
                MessageHandler(filters=Text([settings.help_button]), callback=help_handler),
            ],
            states={
                ConversationEnum.CodeAwait: [
                    MessageHandler(filters=TEXT & ~Text([settings.back_button]), callback=code_handler)
                ],
                ConversationEnum.PersonalAwait: [
                    MessageHandler(filters=TEXT & ~Text([settings.back_button]), callback=personal_handler)
                ],
            },
            fallbacks=[MessageHandler(filters=Text([settings.back_button]), callback=back_handler)],
            block=False,
        )
    )

    app.run_polling()

    logger.info("Done! Have a great day!")
