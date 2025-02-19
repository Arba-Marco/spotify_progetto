from flask import Flask
from blueprints.auth import auth_bp
from blueprints.home import home_bp

app = Flask(__name__)
app.secret_key = 'chiave_per_session'

# Registriamo i Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)

if __name__ == '__main__':
    app.run(debug=True)