from app import create_app

app = create_app('default')

if __name__ == '__main__':
    app = create_app('default')
    app.run(host="0.0.0.0")