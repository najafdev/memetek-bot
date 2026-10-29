"""Inline and Reply keyboards for MEMETEK Bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_meme_reaction_keyboard(meme_id: int, upvotes: int = 0) -> InlineKeyboardMarkup:
    """Build reaction keyboard for memes."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 Degen", callback_data=f"react:{meme_id}:fire"),
                InlineKeyboardButton(text="🚀 Moon", callback_data=f"react:{meme_id}:moon"),
                InlineKeyboardButton(text="💀 Dead", callback_data=f"react:{meme_id}:dead"),
                InlineKeyboardButton(text="👑 Based", callback_data=f"react:{meme_id}:based"),
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐ Score: {upvotes} | Next Meme ➡️",
                    callback_data="next_meme",
                )
            ]
        ]
    )


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Category buttons for interactive help menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🐱 General", callback_data="help:general"),
                InlineKeyboardButton(text="🐸 Fun & Memes", callback_data="help:fun"),
            ],
            [
                InlineKeyboardButton(text="📊 Crypto & Alpha", callback_data="help:crypto"),
                InlineKeyboardButton(text="🛡️ Moderation / Admin", callback_data="help:admin"),
            ],
        ]
    )


def get_back_to_help_keyboard() -> InlineKeyboardMarkup:
    """Back button to return to main help menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Categories", callback_data="help:main")]
        ]
    )
