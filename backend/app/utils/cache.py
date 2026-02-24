"""缓存工具模块 - 提供简单的内存缓存功能"""
import time
from functools import wraps
from typing import Any, Optional, Callable


class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self):
        self._cache = {}
        self._expire_time = {}
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        if key in self._cache:
            if time.time() < self._expire_time.get(key, 0):
                return self._cache[key]
            else:
                # 过期，删除缓存
                self.delete(key)
        return None
    
    def set(self, key: str, value: Any, expire_seconds: int = 300):
        """设置缓存值"""
        self._cache[key] = value
        self._expire_time[key] = time.time() + expire_seconds
    
    def delete(self, key: str):
        """删除缓存"""
        self._cache.pop(key, None)
        self._expire_time.pop(key, None)
    
    def delete_pattern(self, pattern: str):
        """删除匹配模式的缓存"""
        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            self.delete(key)
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._expire_time.clear()


# 全局缓存实例
cache = SimpleCache()


def cached(expire_seconds: int = 300, key_prefix: str = ""):
    """缓存装饰器
    
    Args:
        expire_seconds: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, expire_seconds)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """使匹配模式的缓存失效"""
    cache.delete_pattern(pattern)
