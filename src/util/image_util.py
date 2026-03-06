import base64
from PIL import Image, UnidentifiedImageError
import io

async def image_to_base64(img):
    file_bytes = await img.read()
    base64_str = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{img.content_type};base64,{base64_str}"

async def image_to_base64_with_thumbnail(img, max_size=(200, 200), quality=35):
    try:
        # ---- 读取上传内容 ----
        file_bytes = await img.read()
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        # ---- 原图 Base64 ----
        original_base64 = base64.b64encode(file_bytes).decode("utf-8")
        original_b64_url = f"data:{(img.content_type or 'image/jpeg')};base64,{original_base64}"

        # ---- 生成缩略图 ----
        try:
            image = Image.open(io.BytesIO(file_bytes))
        except UnidentifiedImageError:
            raise ValueError("Uploaded file is not a valid image.")

        if not str(img.content_type or "").lower().startswith("image/"):
            fmt = (image.format or "").upper()
            mime_map = {
                "JPEG": "image/jpeg",
                "JPG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
                "GIF": "image/gif",
                "BMP": "image/bmp",
            }
            mime = mime_map.get(fmt, "image/jpeg")
            original_b64_url = f"data:{mime};base64,{original_base64}"

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
            "base64_img": original_b64_url,
            "base64_thumbnail": thumbnail_b64_url,
        }

    except ValueError as e:
        return {"success": False, "error": str(e)}

    except MemoryError:
        return {"success": False, "error": "Image is too large to process."}

    except Exception as e:
        # 通用兜底
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
