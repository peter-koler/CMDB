import app as app_module
from app import create_app

app = create_app('development')

if __name__ == '__main__':
    app_module.socketio.run(app, host='0.0.0.0', port=5000, debug=True)
