from app import create_app

app = create_app('development')

# 在应用创建后获取socketio实例
from app import socketio

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
