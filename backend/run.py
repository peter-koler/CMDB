from app import create_app

app = create_app('development')

# 在应用创建后导入 socketio（此时已被正确初始化）
import app as app_module

if __name__ == '__main__':
    app_module.socketio.run(app, host='0.0.0.0', port=5000, debug=True)
