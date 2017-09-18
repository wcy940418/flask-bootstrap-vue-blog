from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Text, Table, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
import os

Base = declarative_base()
DEFAULT_DB_URI = None
if 'BLOG_DB_URI' in os.environ:
    DEFAULT_DB_URI = os.environ['BLOG_DB_URI']

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False, index=True)
    password = Column(Text, nullable=False)
    email = Column(String(64), nullable=False, index=True)
    articles = relationship('Post', backref='author')
    role_id = Column(Integer, ForeignKey('roles.id'))
    role = relationship('Role', backref='user')
    api_key = Column(Text)
    def verify_password(self, password):
        if password == self.password:
            return True
        else:
            return False
    def generate_api_key(self, secret_key, expiration=31536000):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({ 'id': self.id })
    @staticmethod
    def verify_api_key(api_key, secret_key):
        s = Serializer(api_key)
        try:
            data = s.loads(api_key)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.username)

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    role = Column(String(64), nullable=False, index=True)
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.role)

class Language(Base):
    __tablename__ = 'languages'
    id = Column(Integer, primary_key=True)
    language = Column(String(64), nullable=False, index=True, unique=True)
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.language)

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    # title = Column(String(255), nullable=False, index=True)
    # content = Column(Text)
    user_id = Column(Integer, ForeignKey('users.id'))
    cat_id = Column(Integer, ForeignKey('categories.id'))
    tags = relationship('Tag', secondary='post_tag', backref='posts')
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.id)

class PostMultiLanguage(Base):
    __tablename__ = 'posts_ml'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text)
    overview = Column(Text)
    language_id = Column(String(64), ForeignKey('languages.language'))
    language = relationship('Language', backref='posts')
    post_id = Column(Integer, ForeignKey('posts.id'))
    post = relationship('Post', backref='post_ml_content')
    last_update_time = Column(DateTime, index=True)
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.title)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)
    posts = relationship('Post', backref='category')
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

post_tag = Table(
    'post_tag', Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

def createSession(uri=None):
    if uri == None:
        uri = DEFAULT_DB_URI
    engine = create_engine(uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Blog db utility')
    parser.add_argument('-c', '--create', action='store_true', help='Initial all tables')
    parser.add_argument('-d', '--drop',action='store_true', help='Drop all tables')
    parser.add_argument('-u', '--uri', type=str, default=None, help='Optional db path')
    args = parser.parse_args()
    if args.uri:
        engine = create_engine(args.uri, echo=True)
    elif DEFAULT_DB_URI:
        engine = create_engine(DEFAULT_DB_URI, echo=True)
    else:
        print "please provide database uri"
        exit(1)
    if args.create:
        print "Preparing for creating the whole blog database"
        Base.metadata.drop_all(engine)
        print "All tables dropped"
        Base.metadata.create_all(engine)
        print "All tables initialized"
        Session = sessionmaker(bind=engine)
        session = Session()
        en = Language(language='en')
        cn = Language(language='cn')
        role_admin = Role(role='admin')
        role_guest = Role(role='guest')
        session.add_all([en, cn, role_admin, role_guest])
        session.commit()
    elif args.drop:
        Base.metadata.drop_all(engine)
        print "All tables dropped"