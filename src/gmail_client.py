import imaplib
import smtplib
import email
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GmailClient:
    """
    A robust client for interacting with Gmail via IMAP and SMTP.
    Handles connection management, threading headers, and draft creation.
    """

    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self._imap_conn: Optional[imaplib.IMAP4_SSL] = None

    def _ensure_imap_connection(self):
        """Ensure active IMAP connection."""
        try:
            if self._imap_conn is None:
                self._connect_imap()
            else:
                # Check strict status
                status = self._imap_conn.noop()[0]
                if status != 'OK':
                    self._connect_imap()
        except Exception:
            self._connect_imap()

    def _connect_imap(self):
        """Establish IMAP connection."""
        logger.info("Connecting to IMAP...")
        self._imap_conn = imaplib.IMAP4_SSL(self.imap_server)
        self._imap_conn.login(self.email_address, self.app_password)

    def close(self):
        """Close IMAP connection gracefully."""
        if self._imap_conn:
            try:
                self._imap_conn.close()
                self._imap_conn.logout()
            except Exception as e:
                logger.warning(f"Error closing IMAP connection: {e}")
            finally:
                self._imap_conn = None

    def fetch_unread_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch unread emails with full threading context.
        """
        self._ensure_imap_connection()
        emails = []
        
        try:
            self._imap_conn.select("inbox")
            # Use UID SEARCH to get UIDs instead of sequence numbers
            status, messages = self._imap_conn.uid('search', None, 'UNSEEN')
            
            if status != 'OK' or not messages[0]:
                logger.info("No unread messages found.")
                return []

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread emails. Fetching last {limit}...")
            # Process strictly the recent ones
            for e_id in email_ids[-limit:]:
                # Use UID FETCH
                res, msg_data = self._imap_conn.uid('fetch', e_id, '(RFC822)')
                if res != 'OK':
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Parse headers
                subject = self._decode_header(msg.get("Subject", ""))
                sender = msg.get("From")
                msg_id = msg.get("Message-ID")
                references = msg.get("References", "")
                in_reply_to = msg.get("In-Reply-To", "")
                date_str = msg.get("Date")

                body = self._get_email_body(msg)

                emails.append({
                    "id": e_id.decode(),
                    "message_id": msg_id,
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "body": body,
                    "references": references,
                    "in_reply_to": in_reply_to
                })
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            raise

        return emails

    def send_email(self, to_email: str, subject: str, body: str, 
                   reference_msg_id: str = None, 
                   reference_chain: str = None,
                   mode: str = "draft") -> bool:
        """
        Send an email or save as draft.
        
        Args:
            mode: 'send' or 'draft'
            reference_msg_id: The Message-ID of the email we are replying to.
            reference_chain: The existing References string.
        """
        msg = MIMEMultipart()
        msg['From'] = self.email_address
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = formataddr((self.email_address, datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")))
        msg['Message-ID'] = make_msgid()

        # Handle Threading
        if reference_msg_id:
            msg['In-Reply-To'] = reference_msg_id
            # Append new ref to chain
            new_references = f"{reference_chain} {reference_msg_id}" if reference_chain else reference_msg_id
            msg['References'] = new_references.strip()

        msg.attach(MIMEText(body, 'plain'))

        if mode == "send":
            return self._smtp_send(to_email, msg)
        elif mode == "draft":
            return self._imap_save_draft(msg)
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _smtp_send(self, to_email: str, msg: Message) -> bool:
        """Send via SMTP."""
        try:
            with smtplib.SMTP_SSL(self.smtp_server, 465) as server:
                server.login(self.email_address, self.app_password)
                server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP Send Failed: {e}")
            return False

    def _imap_save_draft(self, msg: Message) -> bool:
        """Save to [Gmail]/Drafts via IMAP."""
        self._ensure_imap_connection()
        try:
            # Note: Gmail special folder. 
            # Ideally we should list folders to find the drafts one, but this is standard.
            import time
            self._imap_conn.append('"[Gmail]/Drafts"', None, imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            logger.info("Email saved to Drafts.")
            return True
        except Exception as e:
            logger.error(f"Failed to save draft: {e}")
            return False

    def add_label(self, email_uid: str, label: str):
        """
        Add a label to an email (IMAP Copy + Delete or X-GM-LABELS).
        Note: Standard IMAP doesn't support 'Labels' directly, only Folders.
        Gmail IMAP extensions support X-GM-LABELS.
        """
        self._ensure_imap_connection()
        try:
             # Use Gmail extension to add label
             # Check if we are selected
             self._imap_conn.select("inbox")
             
             # Attempt to CREATE label first (idempotent usually, or catch error)
             try:
                 self._imap_conn.create(label)
             except Exception:
                 pass # Label likely exists
                 
             # STORE command with +X-GM-LABELS
             # Note: X-GM-LABELS requires the label name, sometimes quoted
             resp, data = self._imap_conn.uid('STORE', email_uid, '+X-GM-LABELS', f'({label})')
             if resp == 'OK':
                 logger.info(f"Added label {label} to email {email_uid}")
             else:
                 logger.warning(f"Failed to add label {label}: {data}")
        except Exception as e:
             logger.error(f"Error adding label: {e}")

    def archive_email(self, email_uid: str):
        """Archive email by removing from Inbox (Gmail behavior)."""
        self._ensure_imap_connection()
        try:
            # In Gmail, "Archiving" is just removing the "Inbox" label.
            # But via standard IMAP, we might need to move it to "All Mail" or just delete from "Inbox".
            # The safest way is to specificly delete the Inbox label if using X-GM-LABELS, 
            # Or just 'Message Delete' if the server keeps it in All Mail. 
            # Standard 'Deleted' flag in Gmail usually Archives if 'Expunge' is called.
            
            self._imap_conn.select("inbox")
            self._imap_conn.uid('STORE', email_uid, '+FLAGS', '(\\Deleted)')
            self._imap_conn.expunge()
            logger.info(f"Archived email {email_uid}")
        except Exception as e:
            logger.error(f"Error archiving: {e}")

    def _decode_header(self, header_val):
        """Decode MIME encoded headers."""
        if not header_val: return ""
        decoded_list = email.header.decode_header(header_val)
        text = ""
        for token, encoding in decoded_list:
            if isinstance(token, bytes):
                text += token.decode(encoding or 'utf-8', errors='ignore')
            else:
                text += str(token)
        return text

    def _get_email_body(self, msg: Message) -> str:
        """Extract plain text body recursively."""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get("Content-Disposition"))
                if ctype == 'text/plain' and 'attachment' not in cdisp:
                    return part.get_payload(decode=True).decode(errors='ignore')
            # Fallback to HTML if no plain
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/html':
                    # TODO: Strip HTML tags for cleaner processing
                    return part.get_payload(decode=True).decode(errors='ignore')
        else:
            return msg.get_payload(decode=True).decode(errors='ignore')
        return ""
