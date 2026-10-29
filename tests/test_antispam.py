"""Tests for Anti-Spam and Phishing detection engine."""

import pytest
from memetek.services.antispam import AntiSpamService
from memetek.services.cache import cache





@pytest.mark.asyncio
async def test_prohibited_extensions():
    """Verify dangerous file types are detected."""
    svc = AntiSpamService()

    bad_files = ["crypto_drainer.exe", "airdrop_claim.bat", "wallet_bot.apk", "stealer.scr", "script.vbs", "payload.js"]
    for fn in bad_files:
        is_bad, reason = svc.check_file_extension(fn)
        assert is_bad is True, f"Failed to flag dangerous file: {fn}"
        assert "Prohibited" in reason

    safe_files = ["meme.png", "pepe.jpg", "tokenomics.pdf", "clip.mp4", "funny.gif"]
    for fn in safe_files:
        is_bad, reason = svc.check_file_extension(fn)
        assert is_bad is False


@pytest.mark.asyncio
async def test_phishing_url_detection():
    """Verify phishing links and malicious patterns are flagged while allowed domains pass."""
    svc = AntiSpamService()
    allowed_domains = ["t.me", "telegram.org", "coingecko.com", "dexscreener.com", "memetek.org"]

    # Allowed domains
    assert svc.is_domain_allowed("t.me", allowed_domains) is True
    assert svc.is_domain_allowed("app.memetek.org", allowed_domains) is True
    assert svc.is_domain_allowed("coingecko.com", allowed_domains) is True

    # Malicious links with phishing keywords
    phish_urls = [
        "https://claim-airdrop-memetek.xyz/connect",
        "https://free-mint-portal.top/claim",
        "http://wallet-connect-drainer.rest/auth",
        "https://token-claim-bonus.cfd",
    ]
    for url in phish_urls:
        is_phish, reason = svc.check_suspicious_url(url, allowed_domains)
        assert is_phish is True, f"Failed to detect phishing URL: {url}"

    # Legitimate URL from allowed domain
    safe_url = "https://coingecko.com/en/coins/pepe"
    is_phish, _ = svc.check_suspicious_url(safe_url, allowed_domains)
    assert is_phish is False


@pytest.mark.asyncio
async def test_scam_text_patterns():
    """Test recognition of unsolicited advertisements and scam phrases."""
    svc = AntiSpamService()

    scam_texts = [
        "Join now for guaranteed 100x profit on pump!",
        "DM me for signals and passive income daily",
        "Send 1 SOL to receive double back instantly!",
        "Earn $500 daily with our VIP automated bot",
        "Join our new VIP channel: t.me/+abc123secretlink",
    ]
    for txt in scam_texts:
        is_scam, reason = svc.check_scam_text(txt)
        assert is_scam is True, f"Failed to catch scam text: {txt}"

    clean_texts = [
        "Yo fam, what do you think of MEMETEK?",
        "GM legends, let's have a great day!",
        "Check out this hilarious meme I found.",
        "WAGMI brothers, holding strong! 🚀",
    ]
    for txt in clean_texts:
        is_scam, _ = svc.check_scam_text(txt)
        assert is_scam is False


@pytest.mark.asyncio
async def test_impersonation_detection():
    """Detect users impersonating admins or official support."""
    svc = AntiSpamService()

    assert svc.check_impersonation("MEMETEK Support Official")[0] is True
    assert svc.check_impersonation("Admin - Telegram Helpdesk")[0] is True
    assert svc.check_impersonation("Moderator Chad")[0] is True
    assert svc.check_impersonation("Security Team")[0] is True

    # Genuine regular user names
    assert svc.check_impersonation("CryptoKing2026")[0] is False
    assert svc.check_impersonation("DiamondHands42")[0] is False

    # Admins are exempt
    assert svc.check_impersonation("Official Admin", is_admin=True)[0] is False


@pytest.mark.asyncio
async def test_flood_detection():
    """Test message flood rate limiter."""
    svc = AntiSpamService()
    chat_id = -100999
    user_id = 77777

    # First few messages should pass
    for _ in range(4):
        is_flood = await svc.check_flood(chat_id, user_id)
        assert is_flood is False

    # 6th message exceeds FLOOD_MAX_MESSAGES (5)
    _ = await svc.check_flood(chat_id, user_id)
    is_flood = await svc.check_flood(chat_id, user_id)
    assert is_flood is True


@pytest.mark.asyncio
async def test_duplicate_spam_detection():
    """Test duplicate copy-paste message spam."""
    svc = AntiSpamService()
    chat_id = -100888
    user_id = 66666
    repeated_text = "BUY BUY BUY MOON MOON MOON"

    assert await svc.check_duplicate_spam(chat_id, user_id, repeated_text) is False
    assert await svc.check_duplicate_spam(chat_id, user_id, repeated_text) is False
    # 3rd identical message within 30s triggers duplicate spam
    assert await svc.check_duplicate_spam(chat_id, user_id, repeated_text) is True


@pytest.mark.asyncio
async def test_mass_mentions():
    """Test mass mention spam abuse."""
    svc = AntiSpamService()

    mass_text = "Hey @user1 @user2 @user3 @user4 @user5 check this out!"
    is_mass, reason = svc.check_mass_mentions(mass_text)
    assert is_mass is True
    assert "Mass mention" in reason

    normal_text = "Hey @user1 what do you think?"
    is_mass, _ = svc.check_mass_mentions(normal_text)
    assert is_mass is False
