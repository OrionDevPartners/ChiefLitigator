"""Beta invite email sender.

Sends credentials to newly approved beta users. Uses AWS SES when
SES_SENDER_EMAIL is configured, otherwise logs to console for
development environments.

All configuration from environment variables (CPAA-compliant).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("cyphergy.beta.email")


async def send_beta_invite(email: str, name: str, password: str) -> bool:
    """Send beta invite email with credentials.

    Uses AWS SES if SES_SENDER_EMAIL and SES_REGION are set in the
    environment. Otherwise falls back to console logging for local
    development.

    The password is included in the email body but is NEVER logged.

    Args:
        email: Recipient email address.
        name: Recipient display name.
        password: Generated plaintext password for the invite.

    Returns:
        True if the email was sent (or logged) successfully, False on error.
    """
    ses_sender = os.getenv("SES_SENDER_EMAIL", "")
    ses_region = os.getenv("SES_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    subject = "Welcome to Cyphergy Beta"
    body_text = (
        f"Hello {name},\n\n"
        f"You have been invited to the Cyphergy Beta program.\n\n"
        f"Your credentials:\n"
        f"  Email: {email}\n"
        f"  Password: {password}\n\n"
        f"Please log in at https://cyphergy.ai and change your password after first login.\n\n"
        f"Important: Your account will be locked to the IP address of your first login. "
        f"Subsequent logins from a different IP will be denied.\n\n"
        f"-- Cyphergy Team"
    )

    if ses_sender:
        return await _send_via_ses(
            sender=ses_sender,
            recipient=email,
            subject=subject,
            body_text=body_text,
            region=ses_region,
        )

    # Fallback: log to console (development mode)
    logger.info(
        "beta_invite_email | recipient=%s name=%s (console mode -- SES not configured)",
        email,
        name,
    )
    # Log that an invite was generated but NEVER log the password
    logger.info("beta_invite_ready | email=%s -- credentials generated", email)
    return True


async def _send_via_ses(
    sender: str,
    recipient: str,
    subject: str,
    body_text: str,
    region: str,
) -> bool:
    """Send email via AWS SES.

    Uses boto3 SES client. AWS credentials are sourced from the
    environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) or
    IAM role (when running on ECS/Fargate).

    Args:
        sender: Sender email address (must be SES-verified).
        recipient: Recipient email address.
        subject: Email subject line.
        body_text: Plain text email body.
        region: AWS region for SES.

    Returns:
        True on success, False on error.
    """
    try:
        import boto3

        client = boto3.client("ses", region_name=region)
        client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("beta_invite_sent_ses | recipient=%s", recipient)
        return True

    except ImportError:
        logger.error("beta_email_boto3_missing | boto3 not installed -- cannot send via SES")
        return False
    except Exception as exc:
        logger.error("beta_email_ses_error | recipient=%s error=%s", recipient, str(exc)[:200])
        return False
