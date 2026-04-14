"""Image validation and storage helpers."""

import base64
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
MAX_PHOTOS = 5
MAX_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/gif': '.gif',
}


def process_uploaded_images(files, menu_id: str) -> tuple[list[tuple[str, str]], list[dict]]:
    if not files:
        raise ValueError('Pelo menos uma foto e necessaria.')
    if len(files) > MAX_PHOTOS:
        raise ValueError(f'Maximo de {MAX_PHOTOS} fotos permitidas.')

    menu_upload_dir = os.path.join(UPLOADS_DIR, menu_id)
    os.makedirs(menu_upload_dir, exist_ok=True)

    images: list[tuple[str, str]] = []
    saved_files: list[dict] = []
    for index, file_storage in enumerate(files, start=1):
        mime_type = file_storage.mimetype or ''
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f'Tipo de imagem nao suportado: {mime_type}. Use JPEG, PNG, WebP ou GIF.')

        binary_data = file_storage.read()
        if len(binary_data) > MAX_SIZE_BYTES:
            raise ValueError(f"A imagem '{file_storage.filename}' excede o limite de 5 MB.")

        extension = EXTENSIONS[mime_type]
        filename = f'photo_{index:02d}{extension}'
        file_path = os.path.join(menu_upload_dir, filename)
        with open(file_path, 'wb') as file_handle:
            file_handle.write(binary_data)

        image_base64 = base64.b64encode(binary_data).decode('utf-8')
        images.append((image_base64, mime_type))
        saved_files.append({
            'filename': filename,
            'original_name': file_storage.filename or filename,
            'mime_type': mime_type,
            'size_bytes': len(binary_data),
            'url': f'/api/uploads/{menu_id}/{filename}',
        })

    return images, saved_files