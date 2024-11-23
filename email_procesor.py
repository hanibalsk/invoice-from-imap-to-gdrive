import email
import imaplib
import logging
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from email.header import decode_header, make_header

from sqlalchemy.exc import SQLAlchemyError

from db_email import ImportedEmail, Db


class EmailProcessor:
    def __init__(self, imap_server, email_address, password, db, save_path="attachments", year=None, month=None, skip=None):
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.save_path = save_path
        self.year = year
        self.month = month
        self.imap = None
        self.skip = skip if skip else 0
        self.db = db

    def connect(self):
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_address, self.password)
        except Exception as e:
            print(f"An error occurred while connecting: {e}")

    def decode_subject(self, subject):
        if subject:
            try:
                return str(make_header(decode_header(subject)))
            except Exception as e:
                print(f"Failed to decode subject due to encoding issue: {e}")
                return "(Error decoding subject)"
        return ""

    # Function to display progress in one line
    def show_progress_inline(self,current, total):
        progress = (current / total) * 100
        sys.stdout.write(f"\rProgress: {current}/{total} ({progress:.2f}%)")
        sys.stdout.flush()

    def get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get_content_disposition())

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
        return ""

    def save_attachment(self, part, filename, sender):
        unique_filename = f"{uuid.uuid4()}_{sender}_{filename}"
        filepath = os.path.join(self.save_path, unique_filename)
        with open(filepath, "wb") as f:
            f.write(part.get_payload(decode=True))
        return filepath

    def process_email_message(self, msg, session, email_id=None):
        try:
            subject = self.decode_subject(msg.get("Subject"))
            sender = msg.get("From")
            date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            email_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)) if date_tuple else datetime.now()

            is_spam = "***SPAM***" in subject
            has_attachment = False
            attachment_path = None
            body = self.get_email_body(msg)

            return_path = str(msg.get("Return-Path")) if msg.get("Return-Path") else None
            envelope_to = str(msg.get("Envelope-To")) if msg.get("Envelope-To") else None
            delivery_date_str = msg.get("Delivery-date")
            delivery_date = datetime.strptime(delivery_date_str,
                                              "%a, %d %b %Y %H:%M:%S %z") if delivery_date_str else None
            received_from = str(msg.get("Received")) if msg.get("Received") else None
            dkim_signature = str(msg.get("DKIM-Signature")) if msg.get("DKIM-Signature") else None
            spam_status = str(msg.get("X-Spam-Status")) if msg.get("X-Spam-Status") else None
            spam_report = str(msg.get("X-Spam-Report")) if msg.get("X-Spam-Report") else None

            # Filter by year and month if specified
            if self.year and delivery_date.year != self.year:
                # print(
                #     f"Skipping email with ID {email_id} as it is not from the specified year({self.year}) {delivery_date}.")
                return
            if self.month and delivery_date.month != self.month:
                # print(
                #     f"Skipping email with ID {email_id} as it is not from the specified month({self.month}) {delivery_date}.")
                return

            # print(
            #     f"Processing email with ID {email_id} year={self.year}({delivery_date.year}) month={self.month}({delivery_date.month}); {delivery_date}")

            # Check for attachments
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_disposition() == "attachment":
                        filename = part.get_filename()
                        if filename and filename.endswith(".pdf"):
                            has_attachment = True
                            attachment_path = self.save_attachment(part, filename, sender)
                            # print(f"Attachment saved: {attachment_path}")

            # Save email details to the database
            email_instance = ImportedEmail(
                imap_account=self.email_address,
                subject=subject,
                sender=sender,
                sender_organisation=None,
                date=email_date,
                is_spam=is_spam,
                has_attachment=has_attachment,
                body=body,
                attachment_path=attachment_path,
                return_path=return_path,
                envelope_to=envelope_to,
                delivery_date=delivery_date,
                received_from=received_from,
                dkim_signature=dkim_signature,
                spam_status=spam_status,
                spam_report=spam_report
            )
            session.add(email_instance)
            session.commit()
            logging.debug(f"\nProcessed and saved email with date ({delivery_date}): {subject}")
            # print(f"Processed and saved email with date ({delivery_date}): {subject}")
        except LookupError as e:
            print(f"An error occurred while processing email with ID {email_id}: {e}")
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Database error while processing email with ID {email_id}: {e}")

    def process_emails(self):
        try:
            logging.info(f"Processing emails for {self.email_address}...\n")
            # Select the mailbox (e.g., INBOX)
            self.imap.select("INBOX")

            # Search for all emails in the mailbox
            status, messages = self.imap.search(None, "ALL")
            if status != "OK":
                print("No emails found!")
                return

            # Create a directory to save attachments
            os.makedirs(self.save_path, exist_ok=True)

            # Process emails
            with self.db.get_session() as session:
                email_ids = messages[0].split()
                total_emails = len(email_ids)
                for i, num in enumerate(email_ids[self.skip:], start=self.skip+1):
                    status, msg_data = self.imap.fetch(num, "(RFC822)")
                    if status != "OK":
                        print(f"Failed to fetch email with ID {num}")
                        continue

                    # Parse the email
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            self.process_email_message(msg, session, email_id=num.decode('utf-8'))
                    # Update progress inline
                    self.show_progress_inline(i, total_emails)
        except Exception as e:
            print(f"An error occurred while processing emails: {e}")
        finally:
            print("\n")
            logging.info(f"Email processing for {self.email_address} complete.")

    def import_email_by_id(self, email_id):
        try:
            # Select the mailbox (e.g., INBOX)
            self.imap.select("INBOX")

            # Fetch the email by ID
            status, msg_data = self.imap.fetch(email_id, "(RFC822)")
            if status != "OK":
                print(f"Failed to fetch email with ID {email_id}")
                return

            # Create a directory to save attachments
            os.makedirs(self.save_path, exist_ok=True)

            # Parse the email
            with self.db.get_session() as session:
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        self.process_email_message(msg, session, email_id=email_id)
        except Exception as e:
            print(f"An error occurred while importing email by ID: {e}")

    def close_connection(self):
        if self.imap:
            self.imap.close()
            self.imap.logout()


class ImportEmails:
    def __init__(self, email_accounts, save_path, database_url='sqlite:///emails.db'):
        self.email_accounts = email_accounts
        self.save_path = save_path
        self.db = Db(database_url)


    @contextmanager
    def connect(self, year=None, month=None):
        email_processors = []
        try:
            for email_account in self.email_accounts:
                imap_server = email_account["account"]["imap_server"]
                email_address = email_account["account"]["email_address"]
                password = email_account["account"]["password"]
                skip = email_account["account"].get("skip", 0)

                logging.info(f"Connecting to {email_address}...")
                email_processor = EmailProcessor(imap_server, email_address, password, self.db, save_path=self.save_path,
                                                 year=year, month=month, skip=skip)
                email_processor.connect()
                email_processors.append(email_processor)
            yield email_processors
        finally:
            for email_processor in email_processors:
                email_processor.close_connection()

    def import_emails(self, year=None, month=None):
        with self.connect(year, month) as email_processors:
            for email_processor in email_processors:
                email_processor.process_emails()
