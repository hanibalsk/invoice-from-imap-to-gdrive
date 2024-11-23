from flask import Blueprint, jsonify, request

from main import main

# Create a Flask Blueprint
main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/import_email', methods=['POST'])
def import_email():
    try:
        year = request.json.get('year', None)
        month = request.json.get('month', None)
        main.import_email(year=year, month=month)
        return jsonify({'status': 'success', 'message': 'Emails imported successfully.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@main_bp.route('/detect_organization', methods=['POST'])
def detect_organization():
    try:
        main.detect_organization()
        return jsonify({'status': 'success', 'message': 'Organizations detected successfully.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@main_bp.route('/organize_email', methods=['POST'])
def organize_email():
    try:
        main.organize_email()
        return jsonify({'status': 'success', 'message': 'Emails organized and uploaded to Google Drive successfully.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


