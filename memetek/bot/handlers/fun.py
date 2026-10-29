"""Fun, meme, and engagement command handlers for MEMETEK Bot."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.services.meme_service import meme_service
from memetek.database.crud import (
    get_random_approved_meme,
    create_meme,
    add_meme_reaction,
    get_top_memes,
    seed_initial_data_if_empty,
)
from memetek.bot.keyb import get_meme_reaction_keyboard

router = Router(name="fun")


@router.message(Command("gm"))
async def handle_gm(message: Message):
    """Send a fun, community GM greeting."""
    await message.answer(meme_service.get_random_gm())


@router.message(Command("gn"))
async def handle_gn(message: Message):
    """Send a calming GN greeting."""
    await message.answer(meme_service.get_random_gn())


@router.message(Command("wagmi"))
async def handle_wagmi(message: Message):
    """Send a boost of WAGMI community energy."""
    await message.answer(meme_service.get_random_wagmi())


@router.message(Command("ser"))
async def handle_ser(message: Message):
    """Send a funny degen-style meme coin message."""
    await message.answer(meme_service.get_random_ser())


@router.message(Command("flip"))
async def handle_flip(message: Message):
    """Flip a virtual coin with explicit entertainment label."""
    result = meme_service.flip_coin()
    await message.answer(result["message"])


@router.message(Command("vibe"))
async def handle_vibe(message: Message):
    """Perform a MEMETEK vibe check."""
    await message.answer(meme_service.get_random_vibe())


@router.message(Command("meme"))
async def handle_meme(message: Message, session: AsyncSession):
    """Return a random approved meme with reaction buttons."""
    await seed_initial_data_if_empty(session)
    meme = await get_random_approved_meme(session)

    if not meme:
        await message.answer(
            "🐸 <i>No memes in the vault yet! Use /submitmeme to submit the first meme!</i>"
        )
        return

    text_body = f"🐱 <b>MEMETEK VAULT MEME #{meme.id}</b> 🚀\n\n{meme.caption}"
    kb = get_meme_reaction_keyboard(meme.id, meme.upvotes)

    if meme.media_type == "photo" and meme.file_id:
        await message.answer_photo(photo=meme.file_id, caption=text_body, reply_markup=kb)
    else:
        await message.answer(text_body, reply_markup=kb)


@router.callback_query(F.data.startswith("react:"))
async def handle_meme_reaction_callback(callback: CallbackQuery, session: AsyncSession):
    """Record user reaction to a meme and update vote count."""
    parts = callback.data.split(":")
    meme_id = int(parts[1])
    reaction_type = parts[2]
    user_id = callback.from_user.id

    is_new, upvotes = await add_meme_reaction(
        session=session,
        meme_id=meme_id,
        user_id=user_id,
        reaction_type=reaction_type,
    )

    alert_text = (
        f"You reacted with {reaction_type.upper()}! 🔥"
        if is_new
        else f"Updated reaction to {reaction_type.upper()}! ⭐"
    )
    await callback.answer(alert_text, show_alert=False)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_meme_reaction_keyboard(meme_id, upvotes)
        )
    except Exception:
        pass


@router.callback_query(F.data == "next_meme")
async def handle_next_meme_callback(callback: CallbackQuery, session: AsyncSession):
    """Fetch another random meme."""
    meme = await get_random_approved_meme(session)
    if not meme:
        await callback.answer("No more memes in the vault! 🐸", show_alert=False)
        return

    text_body = f"🐱 <b>MEMETEK VAULT MEME #{meme.id}</b> 🚀\n\n{meme.caption}"
    kb = get_meme_reaction_keyboard(meme.id, meme.upvotes)

    try:
        await callback.message.edit_text(text_body, reply_markup=kb)
    except Exception:
        await callback.message.answer(text_body, reply_markup=kb)

    await callback.answer()


@router.message(Command("submitmeme"))
async def handle_submit_meme(message: Message, session: AsyncSession):
    """Allow members to submit memes for admin review."""
    user = message.from_user
    chat = message.chat

    # Check text argument
    caption = ""
    command_parts = message.text.split(maxsplit=1) if message.text else []
    if len(command_parts) > 1:
        caption = command_parts[1].strip()

    media_type = "text"
    file_id = None

    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.photo:
            media_type = "photo"
            file_id = reply.photo[-1].file_id
            caption = caption or reply.caption or "Community photo meme"
        elif reply.text:
            caption = caption or reply.text

    if not caption:
        await message.answer(
            "📝 <b>MEME SUBMISSION GUIDE:</b>\n\n"
            "Submit a meme for the official MEMETEK Vault:\n"
            "• <code>/submitmeme [Your hilarious joke or caption]</code>\n"
            "• Or reply to a photo/message with <code>/submitmeme</code>\n\n"
            "<i>Submissions are queued for moderator review before going live in /meme! 🛡️</i>"
        )
        return

    meme = await create_meme(
        session=session,
        caption=caption,
        media_type=media_type,
        file_id=file_id,
        submitter_user_id=user.id if user else None,
        chat_id=chat.id if chat else None,
        status="pending",
    )

    await message.answer(
        f"✅ <b>MEME SUBMITTED! (ID #{meme.id})</b> 🚀\n\n"
        f"Your meme has been placed in the moderator approval queue. "
        f"Once approved by the team, it will appear in <code>/meme</code> and <code>/topmemes</code>!\n\n"
        f"<i>Thank you for contributing to MEMETEK culture! 🫡💛</i>"
    )


@router.message(Command("topmemes"))
async def handle_top_memes(message: Message, session: AsyncSession):
    """Show the highest-rated community memes."""
    top_list = await get_top_memes(session, limit=5)
    if not top_list:
        await message.answer("🐸 <i>No approved memes found yet!</i>")
        return

    text = "👑 <b>MEMETEK HALL OF FAME — TOP MEMES</b> 🏆\n\n"
    for i, m in enumerate(top_list, 1):
        text += f"<b>{i}.</b> (⭐ {m.upvotes} upvotes) #{m.id}\n<i>\"{m.caption[:120]}\"</i>\n\n"

    text += "<i>Vote on memes using /meme to push your favorites into the Hall of Fame! 🔥</i>"
    await message.answer(text)
