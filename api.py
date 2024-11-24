from flask import Flask

from main_bp import main_bp

app = Flask(__name__)
app.register_blueprint(main_bp, url_prefix='/api')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7667)
