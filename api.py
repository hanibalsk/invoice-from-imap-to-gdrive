from main_bp import main_bp

if __name__ == "__main__":
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(main_bp, url_prefix='/api')

    app.run(host='0.0.0.0', port=7667)