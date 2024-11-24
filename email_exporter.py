import logging
import os
import shutil
from datetime import datetime

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from sqlalchemy import and_

from db_email import ImportedEmail, Db


class EmailOrganizer:
    def __init__(self, db_url='sqlite:///emails.db', base_dir='organized_emails', root_folder_id=None,
                 settings_file='settings.yaml'):
        self.base_dir = base_dir
        self.root_folder_id = root_folder_id  # Google Drive root folder ID
        self.db = Db(db_url)
        self.gauth = GoogleAuth(settings_file=settings_file)
        self.gauth.LocalWebserverAuth()  # Authenticate user
        self.drive = GoogleDrive(self.gauth)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("EmailOrganizer initialized with base directory: %s and root folder ID: %s", self.base_dir,
                         self.root_folder_id)

    def get_emails(self):
        # Retrieve emails with attachments that have not been processed yet
        with self.db.Session() as session:
            emails = session.query(ImportedEmail).filter(
                and_(ImportedEmail.has_attachment == True, ImportedEmail.attachment_path.like('%.pdf'),
                     ImportedEmail.sender_organisation != None, ImportedEmail.processed_path == None)
            ).all()
            self.logger.info("Retrieved %d emails with attachments to process", len(emails))
            return emails

    def categorize_emails(self, batch_size=10):
        # Get a limited number of emails to process
        emails = self.get_emails()[:batch_size]
        self.logger.info("Categorizing %d emails", len(emails))
        with self.db.Session() as session:
            for email in emails:
                # Use the email date or current date if none is available
                email_date = email.date or datetime.now()
                organization = email.sender_organisation or 'Unknown'  # Default to 'Unknown' if no organization is found
                month_name = email_date.strftime('%B')  # Get the month name from the email date
                year = email_date.year  # Get the year from the email date

                # Create directory structure path/to/dir/2024/October/{Organization}/
                organization_dir = os.path.join(self.base_dir, str(year), month_name, organization)
                os.makedirs(organization_dir, exist_ok=True)  # Create the directory if it doesn't exist
                self.logger.info("Created directory: %s", organization_dir)

                # Copy the PDF attachment to the appropriate directory
                if email.attachment_path and os.path.exists(email.attachment_path):
                    destination_path = os.path.join(organization_dir, os.path.basename(email.attachment_path))
                    shutil.copy2(email.attachment_path, destination_path)  # Copy the file to the destination
                    email.processed_path = destination_path  # Update the processed path in the database
                    email.uploaded = False  # Mark as not yet uploaded
                    session.add(email)  # Add the email record to the session
                    self.logger.info("Copied %s to %s", email.attachment_path, destination_path)
            session.commit()  # Commit the changes to the database
            self.logger.info("Categorization of emails completed and changes committed to the database")

    def upload_to_google_drive(self, local_path, parent_folder_id=None):
        parent_folder_id = parent_folder_id or self.root_folder_id  # Use the provided root folder ID

        if os.path.isdir(local_path):
            return
        else:
            # If the local path is a file, upload it to Google Drive
            file_name = os.path.basename(local_path)
            file_metadata = {
                'title': file_name
            }
            # get all directories in the path from local_path
            parent_folder_structure = local_path.split(os.sep)[1:-1]

            # create folder structure in google drive from parent_folder_structure, but first check if the folder already exists
            for folder in parent_folder_structure:
                folder_exists = False
                file_list = self.drive.ListFile({'q': "'%s' in parents and trashed=false" % parent_folder_id}).GetList()
                for file in file_list:
                    if file['title'] == folder:
                        parent_folder_id = file['id']
                        folder_exists = True
                        break
                if not folder_exists:
                    folder_metadata = {
                        'title': folder,
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    if parent_folder_id:
                        folder_metadata['parents'] = [{'id': parent_folder_id}]
                    folder = self.drive.CreateFile(folder_metadata)
                    folder.Upload()
                    # get the id of the created folder
                    parent_folder_id = folder['id']

            if parent_folder_id:
                file_metadata['parents'] = [{'id': parent_folder_id}]
            file = self.drive.CreateFile(file_metadata)
            file.SetContentFile(local_path)  # Set the content of the file to be uploaded
            file.Upload()  # Upload the file to Google Drive
            self.logger.info("Uploaded file %s to Google Drive", local_path)

    def organize_and_upload(self, batch_size=10):
        parent_folder_structure = ''
        # Categorize emails and then upload them to Google Drive
        self.logger.info("Starting organization and upload process for %d emails", batch_size)
        self.categorize_emails(batch_size=batch_size)
        with self.db.Session() as session:
            # Retrieve emails that have been processed but not yet uploaded
            emails = session.query(ImportedEmail).filter(
                and_(ImportedEmail.processed_path != None, ImportedEmail.uploaded == False)
            ).all()
            self.logger.info("Retrieved %d emails to upload to Google Drive", len(emails))
            for email in emails:
                if os.path.exists(email.processed_path):
                    # Upload the processed file to Google Drive
                    self.logger.info("Uploading processed file: %s", email.processed_path)
                    self.upload_to_google_drive(email.processed_path, self.root_folder_id)
                    email.uploaded = True  # Mark as uploaded
                    session.add(email)  # Add the updated email record to the session
                    session.commit()  # Commit the changes to the database
            self.logger.info("Upload process completed and changes committed to the database")
