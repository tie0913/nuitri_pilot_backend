from src.util.config import get_settings
from datetime import datetime,timezone
from jose import jwt, JWTError


# 创建token，不需要过期，因为session我们放在了mongo里
# mongo的 ttl索引会自动做过期删除策略，我们就省事了
def create_token(what_ever:str) -> str :
    settings = get_settings()
    now = datetime.now(timezone.utc)
    pay_load = {"text": what_ever, "iat": int(now.timestamp())}
    token = jwt.encode(pay_load, settings.JWT__SECRET, settings.JWT__ALGORITHM) 
    return token

# 这个方法会在验证出现问题的时候抛出 JWT Error
# 所以最好的办法是分别定义好正确结果以及错误结果对应的代码和错误提示
# 并反馈给调用方，让对方去做业务判断
# 返回的对象是一个tuple，这个在python里最方便了，0号位表示结果标志位，1号位是解析的正确结果或者提示信息
#  0    解密后的明文
#  1    错误提示     
def decode_token(token) -> tuple :
    settings = get_settings()
    try:
        decryption = jwt.decode(token, settings.JWT__SECRET, settings.JWT__ALGORITHM)
        return (0, decryption)
    except JWTError as e:
        return (1, 'Decode token has error')