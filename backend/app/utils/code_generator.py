import random
import string
from datetime import datetime
from app.models.ci_instance import CodeSequence

BASE_CHARS = string.ascii_uppercase + string.digits  # A-Z, 0-9

def base36_encode(number):
    """将数字转换为Base36编码"""
    if number == 0:
        return '0'
    
    chars = string.digits + string.ascii_uppercase
    result = ''
    while number > 0:
        number, remainder = divmod(number, 36)
        result = chars[remainder] + result
    
    return result


def generate_ci_code():
    """
    生成16位BASE编码的CI唯一编码
    格式: CI + 时间戳(10位) + 随机数(4位)
    示例: CI240215A1B2C3D4E
    """
    # 获取当前时间戳
    timestamp = int(datetime.now().timestamp())
    
    # 将时间戳转换为Base36（10位）
    time_part = base36_encode(timestamp)[-10:].zfill(10)
    
    # 生成4位随机字符
    random_part = ''.join(random.choices(BASE_CHARS, k=4))
    
    # 组合编码
    code = f"CI{time_part}{random_part}"
    
    return code


def generate_ci_code_v2():
    """
    生成16位BASE编码（使用序号版本，更短更易读）
    格式: CI + 日期(6位) + 序号(8位)
    示例: CI24021500000001
    """
    today = datetime.now().strftime('%y%m%d')  # 6位日期: 240215
    
    # 获取当日序号
    sequence = CodeSequence.get_next_value('ci')
    
    # 序号部分（8位，不足补0）
    seq_part = str(sequence).zfill(8)
    
    # 组合编码
    code = f"CI{today}{seq_part}"
    
    return code
