import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, email_address: str, app_password: str, imap_server: str = "imap.gmail.com", smtp_server: str = "smtp.gmail.com"):
        """
        Initialize the EmailService with credentials and server details.
        """
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = imap_server
        self.smtp_server = smtp_server

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server."""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.app_password)
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            raise

    def fetch_unread_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from the Inbox.
        Returns a list of dictionaries containing email data.
        """
        mail = self.connect_imap()
        emails_data = []

        try:
            mail.select("inbox")
            # Search for all unread emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("No messages found or error searching.")
                return []

            email_ids = messages[0].split()
            # Process strictly the last 'limit' emails to avoid overload
            for e_id in email_ids[-limit:]:
                status, msg_data = mail.fetch(e_id, '(RFC822)')
                if status != 'OK':
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Extract basic headers
                        subject = self._decode_header(msg.get("Subject"))
                        sender = msg.get("From")
                        date = msg.get("Date")
                        message_id = msg.get("Message-ID")
                        references = msg.get("References", "")
                        in_reply_to = msg.get("In-Reply-To", "")

                        # Extract body
                        body = self._get_email_body(msg)

                        emails_data.append({
                            "id": e_id.decode(),
                            "message_id": message_id,
                            "subject": subject,
                            "sender": sender,
                            "date": date,
                            "body": body,
                            "references": references,
                            "in_reply_to": in_reply_to
                        })
            
            return emails_data

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass

    def send_email(self, to_email: str, subject: str, body: str, in_reply_to: str = None, references: str = None):
        """
        Send an email via SMTP. 
        Supports threading if 'in_reply_to' and 'references' are provided.
        """
        msg = MIMEMultipart()
        msg['From'] = self.email_address
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Threading headers
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL(self.smtp_server, 465) as server:
                server.login(self.email_address, self.app_password)
                server.send_message(msg)
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def create_draft(self, to_email: str, subject: str, body: str, in_reply_to: str = None, references: str = None):
        """
        Create a draft email in Gmail.
        Note: Standard SMTP/IMAP does not strictly 'create draft' in the same way the Gmail API does.
        However, checking Gmail via IMAP, we can Append to the [Gmail]/Drafts folder.
        """
        msg = MIMEMultipart()
        msg['From'] = self.email_address
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = formataddr((self.email_address, datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")))
        
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        msg.attach(MIMEText(body, 'plain'))
        
        mail = self.connect_imap()
        try:
            # Gmail specific: Drafts folder is usually "[Gmail]/Drafts"
            # We might need to handle localization or folder listing to be robust, 
            # but this is the standard English folder name.
            mail.append('"[Gmail]/Drafts"', None, imaplib.Time2Internaldate(datetime.now()), msg.as_bytes())
            logger.info(f"Draft created for {to_email}")
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            raise
        finally:
            try:
                mail.logout()
            except:
                pass

    def _decode_header(self, header_value):
        """Helper to decode email headers."""
        if not header_value:
            return ""
        decoded_list = email.header.decode_header(header_value)
        decoded_str = ""
        for token, encoding in decoded_list:
            if isinstance(token, bytes):
                if encoding:
                    decoded_str += token.decode(encoding)
                else:
                    decoded_str += token.decode('utf-8', errors='ignore')
            else:
                decoded_str += str(token)
        return decoded_str

    def _get_email_body(self, msg):
        """Helper to extract plain text body."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                         body = part.get_payload(decode=True).decode(errors='ignore')
                         break # Prefer plain text
                    elif content_type == "text/html" and not body:
                         # Fallback to HTML if no plain text found so far
                         # In a real app we might want to strip HTML tags here
                         body = part.get_payload(decode=True).decode(errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        return body
