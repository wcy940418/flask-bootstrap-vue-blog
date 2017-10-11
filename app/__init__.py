import sys

from flask import Flask
from flask_bootstrap import Bootstrap

from config import config
from db_controller import createScopedSession

reload(sys)
sys.setdefaultencoding('utf-8')

bootstrap = Bootstrap()

def create_app(config_name):
    app = Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    bootstrap.init_app(app)
    global db_session
    db_session = createScopedSession(app.config['SQLALCHEMY_DATABASE_URI'])
    from main import main as main_blog
    app.register_blueprint(main_blog)
    app.config['db'] = db_session
    return app

