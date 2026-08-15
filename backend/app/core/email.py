"""
Transactional email delivery via the Twilio Emails API.

Credentials are read from the environment (never hardcoded). If they are not
configured the service becomes a no-op so local development and tests can run
without sending real email.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TWILIO_EMAILS_URL = "https://comms.twilio.com/v1/Emails"


class EmailService:
    @property
    def enabled(self) -> bool:
        return bool(
            settings.TWILIO_API_KEY_SID
            and settings.TWILIO_API_KEY_SECRET
            and settings.EMAIL_FROM_ADDRESS
        )

    async def send(self, *, to_address: str, subject: str, html: str, text: str) -> bool:
        """Send one email. Returns False if disabled or the API call failed."""
        if not self.enabled:
            logger.info("Email delivery disabled; skipping email to %s", to_address)
            return False

        payload = {
            "from": {
                "address": settings.EMAIL_FROM_ADDRESS,
                "name": settings.EMAIL_FROM_NAME,
            },
            "to": [{"address": to_address}],
            "content": {"subject": subject, "html": html, "text": text},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    TWILIO_EMAILS_URL,
                    json=payload,
                    auth=(settings.TWILIO_API_KEY_SID, settings.TWILIO_API_KEY_SECRET),
                )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            # Never fail registration because of a mail provider outage.
            logger.error("Failed to send email to %s: %s", to_address, exc)
            return False

    async def send_verification_email(self, *, to_address: str, token: str) -> bool:
        link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
        return await self.send(
            to_address=to_address,
            subject="Verify your Agro Future account",
            html=(
                "<p>Welcome to Agro Future.</p>"
                f'<p><a href="{link}">Click here to verify your email address</a>.</p>'
                "<p>If you did not create this account, you can ignore this email.</p>"
            ),
            text=f"Welcome to Agro Future. Verify your email address: {link}",
        )


email_service = EmailService()
