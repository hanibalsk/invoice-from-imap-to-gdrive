import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from time import sleep

from config_loader import load_config
from email_exporter import EmailOrganizer
from email_procesor import ImportEmails
from organization import OrganizationDetector


class Main:
    def __init__(self):
        self.config = load_config(os.getenv("CONFIG_PATH", "config.yaml"))

        # Configure logging
        log_file = self.config.get('log_file', '/data/server.log')

        # Create logfile if it does not exist
        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.write("")

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Set up logging to console and log file
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setLevel(logging.INFO)

        # Define the logging format and add handlers to the logger
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        self.importer = ImportEmails(self.config["emails"], self.config["save_path"], self.config["database_url"])
        self.detector = OrganizationDetector(self.config["database_url"], self.config['open_api_key'],
                                             self.config['pdf_passwords'])
        self.organizer = EmailOrganizer(self.config["database_url"], self.config["base_dir"],
                                        self.config["root_folder_id"], self.config["settings_file"])

    def import_email(self, year=None, month=None):
        self.importer.import_emails(year=year, month=month)

    def detect_organization(self):
        self.detector.update_emails_with_organization()

    def organize_email(self):
        self.organizer.organize_and_upload(self.config.get('batch_size', 10))


main = Main()


async def background_task():
    while True:
        logging.info("Background job running...")
        main.organize_email()

        interval = main.config.get('background_interval', 60)
        logging.info("Waiting for %d seconds before running the background job again...", interval)
        sleep(interval)


async def run():
    asyncio.create_task(background_task())  # Start background task
    logging.info("Background task started.")
