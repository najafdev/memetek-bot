"""Meme and community engagement service for MEMETEK."""

import random
from typing import Dict, List, Optional
from memetek.config import BRAND_NAME, BRAND_TAGLINE

# GM messages
GM_MESSAGES = [
    "🌅 <b>GM CHADS & DEGENS!</b> Grab your coffee, check the charts, and never fade the memes. WAGMI! ☕🚀",
    "☀️ <b>GM MEMETEK FAM!</b> Another day, another moon mission. The sun is up and so are our spirits. 🪙🔥",
    "🌄 <b>GM KINGS!</b> Remember: paper hands sell, diamond hands meme. Have a legendary day! 💎🫡",
    "☕ <b>GM GM GM!</b> Green candles or red candles, MEMETEK vibes stay immaculate. Let's make it count. 🐸✨",
    "🚀 <b>RISE AND SHINE!</b> Waking up bullish because the MEMETEK community never sleeps. LFG! 🖤💛",
]

# GN messages
GN_MESSAGES = [
    "🌙 <b>GN DEGENS!</b> Rest those eyes, king. The charts will still be fluctuating tomorrow. Sleep tight! 😴🚀",
    "🌌 <b>GN MEMETEK FAM!</b> May your dreams be full of green candles and limitless moonshots. 🛌✨",
    "💤 <b>GN LEGENDS!</b> Turn off the price alerts, secure the sleep, and wake up ready to meme. WAGMI! 🫡🪙",
    "🌛 <b>GN TO ALL THE DIAMOND HANDS!</b> Tomorrow we meme harder. Peace out! 🖤💛",
]

# WAGMI messages
WAGMI_MESSAGES = [
    "🫡 <b>WAGMI, BRO.</b> Rome wasn't built in a day, and neither is the meme revolution. Stay based. 💎🚀",
    "✨ <b>WE ARE ALL GONNA MAKE IT.</b> Stick with the fam, bring the top-tier memes, and enjoy the ride. 🐸🔥",
    "🚀 <b>100% WAGMI ENERGY!</b> The community is our foundation, the memes are our fuel. Moonbound! 🌕🪙",
    "💎 <b>REMEMBER WHY YOU'RE HERE:</b> Not for boring corporate suits, but for the vibe, the tech, and the culture. WAGMI! 👑",
    "🔥 <b>NO PANIC, JUST VIBES.</b> True degens thrive in volatility. WAGMI to every single MEMETEK believer! 🖤💛",
]

# SER messages (hilarious degen advice/crypto slang)
SER_MESSAGES = [
    "🧐 <i>Ser… have you considered that selling before the 100x might cause irreversible emotional damage?</i> 💀",
    "🐸 <i>Ser, this is not a dip. This is an exclusive promotional discount orchestrated by the blockchain gods.</i> 📉",
    "👑 <i>Ser, one does not simply explain meme coin tokenomics to fiat maximalists. Just say 'vibe' and walk away.</i> 🚶‍♂️",
    "🧠 <i>Ser, my technical analysis indicates that when the memes get funnier, the chart gets greener. Science.</i> 📊",
    "🫡 <i>Ser, please calm down. The liquidity is locked, the memes are fresh, and the coffee is brewing.</i> ☕",
    "🚀 <i>Ser, the moon is merely our layover on the way to the Andromeda galaxy. Fasten your seatbelt.</i> 🌌",
    "💀 <i>Ser, my trading strategy is simple: buy the meme, hold the meme, transcend earthly finance.</i> 🪙",
]

# VIBE messages
VIBE_MESSAGES = [
    "✨ <b>VIBE CHECK:</b> 100% Bullish, 0% Corporate, 1000% Degen Energy! 🐸🔥",
    "🌊 <b>CURRENT MEMETEK VIBE:</b> Chilling on the blockchain, listening to synthwave, waiting for the moon. 🚀🎧",
    "💎 <b>VIBE CHECK:</b> Diamond hands forged in the fires of volatility. Unshakeable community spirit! 🛡️💛",
    "⚡ <b>VIBE CHECK:</b> Chaotic good. High meme output, zero toxicity, maximum brotherhood. 🫂👑",
    "🔥 <b>VIBE CHECK:</b> We don't chase pumps; we cultivate culture. The vibes in MEMETEK are elite. 🖤💛",
]


class MemeService:
    """Engagement and community entertainment helpers."""

    @staticmethod
    def get_random_gm() -> str:
        return random.choice(GM_MESSAGES)

    @staticmethod
    def get_random_gn() -> str:
        return random.choice(GN_MESSAGES)

    @staticmethod
    def get_random_wagmi() -> str:
        return random.choice(WAGMI_MESSAGES)

    @staticmethod
    def get_random_ser() -> str:
        return random.choice(SER_MESSAGES)

    @staticmethod
    def get_random_vibe() -> str:
        return random.choice(VIBE_MESSAGES)

    @staticmethod
    def flip_coin() -> Dict[str, str]:
        """Virtual coin flip with explicit entertainment disclaimer."""
        outcome = random.choice(["HEADS 🪙", "TAILS 🪙"])
        degen_flavor = (
            "Bullish omen! Moon mission confirmed."
            if "HEADS" in outcome
            else "Accumulation phase! Buy the dip."
        )
        message = (
            f"🪙 <b>MEMETEK VIRTUAL COIN FLIP</b> 🪙\n\n"
            f"Result: <b>{outcome}</b>\n"
            f"Degen prophecy: <i>{degen_flavor}</i>\n\n"
            f"⚠️ <b>DISCLAIMER:</b> <i>This coin flip is purely for entertainment and community fun! "
            f"It is NOT a trading signal, financial indicator, or investment recommendation. DYOR!</i>"
        )
        return {"outcome": outcome, "message": message}


meme_service = MemeService()
