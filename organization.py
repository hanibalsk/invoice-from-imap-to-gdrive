import json
import os

import PyPDF2
import openai
from PyPDF2.errors import PdfReadError
from openai import OpenAI
from sqlalchemy import and_

from db_email import Db, ImportedEmail
from pdf_processor import PDFProcessor


class OrganizationDetector:
    def __init__(self, db_url='sqlite:///emails.db', openai_api_key='your_openai_api_key', pdf_passwords=None):
        self.db = Db(db_url)
        openai.api_key = openai_api_key
        self.client = OpenAI(api_key=openai_api_key)
        self.pdf_passwords = pdf_passwords if pdf_passwords else []
        self.organization_cache = {}
        self.pdf_processor = PDFProcessor(pdf_passwords)

    def get_emails_with_pdf_attachments(self):
        with self.db.get_session() as session:
            emails = session.query(ImportedEmail).filter(
                and_(ImportedEmail.has_attachment == True, ImportedEmail.attachment_path.like('%.pdf'),
                     ImportedEmail.sender_organisation == None)
            ).all()
            return emails

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                if reader.is_encrypted:
                    for password in self.pdf_passwords:
                        try:
                            reader.decrypt(password)
                            break
                        except NotImplementedError:
                            print(f"PyCryptodome is required for AES algorithm. Unable to decrypt PDF {pdf_path}.")
                            return text
                        except PdfReadError:
                            continue
                    else:
                        print(f"Unable to decrypt PDF {pdf_path} with provided passwords.")
                        return text
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
        return text

    def detect_organization_and_spam(self, email_from, text, body):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You will receive PDF content and sender information. "
                                   "Extract the organization name and determine if the email is spam or not and "
                                   "determine probability that PDF content is invoice "
                                   "('DANOVE PRIZNANIE' is not invoice) "
                                   "promotional in JSON format: "
                                   "{ \"organization\": \"XYZ\", spam: \"No\", \"invoice\": 0.8 }"
                    },
                    {
                        "role": "user",
                        "content": f"Sender: {email_from}\nEmail body: {body}\nPDF content: {text[:2000]}"
                    },
                ],
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error detecting organization and spam status: {e}")
            return None

    def update_emails_with_organization(self):
        emails = self.get_emails_with_pdf_attachments()
        with self.db.get_session() as session:
            for email in emails:
                pdf_path = email.attachment_path
                if os.path.exists(pdf_path):
                    # Check if organization info is already in the cache
                    if email.sender in self.organization_cache:
                        cached_data = self.organization_cache[email.sender]
                        email.sender_organisation = cached_data['organization']
                        email.is_spam = cached_data['is_spam']
                        session.add(email)
                        print(
                            f"Updated email ID {email.id} with cached organization: {email.sender_organisation}, spam status: {email.is_spam}")
                        continue

                    pdf_text = self.pdf_processor.extract_text_from_pdf(pdf_path)
                    if pdf_text:
                        detection_result = self.detect_organization_and_spam(email.sender, pdf_text, email.body)
                        if detection_result:
                            # Assuming detection_result returns something like "Organization: XYZ, Spam: No"
                            try:
                                print(detection_result)
                                # parse detection_result as json data
                                # Trim all characters before the first `{` and after the last `}`
                                start_index = detection_result.index("{")
                                end_index = detection_result.rindex("}") + 1
                                cleaned_data = detection_result[start_index:end_index]

                                json_data = json.loads(cleaned_data)
                                organization = json_data['organization']
                                spam_status = json_data['spam']
                                invoice_probability = json_data['invoice']

                                email.sender_organisation = organization
                                email.is_spam = spam_status.strip().lower() == "yes"
                                if invoice_probability > 0.6:
                                    email.is_invoice = True
                                else:
                                    email.is_invoice = False

                                # Store the result in the cache
                                self.organization_cache[email.sender] = {
                                    'organization': email.sender_organisation,
                                    'is_spam': email.is_spam,
                                    'is_invoice': email.is_invoice
                                }
                                session.add(email)
                                print(
                                    f"Updated email ID {email.id} with organization: {email.sender_organisation}, spam status: {email.is_spam}")
                            except ValueError:
                                print(f"Unexpected response format for email ID {email.id}: {detection_result}")
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Error updating emails in database: {e}")

