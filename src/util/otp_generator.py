import secrets
import string

def generate_otp(digit_number) -> str:
    chars = string.digits
    return ''.join(secrets.choice(chars) for _ in range(digit_number))
