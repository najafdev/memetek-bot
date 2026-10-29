"""Anti-Spam, Anti-Phishing, Flood and Security Moderation Engine for MEMETEK."""

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse

from memetek.config import settings
from memetek.services.cache import cache

logger = logging.getLogger(__name__)

# Dangerous executable or script extensions
PROHIBITED_EXTENSIONS = {
    ".exe", ".scr", ".bat", ".com", ".apk", ".vbs", ".js", ".cmd",
    ".pif", ".msi", ".jar", ".ps1", ".hta", ".wsf",
}

# Suspicious words often found in crypto phishing URLs
PHISHING_URL_KEYWORDS = [
    "airdrop-claim", "claim-airdrop", "free-mint", "connect-wallet",
    "wallet-connect", "claim-reward", "drainer", "verify-portal",
    "token-claim", "bonus-claim", "presale-live", "claim-bonus",
]

# Unsolicited ads and scam phrases
SCAM_PHRASES_PATTERNS = [
    r"\bguaranteed\s+(?:\d+x|profit|returns?)\b",
    r"\bdm\s+me\s+for\s+(?:signals|profit|crypto|alpha)\b",
    r"\bpassive\s+income\s+daily\b",
    r"\bearn\s+\$\d+\s+daily\b",
    r"\bsend\s+(?:\d+\s+)?(?:eth|sol|btc|usdt)\s+to\s+receive\s+double\b",
    r"\bwhatsapp\s+invest(?:ment|or)?\b",
    r"\bclaim\s+your\s+(?:free\s+)?airdrop\s+now\b",
    r"\bconnect\s+wallet\s+to\s+claim\b",
    r"\bpump\.fun\s+join\b",
]

# Impersonation keywords in display name / bio
IMPERSONATION_KEYWORDS = [
    "admin", "administrator", "moderator", "support", "helpdesk",
    "official", "memetek team", "founder", "ceo", "security",
]

# URL extraction regex
URL_REGEX = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?",
    re.IGNORECASE,
)


@dataclass
class SpamCheckResult:
    """Result of an anti-spam inspection."""
    is_violation: bool = False
    reason: str = ""
    action_type: str = "none"  # 'delete', 'warn', 'mute', 'none'
    severity: str = "low"      # 'low', 'medium', 'high', 'critical'
    safe_disclaimer: str = (
        "Automated scam heuristic check - not an absolute guarantee of safety."
    )


class AntiSpamService:
    """Comprehensive anti-spam and moderation filter."""

    def __init__(self):
        self.scam_regexes = [re.compile(p, re.IGNORECASE) for p in SCAM_PHRASES_PATTERNS]

    async def check_flood(self, chat_id: int, user_id: int) -> bool:
        """Check if user has exceeded the message flood threshold."""
        key = f"flood:{chat_id}:{user_id}"
        count = await cache.increment(key, ttl=settings.FLOOD_WINDOW_SECONDS)
        return count > settings.FLOOD_MAX_MESSAGES

    async def check_duplicate_spam(self, chat_id: int, user_id: int, text: str) -> bool:
        """Check if user is repeatedly sending the exact same message."""
        if not text or len(text.strip()) < 5:
            return False

        text_hash = hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
        key = f"dup_spam:{chat_id}:{user_id}:{text_hash}"
        count = await cache.increment(key, ttl=30)
        return count >= 3

    async def check_command_rate_limit(self, user_id: int) -> bool:
        """Rate limit command usage per user."""
        key = f"cmd_rate:{user_id}"
        count = await cache.increment(key, ttl=10)
        return count > 7

    def extract_urls(self, text: str) -> List[str]:
        """Extract all URLs from a message text."""
        if not text:
            return []
        return URL_REGEX.findall(text)

    def extract_domain(self, url: str) -> str:
        """Extract base domain from a URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def is_domain_allowed(self, domain: str, allowed_domains: List[str]) -> bool:
        """Check if domain or parent domain is in the allowlist."""
        clean_domain = domain.lower()
        for allowed in allowed_domains:
            allowed_clean = allowed.lower()
            if clean_domain == allowed_clean or clean_domain.endswith("." + allowed_clean):
                return True
        return False

    def check_suspicious_url(self, url: str, allowed_domains: List[str]) -> Tuple[bool, str]:
        """Inspect a single URL for phishing or scam patterns."""
        domain = self.extract_domain(url)
        if not domain:
            return False, ""

        # Allow if in trusted allowlist
        if self.is_domain_allowed(domain, allowed_domains):
            return False, ""

        url_lower = url.lower()

        # Check phishing keywords
        for kw in PHISHING_URL_KEYWORDS:
            if kw in url_lower:
                return True, f"Suspicious phishing link keyword detected ({kw}) in domain '{domain}'"

        # Check suspicious TLDs often used for one-off throwaway scam links
        for sus_tld in [".xyz", ".top", ".buzz", ".zip", ".mov", ".cfd", ".monster"]:
            if domain.endswith(sus_tld):
                # Check if it also has crypto or wallet words
                if any(w in url_lower for w in ["claim", "airdrop", "mint", "wallet", "free", "moon"]):
                    return True, f"Suspicious TLD with crypto lure: '{domain}'"

        return False, ""

    def check_file_extension(self, filename: Optional[str]) -> Tuple[bool, str]:
        """Check if file has an unsafe executable or script extension."""
        if not filename:
            return False, ""
        fn_lower = filename.lower()
        for ext in PROHIBITED_EXTENSIONS:
            if fn_lower.endswith(ext):
                return True, f"Prohibited executable/script file type ({ext})"
        return False, ""

    def check_scam_text(self, text: str) -> Tuple[bool, str]:
        """Check text against known spam/scam patterns."""
        if not text:
            return False, ""
        for regex in self.scam_regexes:
            if regex.search(text):
                return True, "Unsolicited crypto scam / referral solicitation pattern detected"

        # Check for invite link spam to external groups
        if "t.me/+" in text or "t.me/joinchat/" in text:
            return True, "Unauthorized Telegram invite link spam detected"

        return False, ""

    def check_mass_mentions(self, text: str) -> Tuple[bool, str]:
        """Detect mass mention abuse (@user @user @user...)."""
        if not text:
            return False, ""
        mentions = re.findall(r"@\w+", text)
        if len(mentions) >= 5:
            return True, f"Mass mention abuse ({len(mentions)} mentions in single message)"
        return False, ""

    def check_impersonation(self, user_name: Optional[str], is_admin: bool = False) -> Tuple[bool, str]:
        """Check if user display name mimics admin or official support."""
        if is_admin or not user_name:
            return False, ""

        name_lower = user_name.lower()
        for kw in IMPERSONATION_KEYWORDS:
            if kw in name_lower:
                return True, f"Potential impersonation: user name contains '{kw}'"

        return False, ""

    async def inspect_message(
        self,
        chat_id: int,
        user_id: int,
        text: Optional[str],
        user_name: Optional[str],
        filename: Optional[str],
        allowed_domains: List[str],
        is_chat_admin: bool = False,
    ) -> SpamCheckResult:
        """Run all moderation checks on an incoming message."""
        # Chat administrators bypass automatic content filtering
        if is_chat_admin:
            return SpamCheckResult(is_violation=False)

        # 1. Impersonation check
        is_imp, imp_reason = self.check_impersonation(user_name, is_chat_admin)
        if is_imp:
            return SpamCheckResult(
                is_violation=True,
                reason=imp_reason,
                action_type="warn",
                severity="medium",
            )

        # 2. Prohibited file extension
        is_bad_file, file_reason = self.check_file_extension(filename)
        if is_bad_file:
            return SpamCheckResult(
                is_violation=True,
                reason=file_reason,
                action_type="delete",
                severity="high",
            )

        # If there's text, perform text & link checks
        if text:
            # 3. Message flood check
            if await self.check_flood(chat_id, user_id):
                return SpamCheckResult(
                    is_violation=True,
                    reason="Message flooding (too many messages in short time)",
                    action_type="mute",
                    severity="medium",
                )

            # 4. Duplicate spam check
            if await self.check_duplicate_spam(chat_id, user_id, text):
                return SpamCheckResult(
                    is_violation=True,
                    reason="Repeated duplicate copy-paste spam",
                    action_type="delete",
                    severity="low",
                )

            # 5. Mass mentions
            is_mass_m, mm_reason = self.check_mass_mentions(text)
            if is_mass_m:
                return SpamCheckResult(
                    is_violation=True,
                    reason=mm_reason,
                    action_type="delete",
                    severity="medium",
                )

            # 6. Text scam / solicitation pattern
            is_scam, scam_reason = self.check_scam_text(text)
            if is_scam:
                return SpamCheckResult(
                    is_violation=True,
                    reason=scam_reason,
                    action_type="delete",
                    severity="high",
                )

            # 7. URL & Phishing check
            urls = self.extract_urls(text)
            for url in urls:
                is_phish, phish_reason = self.check_suspicious_url(url, allowed_domains)
                if is_phish:
                    return SpamCheckResult(
                        is_violation=True,
                        reason=phish_reason,
                        action_type="delete",
                        severity="high",
                    )

        return SpamCheckResult(is_violation=False)


antispam_service = AntiSpamService()
