# -*- coding: utf-8 -*-
from flask import render_template, session, redirect, url_for, jsonify, request, flash, abort, current_app
import json
import httplib
import datetime
from sqlalchemy import extract
from app.db_controller import *
from . import main


KELVIN_ZERO = 273.15
MAGIC_CODE = "940623"

basedir = os.path.abspath(os.path.dirname(__file__))



def check_sign_status(sess):
    if 'username' in sess:
        return url_for('main.user_signout'), "Sign out"
    else:
        return url_for('main.user_signin'), "Sign in"

def unified_auth(session, token=None):
    username = None
    if token is None:
        if 'username' in session:
            username = session['username']
    return username
    #TODO: Add token auth mechanism

@main.teardown_request
def teardown_request(exception=None):
    db_session = current_app.config['db']
    db_session.remove()

@main.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

@main.route('/', methods=['GET'])
def index():
    lan = request.args.get('lan', None)
    if lan:
        if lan == 'en':
            session['language'] = 'en'
        elif lan == 'cn':
            session['language'] = 'cn'
    if 'language' not in session:
        session['language'] = 'en'
    return render_template('index.html')

@main.route('/p', methods=['GET'])
def view_post():
    db_session = current_app.config['db']
    lan = request.args.get('lan', None)
    post_id = request.args.get('id', None)
    if lan is None:
        if 'language' in session:
            lan = session['language']
        else:
            lan = 'en'
    if not post_id:
        abort(404)
    post_content = db_session.query(PostMultiLanguage)\
        .join(Language)\
        .join(Post)\
        .filter(Language.language == lan)\
        .filter(Post.id == int(post_id))\
        .first()
    if post_content is None:
        abort(404)
    edit_link = url_for('main.edit_post', p=post_id, lan=lan, _external=True)
    return render_template('post.html', post=post_content, edit_link=edit_link, post_id=post_id)

@main.route('/editor', methods=['GET'])
def edit_post():
    if 'username' not in session:
        abort(400)
    return render_template('editor.html')

@main.route('/user/<username>', methods=['GET'])
def user_panel(username):
    return redirect(url_for('main.index'))

@main.route('/status',methods=['GET'])
def status():
    message = request.args.get('msg', None)
    flash(message)
    return render_template('status.html', new_location=url_for('main.index'))

@main.route('/logstatus',methods=['GET'])
def log_status():
    if 'username' in session:
        flash('You have signed in, redirect to index in 3 seconds')
    else:
        flash('You have signed out, redirect to index in 3 seconds')
    return render_template('status.html', new_location=url_for('main.index'))

@main.route('/signin', methods=['GET', 'POST'])
def user_signin():
    if 'username' in session:
        return redirect(url_for('main.user_panel', username=session['username']))
    else:
        db_session = current_app.config['db']
        if request.method == 'POST':
            email = request.form['email']
            if email != 'wcy940418@gmail.com':
                flash('Invalid password or email')
                return render_template('signin.html'), 400
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
                    return redirect(url_for('main.log_status'))
                else:
                    flash('Invalid password or email')      
                    return render_template('signin.html'), 400
            else:
                flash('Invalid password or email') 
                return render_template('signin.html'), 400
        else:
            return render_template('signin.html')

@main.route('/signout', methods=['GET'])
def user_signout():
    session.pop('username', None)
    return redirect(url_for('main.log_status'))

@main.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        db_session = current_app.config['db']
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
        return redirect(url_for('main.log_status'))
    else:
        return render_template('register.html')

@main.route('/api/weather', methods=['GET'])
def api_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    response_dict = dict()
    if lat and lon:
        conn = httplib.HTTPConnection("api.openweathermap.org")
        conn.request("GET", "/data/2.5/weather?lat=" + lat
                     + '&lon=' + lon + "&appid=" + current_app.config['OMW_API_KEY'])
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
    return jsonify(response_dict)

@main.route('/api/user_register', methods=['POST'])
def api_new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    email = request.json.get('email')
    magiccode = request.json.get('magiccode')
    db_session = current_app.config['db']
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
           {'Location': url_for('main.user_panel', userid=user.id, _external=True)}


@main.route('/api/post', methods=['GET', 'POST'])
def api_posts():
    db_session = current_app.config['db']
    if request.method == 'GET':
        post_id = request.args.get('postid', None)
        date_month = request.args.get('date_month', None)
        category = request.args.get('cat', None)
        tag = request.args.get('tag', None)
        num = request.args.get('num', '1')
        lan = request.args.get('lan', None)
        response = {
            'posts': []
        }
        if post_id:
            post_content = db_session.query(PostMultiLanguage)\
                .join(Language)\
                .join(Post)
            if lan is not None:
                post_content = post_content.filter(Language.language == lan)
            post_content = post_content.filter(Post.id == int(post_id)).first()
            if post_content is None:
                return jsonify({'status': "No such post"}), 400
            else:
                post = {
                    'id': str(post_content.post_id),
                    'title': post_content.title,
                    'last_update_time': post_content.last_update_time.strftime("%B %d, %Y"),
                    'author': post_content.post.author.username,
                    'content': post_content.content,
                    'overview': post_content.overview,
                    'category': post_content.post.category.name,
                    'tags': [tag.name for tag in post_content.post.tags],
                    'language': post_content.language.language
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
                        'overview': post_content.overview,
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
        username = unified_auth(session, request.args.get('apikey', None))
        if not username:
            return jsonify({'status': "No modification permission"}), 400
        requested_json = request.get_json(force=True)
        method = requested_json['method']
        if method == 'delete':
            post_id = requested_json['post_id']
            language = requested_json['language']
            if language == 'all':
                post_content = db_session.query(PostMultiLanguage) \
                    .join(Post) \
                    .filter(Post.id == int(post_id)).all()
                for x in post_content:
                    db_session.delete(x)
                db_session.query(Post).filter(Post.id == int(post_id)).delete()
                db_session.commit()
                return jsonify({'status': "Deleting succeeded"}), 200
            else:
                post_content = db_session.query(PostMultiLanguage) \
                    .join(Language) \
                    .join(Post) \
                    .filter(Language.language == language) \
                    .filter(Post.id == int(post_id)).first()
                db_session.delete(post_content)
                count = db_session.query(PostMultiLanguage) \
                    .join(Post) \
                    .filter(Post.id == int(post_id)).count()
                if count == 0:
                    db_session.query(Post).filter(Post.id == int(post_id)).delete()
                db_session.commit()
                return jsonify({'status': "Deleting succeeded"}), 200
        elif method == 'new':
            language = db_session.query(Language).filter(Language.language == requested_json['language']).first()
            title = requested_json['title']
            overview = requested_json['overview']
            tags = [db_session.query(Tag).filter(Tag.name == tag).first() for tag in requested_json['tags']]
            cat = db_session.query(Category).filter(Category.name == requested_json['cat']).first()
            content = requested_json['content']
            user = db_session.query(User).filter(User.username == username).first()
            post_mainthread = Post(
                category=cat,
                tags=tags,
                author=user
            )
            post_content = PostMultiLanguage(
                title=title,
                content=content,
                overview=overview,
                language=language,
                post=post_mainthread,
                last_update_time=datetime.datetime.now()
            )
            db_session.add(post_mainthread)
            db_session.add(post_content)
            db_session.flush()
            new_post_id = post_mainthread.id
            db_session.commit()
            return jsonify({'status': "Adding succeeded", "post_id": str(new_post_id)}), 200
        elif method == 'change':
            post_id = requested_json['post_id']
            language = requested_json['language']
            title = requested_json['title']
            overview = requested_json['overview']
            tags = requested_json['tags']
            cat = requested_json['cat']
            content = requested_json['content']
            exist_language_version = [posts.language.language for posts in
                                        db_session.query(PostMultiLanguage)
                                          .join(Post)
                                          .filter(Post.id == post_id)
                                          .all()
                                      ]
            if language in exist_language_version:
                post_content = db_session.query(PostMultiLanguage) \
                    .join(Language) \
                    .join(Post) \
                    .filter(Language.language == language) \
                    .filter(Post.id == int(post_id)).first()
                post_content.overview = overview
                post_content.title = title
                post_content.tags = [db_session.query(Tag).filter(Tag.name == x).first() for x in tags]
                post_content.cat = db_session.query(Category).filter(Category.name == cat).first()
                post_content.content = content
                post_content.last_update_time = datetime.datetime.now()
                db_session.add(post_content)
                db_session.commit()
                return jsonify({'status': "Changing succeeded"}), 200
            else:
                post_mainthread = db_session.query(Post).filter(Post.id == post_id).first()
                post_content = PostMultiLanguage(
                    title=title,
                    content=content,
                    overview=overview,
                    language=language,
                    post=post_mainthread,
                    last_update_time=datetime.datetime.now()
                )
                db_session.add(post_mainthread)
                db_session.add(post_content)
                db_session.commit()
                return jsonify({'status': "Changing succeeded"}), 200

@main.route('/api/posts-meta', methods=['GET', 'POST'])
def api_posts_meta():
    db_session = current_app.config['db']
    if request.method == 'GET':
        attr = request.args.get('attr', None)
        lan = request.args.get('lan', None)
        if lan is not None:
            if attr:
                if attr == 'all':
                    categories = [ category.name for category in db_session.query(Category)
                        .join(Post)
                        .join(PostMultiLanguage)
                        .join(Language)
                        .filter(Language.language == lan)
                        .order_by(Category.name).all()]
                    tags = [tag.name for tag in db_session.query(Tag)
                        .join(Tag.posts)
                        .join(PostMultiLanguage)
                        .join(Language)
                        .filter_by(language=lan)
                        .all()]
                    dates_ = [date.last_update_time for date in db_session.query(PostMultiLanguage)
                        .join(Language)
                        .filter(Language.language == lan)
                        .order_by(PostMultiLanguage.last_update_time.desc())
                        .all()]
                    dates = []
                    languages = [language.language for language in db_session.query(Language).all()]
                    for date in dates_:
                        date_str = date.strftime("%Y-%m")
                        if date_str not in dates:
                            dates.append(date_str)
                    return jsonify({
                        'categories': categories,
                        'tags': tags,
                        'dates': dates,
                        'languages': languages
                    }), 200
                elif attr == 'tags':
                    tags = [tag.name for tag in db_session.query(Tag)
                        .join(Tag.posts)
                        .join(PostMultiLanguage)
                        .join(Language)
                        .filter_by(language=lan)
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
                elif attr == 'languages':
                    languages = [language.language for language in db_session.query(Language).all()]
                    return jsonify({
                        'languages': languages
                    }), 200
            else:
                return jsonify({'status': "Please enter valid searching information"}), 400
        else:
            if attr:
                if attr == 'all':
                    categories = [category.name for category in db_session.query(Category).order_by(Category.name).all()]
                    tags = [tag.name for tag in db_session.query(Tag).order_by(Tag.name).all()]
                    dates_ = [date.last_update_time for date in db_session.query(PostMultiLanguage)
                        .order_by(PostMultiLanguage.last_update_time.desc())
                        .all()]
                    dates = []
                    languages = [language.language for language in db_session.query(Language).all()]
                    for date in dates_:
                        date_str = date.strftime("%Y-%m")
                        if date_str not in dates:
                            dates.append(date_str)
                    return jsonify({
                        'categories': categories,
                        'tags': tags,
                        'dates': dates,
                        'languages': languages
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
                        .order_by(Category.name).all()]
                    return jsonify({
                        'categories': categories
                    }), 200
                elif attr == 'dates':
                    dates_ = [date.last_update_time for date in db_session.query(PostMultiLanguage)
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
                elif attr == 'languages':
                    languages = [language.language for language in db_session.query(Language).all()]
                    return jsonify({
                        'languages': languages
                    }), 200
            else:
                return jsonify({'status': "Please enter valid searching information"}), 400
    elif request.method == 'POST':
        username = unified_auth(session, request.args.get('apikey', None))
        if not username:
            return jsonify({'status': "No modification permission"}), 400
        requested_json = request.get_json(force=True)
        method = requested_json['method']
        if method == 'add_tag':
            tag = requested_json['name']
            new_tag = Tag(name=tag)
            db_session.add(new_tag)
            db_session.commit()
            return jsonify({'status': "Adding tag succeeded"}), 200
        elif method == 'add_cat':
            cat = requested_json['name']
            new_cat = Category(name=cat)
            db_session.add(new_cat)
            db_session.commit()
            return jsonify({'status': "Adding cat succeeded"}), 200
        elif method == 'del_tag':
            tag = db_session.query(Tag).filter(Tag.name == requested_json['name'])
            db_session.delete(tag)
            db_session.commit()
            return jsonify({'status': "Deleting tag succeeded"}), 200
        elif method == 'del_cat':
            cat = db_session.query(Category).filter(Category.name == requested_json['name'])
            db_session.delete(cat)
            db_session.commit()
            return jsonify({'status': "Deleting cat succeeded"}), 200
        else:
            return jsonify({'status': "Please submit valid command"}), 400

@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@main.errorhandler(500)
def server_internal_error(e):
    return render_template('500.html'), 500

