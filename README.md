# Email Processing System

## Overview
This project provides a complete email processing system that includes the following features:
- Import emails from multiple IMAP accounts.
- Detect and extract organization information from email attachments.
- Categorize and organize email attachments by organization and date.
- Upload organized files to Google Drive.
- Control and manage the entire workflow using a Flask API.

## Features
- **Email Importing**: Automatically import emails from specified IMAP accounts, including attachments.
- **Organization Detection**: Use OpenAI to extract organization names and identify spam or promotional content.
- **Categorization**: Organize attachments by year, month, and organization.
- **Google Drive Upload**: Upload organized files to a specified Google Drive folder.
- **Flask API**: Control the entire system through a RESTful API.

## Configuration
The system is configured using a YAML file (`config.yaml`). Below are the key configurations:

### Database Configuration
- `database_url`: Path to the SQLite database file.

### Logging
- `log_file`: Path to the log file used by the system.

### Email Import Settings
- `save_path`: Directory to save email attachments.
- `emails`: List of email accounts with credentials and IMAP server details.

### OpenAI Settings
- `open_api_key`: API key for accessing OpenAI services (recommended to use environment variables for security).

### Google API Settings
- `client_config_file`: Path to the Google client secret file.
- `save_credentials_file`: Path to save Google API credentials.
- `root_folder_id`: Google Drive folder ID where organized files will be uploaded.
- `settings_file`: Settings file for GoogleAuth.

### PDF Decryption
- `pdf_passwords`: List of passwords used to decrypt PDF attachments.

## Docker Setup
This project includes a Docker setup to run the Flask server conveniently.

### Docker Compose Configuration
A `docker-compose.yml` file is provided with the following configuration:

```yaml
docker-compose.yml:
version: '3.8'

services:
  plex-webhook:
    image: registry.rlt.sk/invoice-from-imap-to-gdrive:latest
    container_name: invoice-from-imap-to-gdrive
    ports:
      - "7667:7667"
    volumes:
      - /data:/data
    environment:
      FLASK_PORT: 7667
      FLASK_ENV: production
      FLASK_DEBUG: 'false'
      CONFIG_PATH: /data/config.yaml
    restart: unless-stopped
```

### Docker Usage
1. **Run Docker Compose**:
   To start the service using Docker Compose, run the following command:
   ```sh
   docker-compose up -d
   ```
   This will start the container and run the Flask server, making it available at `http://localhost:7667`.

## Setup Instructions
1. **Clone the Repository**:
   ```sh
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

3. **Set Up Google API**:
   - Enable Google Drive API in the Google Cloud Console.
   - Download the `client_secret.json` file and place it in the project directory.
   - Update `config.yaml` with the path to `client_secret.json`.

4. **Update Configuration**:
   - Modify `config.yaml` to include email credentials, OpenAI API key, and other relevant configurations.

5. **Run the Flask Server**:
   ```sh
   python flask_blueprint_main_control.py
   ```
   The API will be available at `http://localhost:5000/api`.

## Usage
- **Import Emails**: Use the `/api/import_email` endpoint to import emails.
- **Detect Organizations**: Use the `/api/detect_organization` endpoint to analyze and detect organizations from email attachments.
- **Organize and Upload**: Use the `/api/organize_email` endpoint to organize attachments and upload them to Google Drive.

### Example CURL Commands
- **Import Emails**:
  ```sh
  curl -X POST http://localhost:5000/api/import_email -H "Content-Type: application/json" -d '{"year": 2024, "month": 11}'
  ```

- **Detect Organizations**:
  ```sh
  curl -X POST http://localhost:5000/api/detect_organization
  ```

- **Organize and Upload**:
  ```sh
  curl -X POST http://localhost:5000/api/organize_email
  ```

## Security Considerations
- **Credentials**: Store sensitive information (e.g., email passwords, OpenAI API key) in environment variables or a secure secrets manager.
- **Google Credentials**: Ensure that `client_secret.json` and `credentials.json` are kept secure and not shared publicly.

## License
This project is licensed under the MIT License.

## Contributions
Contributions are welcome! Please fork the repository and create a pull request with your changes.

## Contact
For questions or support, please reach out to the repository maintainer.
