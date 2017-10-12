import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SSL_DISABLE = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    OMW_API_KEY = os.environ.get('OMW_API_KEY')
    MAGIC_CODE = os.environ.get('MAGIC_CODE')
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    # DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI')



class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}