"""
Environment Platform – Local Email provider.
"""

import os
import logging
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Dict, Any, List, Optional

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalEmailProvider(EnvironmentProvider):
    """
    Local email provider using SMTP and IMAP.
    """

    def __init__(self, secure_memory=None):
        self.secure_memory = secure_memory
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalEmailProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalEmailProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_email",
            domain=Domain.EMAIL,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Local email provider using SMTP/IMAP.",
            capabilities=[
                EnvironmentProviderCapability(
                    name="send",
                    description="Send an email",
                    parameters={"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                    returns={"message": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="list",
                    description="List recent emails",
                    parameters={"limit": {"type": "integer"}},
                    returns={"emails": {"type": "array"}}
                ),
                EnvironmentProviderCapability(
                    name="read",
                    description="Read a full email by ID",
                    parameters={"email_id": {"type": "string"}},
                    returns={"id": {"type": "string"}, "from": {"type": "string"}, "subject": {"type": "string"}, "date": {"type": "string"}, "body": {"type": "string"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["send", "list", "read"]

    def _decode_header(self, header):
        if header is None:
            return ""
        decoded = decode_header(header)
        result = []
        for part, encoding in decoded:
            if isinstance(part, bytes):
                try:
                    part = part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    part = part.decode('utf-8', errors='ignore')
            result.append(part)
        return ''.join(result)

    def _get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        return ""
                for part in msg.walk():
                    if part.get_content_type().startswith("text/"):
                        try:
                            return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            return ""
        else:
            try:
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                return ""
        return ""

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        try:
            if capability == "send":
                to = params.get('to') or params.get('recipient')
                subject = params.get('subject')
                body = params.get('body') or params.get('content')
                if not to or not subject or not body:
                    return {"error": "Missing 'to', 'subject', or 'body'"}

                smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
                smtp_port = int(os.getenv("EMAIL_PORT", 587))
                smtp_user = os.getenv("EMAIL_USER", "")
                smtp_password = os.getenv("EMAIL_PASSWORD", "")

                if not smtp_user or not smtp_password:
                    return {"error": "SMTP credentials not configured"}

                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = to
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                return {"message": f"Email sent to {to}"}

            elif capability == "list":
                imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
                imap_port = int(os.getenv("IMAP_PORT", 993))
                imap_user = os.getenv("EMAIL_USER", "")
                imap_password = os.getenv("EMAIL_PASSWORD", "")

                if not imap_user or not imap_password:
                    return {"error": "IMAP credentials not configured"}

                conn = imaplib.IMAP4_SSL(imap_host, imap_port)
                conn.login(imap_user, imap_password)
                conn.select("INBOX")
                limit = params.get('limit', 10)
                status, data = conn.search(None, "ALL")
                if status != "OK":
                    return {"error": "Failed to search emails"}
                email_ids = data[0].split()
                email_ids = email_ids[-limit:]

                emails = []
                for eid in reversed(email_ids):
                    status, msg_data = conn.fetch(eid, "(RFC822)")
                    if status != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = self._decode_header(msg.get("Subject", "No Subject"))
                    from_addr = self._decode_header(msg.get("From", "Unknown"))
                    date = msg.get("Date", "Unknown")
                    body = self._get_email_body(msg)[:500]
                    emails.append({
                        "id": eid.decode(),
                        "from": from_addr,
                        "subject": subject,
                        "date": date,
                        "body_preview": body[:200] + "..." if len(body) > 200 else body,
                    })
                conn.close()
                return {"emails": emails, "count": len(emails)}

            elif capability == "read":
                email_id = params.get('email_id')
                if not email_id:
                    return {"error": "Missing 'email_id'"}
                imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
                imap_port = int(os.getenv("IMAP_PORT", 993))
                imap_user = os.getenv("EMAIL_USER", "")
                imap_password = os.getenv("EMAIL_PASSWORD", "")
                if not imap_user or not imap_password:
                    return {"error": "IMAP credentials not configured"}

                conn = imaplib.IMAP4_SSL(imap_host, imap_port)
                conn.login(imap_user, imap_password)
                conn.select("INBOX")
                status, msg_data = conn.fetch(email_id.encode(), "(RFC822)")
                if status != "OK":
                    return {"error": f"Failed to fetch email {email_id}"}
                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header(msg.get("Subject", "No Subject"))
                from_addr = self._decode_header(msg.get("From", "Unknown"))
                date = msg.get("Date", "Unknown")
                body = self._get_email_body(msg)
                conn.close()
                return {
                    "id": email_id,
                    "from": from_addr,
                    "subject": subject,
                    "date": date,
                    "body": body,
                }

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalEmailProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
