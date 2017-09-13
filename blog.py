# -*- coding: utf-8 -*-
import os
from flask import Flask
from flask import render_template, session, redirect, url_for, jsonify, request, flash
import json
import httplib
import datetime

from sqlalchemy import extract
from flask_bootstrap import Bootstrap

from db_controller import *

KELVIN_ZERO = 273.15
MAGIC_CODE = "940623"

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Q^\xc7\xc8RI\xba\x98\x9d9\x88%VF-3\xf1\xfe\t\xfa_Tx\x8f'
app.config['SQLALCHEMY_DATABASE_URI'] = None
if 'BLOG_DB_URI' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['BLOG_DB_URI']

app.config['OMW_API_KEY'] = '73323744bf4b7300b711576a9e8b74eb'
bootstrap = Bootstrap(app)



@app.route('/', methods=['GET', 'POST'])
def index():
    if 'language' not in session:
        session['language'] = 'en'
    return render_template('index.html')

@app.route('/p/<postid>', methods=['GET'])
def view_post(postid):
    pass

@app.route('/user/<username>', methods=['GET'])
def user_panel(username):
    return redirect(url_for('index'))

@app.route('/logstatus',methods=['GET'])
def log_status():
    if 'username' in session:
        flash('You have signed in, redirect to index in 3 seconds')
    else:
        flash('You have signed out, redirect to index in 3 seconds')
    return render_template('logstatus.html')

@app.route('/signin', methods=['GET', 'POST'])
def user_signin():
    if 'username' in session:
        return redirect(url_for('user_panel', username=session['username']))
    else:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            remember = True if 'remember-me' in request.form.getlist('remember') else False
            if email is None or password is None or remember is None:
                flash('Please enter valid information')
                return render_template('signin.html'), 400
            user = db_session.query(User).filter_by(email=email).first()
            if user is not None:
                if user.verify_password(password):
                    session['username'] = user.username
                    if remember:
                        session.permanent = True
                    return redirect(url_for('log_status'))
                else:
                    flash('Invalid password or email')
                    return render_template('signin.html'), 400
            else:
                flash('Invalid password or email')
                return render_template('signin.html'), 400
        else:
            return render_template('signin.html')

@app.route('/signout', methods=['GET'])
def user_signout():
    session.pop('username', None)
    return redirect(url_for('log_status'))

@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        magiccode = request.form['magiccode']
        if username is None or password is None or email is None:
            flash('Please enter valid information')
            return render_template('register.html'), 400
        if db_session.query(User).filter_by(username=username).first() is not None:
            flash(username + ' has existed')
            return render_template('register.html'), 400
        if magiccode != MAGIC_CODE:
            flash('Magic Code incorrect')
            return render_template('register.html'), 400
        user = User(username=username, password=password, email=email)
        db_session.add(user)
        db_session.commit()
        session.pop('username', None)
        session['username'] = username
        return redirect(url_for('log_status'))
    else:
        return render_template('register.html')

@app.route('/api/weather', methods=['GET'])
def api_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    response_dict = dict()
    if lat and lon:
        conn = httplib.HTTPConnection("api.openweathermap.org")
        conn.request("GET", "/data/2.5/weather?lat=" + lat
                     + '&lon=' + lon + "&appid=" + app.config['OMW_API_KEY'])
        response = conn.getresponse()
        brooklyn_weather = json.loads(response.read())
        conn.close()
        if "name" in brooklyn_weather:
            response_dict['name'] = brooklyn_weather['name']
            response_dict['temperature'] = str(brooklyn_weather['main']['temp'] - KELVIN_ZERO) + u'℃'
            response_dict['weather'] = brooklyn_weather['weather'][0]['main']
            response_dict['overview'] = " ".join([response_dict['name'],
                                                  response_dict['temperature'],
                                                  response_dict['weather']
                                                  ])
        else:
            response_dict['overview'] = ""
    else:
        response_dict['overview'] = ""
    print response_dict['overview']
    return jsonify(response_dict)

@app.route('/api/user_register', methods=['POST'])
def api_new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    email = request.json.get('email')
    magiccode = request.json.get('magiccode')
    if username is None or password is None or email is None:
        return jsonify({'status': 'Please enter valid username, password and email'}), 400
    if db_session.query(User).filter_by(username=username).first() is not None:
        return jsonify({'status': 'Username ' + username + ' has existed', 'username': username}), 400
    if magiccode != MAGIC_CODE:
        return jsonify({'status': 'Magic code incorrect'}), 400
    user = User(username=username, password=password, email=email)
    db_session.add(user)
    db_session.commit()
    return jsonify({'status': user.username + " has been created"}), \
           201, \
           {'Location': url_for('user_panel', userid=user.id, _external=True)}


@app.route('/api/post', methods=['GET', 'POST'])
def api_posts():
    if request.method == 'GET':
        post_id = request.args.get('postid', None)
        date_month = request.args.get('date_month', None)
        category = request.args.get('cat', None)
        tag = request.args.get('tag', None)
        num = request.args.get('num', '1')
        lan = request.args.get('lan', 'en')
        response = {
            'posts': []
        }
        if post_id:
            post_content = db_session.query(PostMultiLanguage)\
                .join(Language)\
                .join(Post)\
                .filter(Language.language == lan)\
                .filter(Post.id == int(post_id)).first()
            if post_content is None:
                return jsonify({'status': "No such post"}), 400
            else:
                post = {
                    'id': str(post_content.post_id),
                    'title': post_content.title,
                    'last_update_time': post_content.last_update_time.strftime("%B %d, %Y"),
                    'author': post_content.post.author.username,
                    'content': post_content.content,
                    'category': post_content.post.category.name,
                    'tags': [tag.name for tag in post_content.post.tags]
                }
                response['posts'].append(post)
                return jsonify(response), 200
        elif date_month or category or tag or num < 50 or lan:
            query = db_session.query(PostMultiLanguage)
            if lan:
                query = query.join(Language).filter(Language.language == lan)
            if date_month:
                year, month = date_month.split('-')
                query = query.filter(extract('year', PostMultiLanguage.last_update_time) == int(year),
                                     extract('month', PostMultiLanguage.last_update_time) == int(month))
            query = query.join(Post)
            if category:
                query = query.join(Category).filter(Category.name == category)
            if tag:
                query = query.filter(Post.tags.any(name=tag))
            posts_list = query.order_by(PostMultiLanguage.last_update_time.desc()).limit(int(num)).all()
            if len(posts_list) != 0:
                for post_content in posts_list:
                    post = {
                        'id': str(post_content.post_id),
                        'title': post_content.title,
                        'last_update_time': post_content.last_update_time.strftime("%B %d, %Y"),
                        'author': post_content.post.author.username,
                        'content': post_content.content,
                        'category': post_content.post.category.name,
                        'tags': [tag.name for tag in post_content.post.tags]
                    }
                    response['posts'].append(post)
                return jsonify(response), 200
            else:
                return jsonify({'status': "No such post"}), 400
        else:
            return jsonify({'status': "Please enter valid searching information"}), 400

    elif request.method == 'POST':
        pass
        # TODO:api_key auth and change blog by POST method

@app.route('/api/posts-meta', methods=['GET'])
def api_posts_meta():
    attr = request.args.get('attr', None)
    lan = request.args.get('lan', 'en')
    if attr:
        if attr == 'all':
            categories = [ category.name for category in db_session.query(Category)
                .join(Post)
                .join(PostMultiLanguage)
                .join(Language)
                .filter(Language.language == lan)
                .order_by(Category.name).all()]
            # tags = [tag.name for tag in db_session.query(Tag)
            #     .filter(Tag.posts.any())
            #     .join(PostMultiLanguage)
            #     .join(Language)
            #     .order_by(Tag.name)
            #     .filter(Language.language == lan)
            #     .all()]
            tags = [tag.name for tag in db_session.query(Tag)
                .order_by(Tag.name)
                .all()]
            dates_ = [date.last_update_time for date in db_session.query(PostMultiLanguage)
                .join(Language)
                .filter(Language.language == lan)
                .order_by(PostMultiLanguage.last_update_time.desc())
                .all()]
            dates = []
            for date in dates_:
                date_str = date.strftime("%Y-%m")
                if date_str not in dates:
                    dates.append(date_str)
            return jsonify({
                'categories': categories,
                'tags': tags,
                'dates': dates
            }), 200
        elif attr == 'tags':
            tags = [tag.name for tag in db_session.query(Tag)
                .order_by(Tag.name)
                .all()]
            return jsonify({
                'tags': tags
            }), 200
        elif attr == 'categories':
            categories = [category.name for category in db_session.query(Category)
                .join(Post)
                .join(PostMultiLanguage)
                .join(Language)
                .filter(Language.language == lan)
                .order_by(Category.name).all()]
            return jsonify({
                'categories': categories
            }), 200
        elif attr == 'dates':
            dates_ = [date.last_update_time for date in db_session.query(PostMultiLanguage)
                .join(Language)
                .filter(Language.language == lan)
                .order_by(PostMultiLanguage.last_update_time.desc())
                .all()]
            dates = []
            for date in dates_:
                date_str = date.strftime("%Y-%m")
                if date_str not in dates:
                    dates.append(date_str)
            return jsonify({
                'dates': dates
            }), 200
    else:
        return jsonify({'status': "Please enter valid searching information"}), 400

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Blog main app')
    parser.add_argument('-d', '--db', type=str, default=None, help='Optional db path')
    args = parser.parse_args()
    if args.db:
        app.config['SQLALCHEMY_DATABASE_URI'] = args.db
    if app.config['SQLALCHEMY_DATABASE_URI']:
        db_session = createSession(app.config['SQLALCHEMY_DATABASE_URI'])
    else:
        print "Please provide database URI"
        exit(1)
    app.run(ssl_context='adhoc', host='0.0.0.0')