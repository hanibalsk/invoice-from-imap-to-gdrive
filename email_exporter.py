import os
import shutil
from sqlalchemy import and_, update
from db_email import ImportedEmail, Db
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

class EmailOrganizer:
    def __init__(self, db_url='sqlite:///emails.db', base_dir='organized_emails', root_folder_id=None, settings_file='settings.yaml'):
        self.base_dir = base_dir
        self.root_folder_id = root_folder_id  # Google Drive root folder ID
        self.db = Db(db_url)
        self.gauth = GoogleAuth(settings_file=settings_file)
        self.gauth.LocalWebserverAuth()  # Authenticate user
        self.drive = GoogleDrive(self.gauth)
        self.chunk_size = 10 * 1024 * 1024  # 10 MB

    def get_emails(self):
        with self.db.Session() as session:
            emails = session.query(ImportedEmail).filter(
                and_(ImportedEmail.has_attachment == True, ImportedEmail.attachment_path.like('%.pdf'),
                     ImportedEmail.sender_organisation != None, ImportedEmail.processed_path == None)
            ).all()
            return emails

    def categorize_emails(self, process_count=10):
        emails = self.get_emails()[:process_count]
        with self.db.Session() as session:
            for email in emails:
                email_date = email.date or datetime.now()
                organization = email.sender_organisation or 'Unknown'
                month_name = email_date.strftime('%B')
                year = email_date.year

                # Create directory structure path/to/dir/2024/October/{Organization}/
                organization_dir = os.path.join(self.base_dir, str(year), month_name, organization)
                os.makedirs(organization_dir, exist_ok=True)

                # Copy the PDF attachment to the appropriate directory
                if email.attachment_path and os.path.exists(email.attachment_path):
                    destination_path = os.path.join(organization_dir, os.path.basename(email.attachment_path))
                    shutil.copy2(email.attachment_path, destination_path)
                    email.processed_path = destination_path
                    session.add(email)
                    email.uploaded = False
                    print(f"Copied {email.attachment_path} to {destination_path}")
            session.commit()

    def upload_file_in_chunks(self, file_path, parent_folder_id):
        file_name = os.path.basename(file_path)
        file_metadata = {
            'title': file_name
        }
        if parent_folder_id:
            file_metadata['parents'] = [{'id': parent_folder_id}]
        file = self.drive.CreateFile(file_metadata)

        with open(file_path, 'rb') as f:
            file_content = f.read(self.chunk_size)
            file.content = file_content
            file.Upload()
            print(f"Uploaded chunk of {file_name} to Google Drive")

            while file_content:
                file_content = f.read(self.chunk_size)
                if file_content:
                    file.content = file_content
                    file.Upload(param={'supportsTeamDrives': True, 'uploadType': 'media'})
                    print(f"Uploaded additional chunk of {file_name} to Google Drive")

    def upload_to_google_drive(self, local_path, parent_folder_id=None):
        parent_folder_id = parent_folder_id or self.root_folder_id  # Use the provided root folder ID

        if os.path.isdir(local_path):
            folder_name = os.path.basename(local_path)
            folder_metadata = {
                'title': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                folder_metadata['parents'] = [{'id': parent_folder_id}]
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            folder_id = folder['id']

            for item in os.listdir(local_path):
                item_path = os.path.join(local_path, item)
                self.upload_to_google_drive(item_path, folder_id)
        else:
            self.upload_file_in_chunks(local_path, parent_folder_id)

    def organize_and_upload(self, process_count=10):
        self.categorize_emails(process_count=process_count)
        with self.db.Session() as session:
            emails = session.query(ImportedEmail).filter(and_(ImportedEmail.processed_path != None, ImportedEmail.uploaded == False)).all()
            for email in emails:
                if os.path.exists(email.processed_path):
                    self.upload_to_google_drive(email.processed_path, self.root_folder_id)
                    email.processed_path = None  # Mark as processed
                    email.uploaded = True  # Mark as uploaded
                    session.add(email)
            session.commit()
