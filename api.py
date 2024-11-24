import asyncio

from main import background_task
from main_bp import main_bp
from flask import Flask

app = Flask(__name__)
app.register_blueprint(main_bp, url_prefix='/api')


if __name__ == "__main__":
    asyncio.create_task(background_task())  # Start background task
    app.run(host='0.0.0.0', port=7667)
