from flask import Flask
from api import api_bp
from web import web_bp

app = Flask(__name__)

app.register_blueprint(api_bp)

app.register_blueprint(web_bp)

if __name__ == "__main__":
    app.run(debug=True)