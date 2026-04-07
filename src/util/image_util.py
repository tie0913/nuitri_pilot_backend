import asyncio
import uuid

import boto3
import base64
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile
from src.util.config import get_settings
import io

settings = get_settings()
s3 = boto3.client(
    "s3",
    endpoint_url=settings.CDN_R2_ENDPOINT,
    aws_access_key_id=settings.CDN_ACCESS_KEY,
    aws_secret_access_key=settings.CDN_SECRET_KEY,
)

async def dealwith_img(img: UploadFile, user_id:str):

    file_name = img.filename
    file_content = await img.read()
    content_type = img.content_type
    upload_result = await upload_to_r2(
        file_name=file_name,
        file_content=file_content,
        content_type=content_type,
        user_id=user_id)
    
    convert_result = await image_to_thumbnail(file_content=file_content, content_type=content_type)

    if upload_result['success'] and convert_result['success']:
        return upload_result | convert_result
    else:
        errors = []
        if 'error' in upload_result:
            errors.append(upload_result['error'])
        
        if 'error' in convert_result:
            errors.append(convert_result['error'])
        return {
            'success': False,
            'errors' : errors
        }



async def upload_to_r2(file_name, file_content, content_type, user_id: str) -> str:
    # 生成随机文件名
    ext = file_name.split(".")[-1]
    cnd_file_name = f"users/{user_id}/{uuid.uuid4()}.{ext}"

    # boto3 是同步 → 放线程池
    loop = asyncio.get_event_loop()

    try:
        await loop.run_in_executor(
            None,
            lambda: s3.put_object(
                Bucket=settings.CDN_BUCKET_NAME,
                Key=cnd_file_name,
                Body=file_content,
                ContentType=content_type)
        )
        return {
            'success': True,
            'path': f"{settings.CDN_READ_PREFIX}/{cnd_file_name}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'CDB error' + str(e)
        }


async def image_to_thumbnail(file_content, content_type, max_size=(200, 200), quality=35):
    try:
        # ---- 读取上传内容 ----
        if not file_content:
            raise ValueError("Uploaded file is empty.")

        # ---- 生成缩略图 ----
        try:
            image = Image.open(io.BytesIO(file_content))
        except UnidentifiedImageError:
            raise ValueError("Uploaded file is not a valid image.")

        # 部分图片格式必须转换为 RGB
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        image.thumbnail(max_size)

        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=quality)
        buffer.seek(0)

        thumbnail_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        thumbnail_b64_url = f"data:image/webp;base64,{thumbnail_base64}"

        return {
            "success": True,
            "base64_thumbnail": thumbnail_b64_url,
        }

    except ValueError as e:
        return {"success": False, "error": str(e)}

    except MemoryError:
        return {"success": False, "error": "Image is too large to process."}

    except Exception as e:
        # 通用兜底
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
