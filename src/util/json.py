# utils/encode.py
from datetime import datetime
from bson import ObjectId, Decimal128
from fastapi.encoders import jsonable_encoder

def convert_id(collection) :
    return list(map(lambda d: {**d, "_id": str(d["_id"])}, collection))

def to_json(data):
    return jsonable_encoder(
        data,
        custom_encoder={
            ObjectId: str,                         # 64位16进制字符串
            datetime: lambda dt: dt.isoformat(),   # ISO8601
            Decimal128: lambda d: str(d.to_decimal()),  # 或者 float(...)，但注意精度
        },
    )



def generate_result(t:tuple):
    if t[0] == 0:
        return {
            "success":True,
            "code":t[0],
            "message":"",
            "data":t[1]
        }
    else:
        return {
            "success":False,
            "code":t[0],
            "message":t[1],
            "data":""
        }