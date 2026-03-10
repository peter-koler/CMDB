import random
import string
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from flask import session


def generate_math_captcha():
    """生成数学运算验证码"""
    # 随机选择运算符（加法或减法）
    operator = random.choice(['+', '-'])

    # 生成数字，确保减法结果为正数
    if operator == '+':
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        result = num1 + num2
    else:
        num1 = random.randint(2, 20)
        num2 = random.randint(1, num1 - 1)
        result = num1 - num2

    # 生成公式字符串
    formula = f"{num1} {operator} {num2} = ?"

    return {
        'formula': formula,
        'result': result,
        'num1': num1,
        'num2': num2,
        'operator': operator
    }


def generate_captcha_image(formula, width=200, height=50):
    """生成验证码图片"""
    # 创建白色背景图片
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 添加背景噪点
    for _ in range(300):
        x = random.randint(0, width)
        y = random.randint(0, height)
        color = (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
        draw.point((x, y), fill=color)

    # 添加干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(150, 200), random.randint(150, 200), random.randint(150, 200))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

    # 尝试使用系统字体，如果没有则使用默认字体
    try:
        # 尝试使用常见的等宽字体
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 28)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 28)
        except:
            font = ImageFont.load_default()

    # 计算文字位置使其居中
    bbox = draw.textbbox((0, 0), formula, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 5

    # 绘制文字（带轻微偏移产生模糊效果）
    for offset in [(1, 1), (-1, -1)]:
        draw.text((x + offset[0], y + offset[1]), formula, font=font, fill=(200, 200, 200))

    # 绘制主文字
    draw.text((x, y), formula, font=font, fill=(50, 50, 50))

    # 添加前景噪点（较少）
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        color = (random.randint(100, 150), random.randint(100, 150), random.randint(100, 150))
        draw.point((x, y), fill=color)

    # 转换为base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    return f"data:image/png;base64,{image_base64}"


def save_captcha_to_session(captcha_data):
    """保存验证码到session"""
    session['captcha_result'] = captcha_data['result']
    session['captcha_expire'] = (datetime.now() + timedelta(minutes=5)).isoformat()


def verify_captcha(user_answer):
    """验证用户输入的验证码"""
    stored_result = session.get('captcha_result')
    expire_time_str = session.get('captcha_expire')

    if stored_result is None or expire_time_str is None:
        return False, '验证码已过期，请重新获取'

    # 检查是否过期
    expire_time = datetime.fromisoformat(expire_time_str)
    if datetime.now() > expire_time:
        # 清除过期的验证码
        session.pop('captcha_result', None)
        session.pop('captcha_expire', None)
        return False, '验证码已过期，请重新获取'

    # 验证答案
    try:
        user_answer_int = int(user_answer)
        if user_answer_int == stored_result:
            # 验证成功后立即清除，防止重放攻击
            session.pop('captcha_result', None)
            session.pop('captcha_expire', None)
            return True, '验证成功'
        else:
            return False, '验证码错误'
    except ValueError:
        return False, '验证码格式错误'


def clear_captcha():
    """清除验证码"""
    session.pop('captcha_result', None)
    session.pop('captcha_expire', None)
