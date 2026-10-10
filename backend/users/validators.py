from rest_framework import serializers
from PIL import Image

def validate_image(value):
    if value and value.size > 5 * 1024 * 1024:
        raise serializers.ValidationError("Изображение должно быть меньше 5 МБ.")
    if value:
        image = Image.open(value)
        if image.format not in ("JPEG", "PNG", "WEBP") or image.width * image.height > 20_000_000:
            raise serializers.ValidationError("Разрешены JPEG, PNG, WEBP до 20 мегапикселей.")
        value.seek(0)
    return value
