import os
import math
import uuid
from PIL import Image
from book_web import settings

photo_specs = [
    {
        'type': 'thumb',
        'width': 180,
        'height': 180,
        'quality': 86
    },
    {
        'type': 'thumbicon',
        'is_square': True,
        'width': 100,
        'quality': 86
    },
    {
        'type': 'title',
        'width': 800,
        'quality': 86
    },
    {
        'type': 'photo',
        'length': 1080,
        'quality': 86
    },
]

pic_specs = [{
    'type': 'mpic',
    'pixel': 14500,
    'quality': 88
}, {
    'type': 'spic',
    'pixel': 6500,
    'quality': 88
}]

photo_type_dict = {
    'photo': {
        'sub_path':
        'photos',
        'specs': (
            {
                'type': 'thumb',
                'width': 180,
                'height': 180,
                'quality': 86
            },
            {
                'type': 'thumbicon',
                'is_square': True,
                'width': 100,
                'height': 100,
                'quality': 86
            },
            {
                'type': 'title',
                'width': 800,
                'height': 200,
                'is_crop': True,
                'quality': 86
            },
            {
                'type': 'photo',
                'width': 1080,
                'height': 1080,
                'quality': 86
            },
        ),
    },
    'avatar': {
        'sub_path':
        'avatars',
        'specs': (
            {
                'type': 'icon',
                'width': 200,
                'height': 200,
                'is_square': True,
                'quality': 86
            },
            {
                'type': 'title',
                'width': 400,
                'height': 400,
                'is_square': True,
                'quality': 86
            },
        ),
    }
}


def convert_photo(photo_id,
                  base_static_path,
                  photo_type='photo',
                  extension='.jpg'):
    f_path_raw = os.path.join(base_static_path,
                              photo_type_dict[photo_type]['sub_path'], 'raw',
                              photo_id[:2], photo_id + extension)
    f_path_raw = f_path_raw.replace('\\', '/')

    photo_raw_obj = Image.open(f_path_raw)
    # cannot write mode RGBA as JPEG
    photo_raw_obj = photo_raw_obj.convert('RGB')
    # photo_raw_obj.save(f_path_raw)

    photo_width, photo_height = photo_raw_obj.size
    photo_info_dict = {
        'id': str(photo_id),
        'width': photo_width,
        'height': photo_height,
        'size': str(float(os.path.getsize(f_path_raw) / 1024)) + 'KB'
    }

    for spec in photo_type_dict[photo_type]['specs']:
        d_path_target = os.path.join(base_static_path,
                                     photo_type_dict[photo_type]['sub_path'],
                                     spec['type'], photo_id[:2])
        d_path_target = d_path_target.replace('\\', '/')
        if not os.path.exists(d_path_target):
            os.makedirs(d_path_target, 0o775)

        width_scale = float(photo_width / float(spec['width']))
        height_scale = float(photo_height / float(spec['height']))
        size_box = None

        if spec.get('is_square') is True:
            if width_scale > 1 and height_scale > 1:
                if width_scale > height_scale:
                    size_box = (int((photo_width - photo_height) / 2), 0,
                                int((photo_width - photo_height) / 2) +
                                photo_height, photo_height)
                else:
                    size_box = (0, int((photo_height - photo_width) / 2),
                                photo_width, photo_width +
                                int(photo_height - photo_width) / 2)
                new_width = spec['width']
                new_height = spec['height']
            else:
                if width_scale > height_scale:
                    size_box = (int((photo_width - photo_height) / 2), 0,
                                int((photo_width - photo_height) / 2) +
                                photo_width, photo_height)
                    new_width = int(photo_height)
                    new_height = int(photo_height)
                else:
                    size_box = (0, int((photo_height - photo_width) / 2),
                                photo_width, photo_width +
                                int(photo_height - photo_width) / 2)
                    new_width = int(photo_width)
                    new_height = int(photo_width)
        else:
            if width_scale > 1 or height_scale > 1:
                if width_scale > height_scale:
                    if height_scale > 1:
                        new_height = spec['height']
                    else:
                        new_height = photo_height
                    new_width = int(photo_width * new_height / photo_height)
                else:
                    if width_scale > 1:
                        new_width = spec['width']
                    else:
                        new_width = photo_width
                    new_height = int(photo_height * new_width / photo_width)
            else:
                new_width = int(photo_width)
                new_height = int(photo_height)

        f_path_target = os.path.join(d_path_target, photo_id + extension)
        if size_box:
            region_obj = photo_raw_obj.crop(size_box)
            region_obj.resize((new_width, new_height),
                              Image.ANTIALIAS).save(f_path_target,
                                                    quality=spec['quality'])
        else:
            photo_raw_obj.resize((new_width, new_height),
                                 Image.ANTIALIAS).save(f_path_target,
                                                       quality=spec['quality'])

    return photo_info_dict


def remove_photo(photo_id,
                 base_static_path,
                 photo_type='photo',
                 extension='.jpg'):
    target_specs = photo_specs
    target_path_name = 'photos'
    if photo_type == 'pic':
        target_specs = pic_specs
        target_path_name = 'pics'

    for spec in target_specs:
        f_path_target = os.path.join(base_static_path, target_path_name,
                                     spec['type'], photo_id[:2],
                                     photo_id + extension)
        f_path_target = f_path_target.replace('\\', '/')
        try:
            os.remove(f_path_target)
        except OSError:
            pass


def split_photo_fit_kindle(photo_file, outpath=settings.UPLOAD_SAVE_PATH):
    if not os.path.exists(photo_file):
        raise IOError

    if not os.path.exists(outpath):
        os.makedirs(outpath, 0o0755)

    img = Image.open(photo_file)
    orig_width, orig_height = img.size

    img_split_num = int(math.ceil(orig_height / (orig_width * 1.6)))
    if img_split_num == 1:
        return [photo_file]
    else:
        file_list = []
        for i in range(img_split_num):
            shape = (0, int(orig_width * 1.2 * i), orig_width,
                     int(orig_width * 1.2 * (i + 1)))
            new_img = img.crop(shape)
            filename = os.path.join(
                outpath, "{}_{}".format(i,
                                        os.path.split(photo_file)[-1]))
            new_img.save(filename)
            file_list.append(filename)

        return file_list


def save_upload_photo(photo_file,
                      base_static_path=settings.UPLOAD_SAVE_PATH,
                      photo_type='photo',
                      extension='.jpg'):
    raw_ext = photo_file.name.split('.')[-1]
    if raw_ext not in ['jpg', 'jpeg', 'png']:
        return False

    photo_id = uuid.uuid4().hex

    d_path_raw = os.path.join(base_static_path,
                              photo_type_dict[photo_type]['sub_path'], 'raw',
                              photo_id[:2])
    f_path_raw = os.path.join(d_path_raw, photo_id + extension)
    d_path_raw = d_path_raw.replace('\\', '/')
    f_path_raw = f_path_raw.replace('\\', '/')
    if not os.path.exists(d_path_raw):
        os.makedirs(d_path_raw, 0o0755)

    with open(f_path_raw, 'wb+') as f:
        for chunk in photo_file.chunks():
            f.write(chunk)

    photo_info_dict = convert_photo(photo_id,
                                    base_static_path,
                                    photo_type=photo_type,
                                    extension=extension)
    photo_info_dict['name'] = photo_id + extension
    return photo_info_dict


def save_binary_photo(photo_file,
                      base_static_path=settings.UPLOAD_SAVE_PATH,
                      photo_type='photo',
                      extension='.jpg'):
    photo_id = uuid.uuid4().hex

    d_path_raw = os.path.join(base_static_path,
                              photo_type_dict[photo_type]['sub_path'], 'raw',
                              photo_id[:2])
    f_path_raw = os.path.join(d_path_raw, photo_id + extension)
    d_path_raw = d_path_raw.replace('\\', '/')
    f_path_raw = f_path_raw.replace('\\', '/')
    if not os.path.exists(d_path_raw):
        os.makedirs(d_path_raw, 0o0755)

    with open(f_path_raw, 'wb+') as f:
        f.write(photo_file)

    photo_info_dict = convert_photo(photo_id,
                                    base_static_path,
                                    photo_type=photo_type,
                                    extension=extension)
    photo_info_dict['name'] = photo_id + extension
    return photo_info_dict


def django_image_upload_handler(instance, filename):
    image_info = save_upload_photo(instance.key)
    return image_info['name']


def save_qrcode_photo(photo_file,
                      base_static_path=settings.UPLOAD_SAVE_PATH,
                      photo_type='photo',
                      extension='.jpg'):

    photo_id = uuid.uuid4().hex

    d_path_raw = os.path.join(base_static_path,
                              photo_type_dict[photo_type]['sub_path'], 'raw',
                              photo_id[:2])
    f_path_raw = os.path.join(d_path_raw, photo_id + extension)
    f_path_raw = f_path_raw.replace('\\', '/')
    d_path_raw = d_path_raw.replace('\\', '/')
    if not os.path.exists(d_path_raw):
        os.makedirs(d_path_raw, 0o0755)

    with open(f_path_raw, 'wb+') as f:
        f.write(photo_file)

    photo_info_dict = convert_photo(photo_id,
                                    base_static_path,
                                    photo_type=photo_type,
                                    extension=extension)
    photo_info_dict['name'] = photo_id + extension
    return photo_info_dict


def build_photo_url(photo_name, pic_type='photo', ext='jpg'):
    _img_exts = ('.jpg', '.png', '.gif')
    url = ""
    if photo_name:
        _base_path = os.path.join(settings.UPLOAD_STATIC_URL, 'photos',
                                  pic_type, photo_name[:2])
        if photo_name.endswith(_img_exts):
            return settings.APP_HOST + os.path.join(_base_path, photo_name)
        if '.' in ext:
            ext = ext.rsplit('.', 1)[-1]
        return settings.APP_HOST + os.path.join(
            _base_path, '{}.{}'.format(photo_name, ext))
    return os.path.join(settings.APP_HOST, 'images', 'no_img.png')


def build_photo_path(photo_name, pic_type='photo', ext='jpg'):
    _img_exts = ('.jpg', '.png', '.gif')
    if photo_name:
        _base_path = os.path.join(settings.UPLOAD_SAVE_PATH, 'photos',
                                  pic_type, photo_name[:2])
        if photo_name.endswith(_img_exts):
            return os.path.join(_base_path, photo_name)
        if '.' in ext:
            ext = ext.rsplit('.', 1)[-1]
        return os.path.join(_base_path, '{}.{}'.format(photo_name, ext))
    return os.path.join(settings.UPLOAD_SAVE_PATH, 'images', 'no_img.png')


def get_img_url_by_obj(img_obj, pic_type='photo', ext='jpg'):
    if not img_obj:
        return ''
    if isinstance(img_obj, dict):
        return build_photo_url(photo_name=img_obj.get("key"),
                               pic_type=pic_type,
                               ext=ext)
    return build_photo_url(photo_name=img_obj.key, pic_type=pic_type, ext=ext)


def get_thumb_img_url(img_obj):
    # {'type': 'thumb', 'width': 180, 'height': 180, 'quality': 86},
    return get_img_url_by_obj(img_obj, pic_type='thumb')


def get_thumbicon_img_url(img_obj):
    # {'type': 'thumbicon', 'width': 100, 'height': 100, 'quality': 86},
    return get_img_url_by_obj(img_obj, pic_type='thumbicon')


def get_title_img_url(img_obj):
    # {'type': 'title', 'width': 800, 'height': 200, 'quality': 86},
    return get_img_url_by_obj(img_obj, pic_type='title')


def get_photo_img_url(img_obj):
    # {'type': 'photo', 'width': 1080, 'height': 1080, 'quality': 86}
    return get_img_url_by_obj(img_obj, pic_type='photo')


def get_raw_img_url(img_obj):
    return get_img_url_by_obj(img_obj, pic_type='raw')
