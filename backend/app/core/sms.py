"""
SMS delivery via the Twilio Messages API.

Credentials come from the environment. When they are absent the service is a
no-op so local development and tests never hit the network.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsService:
    @property
    def enabled(self) -> bool:
        return bool(
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_API_KEY_SID
            and settings.TWILIO_API_KEY_SECRET
            and settings.TWILIO_SMS_FROM
        )

    async def send(self, *, to_number: str, body: str) -> bool:
        if not self.enabled:
            logger.info("SMS delivery disabled; skipping message to %s", to_number)
            return False

        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    data={"To": to_number, "From": settings.TWILIO_SMS_FROM, "Body": body},
                    auth=(settings.TWILIO_API_KEY_SID, settings.TWILIO_API_KEY_SECRET),
                )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            # Never fail registration because of a carrier/provider outage.
            logger.error("Failed to send SMS to %s: %s", to_number, exc)
            return False

    async def send_verification_code(self, *, to_number: str, code: str) -> bool:
        return await self.send(
            to_number=to_number,
            body=f"Your Agro Future verification code is {code}. It expires in "
            f"{settings.MOBILE_CODE_TTL_MINUTES} minutes.",
        )


sms_service = SmsService()
