import os

import app as app_module
from app import create_app

# 避免本地 manager(127.0.0.1) 被系统代理接管，导致 Python-Web 调用上游 503。
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

app = create_app('development')

if __name__ == '__main__':
    app_module.socketio.run(app, host='0.0.0.0', port=5000, debug=True)
