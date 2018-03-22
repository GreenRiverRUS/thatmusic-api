import asyncio
import hashlib
import re
import subprocess
from functools import wraps
from typing import Union, Optional
from urllib.parse import urljoin
import binascii
import logging

from tornado import web

from settings import PATHS


basic_stream_handler = logging.StreamHandler()
basic_stream_handler.setFormatter(logging.Formatter('%(levelname)-8s %(asctime)s %(message)s'))
basic_stream_handler.setLevel(logging.DEBUG)


class BasicHandler(web.RequestHandler):
    def get(self, *args, **kwargs):
        raise web.HTTPError(404)

    def write_result(self, result):
        if result['success'] == 0:
            error_code = result.pop('error_code', 400)
            self.set_status(error_code)
            result = dict(result)
            result.update({'error_code': error_code})
        self.finish(result)

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        self.finish({'success': 0, 'error': self._reason, 'error_code': status_code})

    def data_received(self, chunk):
        pass

    def reverse_full_url(self, name, *args):
        host_url = "{protocol}://{host}".format(**vars(self.request))
        return urljoin(host_url, self.reverse_url(name, *args))


def setup_logger(name, lvl=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(lvl)
    logger.addHandler(basic_stream_handler)
    logger.propagate = False
    return logger


def logged(logger=setup_logger('default')):
    def wrapper(method):
        if asyncio.iscoroutinefunction(method):
            @wraps(method)
            async def wrapped(*args, **kwargs):
                self = args[0]  # type: BasicHandler
                logger.info('{} request from {}: {}'.format(method.__name__.capitalize(),
                                                            self.request.remote_ip,
                                                            self.request.uri))
                logger.info('Request body: {}'.format(self.request.body.decode()))
                await method(*args, **kwargs)
                logger.info('Response sent')
        else:
            @wraps(method)
            def wrapped(*args, **kwargs):
                self = args[0]  # type: BasicHandler
                logger.info('{} request from {}: {}'.format(method.__name__.capitalize(),
                                                            self.request.remote_ip,
                                                            self.request.uri))
                logger.info('Request body: {}'.format(self.request.body.decode()))
                method(*args, **kwargs)
                logger.info('Response sent')
        return wrapped
    return wrapper


def vk_url(path: str):
    return urljoin('https://m.vk.com/', path)


def crc32(string: Union[str, bytes]):
    if isinstance(string, str):
        string = string.encode()
    return '{:08x}'.format(binascii.crc32(string) & 0xFFFFFFFF)


def md5(string: Union[str, bytes]):
    if isinstance(string, str):
        string = string.encode()
    return hashlib.md5(string).hexdigest()


def md5_file(file_name, chunk_size=4096):
    hash_md5 = hashlib.md5()
    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def uni_hash(hash_func: str, string):
    if hash_func == 'crc32':
        return crc32(string)
    elif hash_func == 'md5':
        return md5(string)

    raise ValueError('Unknown hash function: {}'.format(hash_func))


def decode_vk_mp3_url(url: str, user_id: str):
    nodejs = PATHS['nodejs']
    decoder_js = PATHS['decode-js']

    process = subprocess.run([nodejs, decoder_js, url, user_id], stdout=subprocess.PIPE)
    return process.stdout.decode()


def sanitize(string, to_lower: bool = True, alpha_numeric_only: bool = False, truncate: Optional[int] = None):
    if alpha_numeric_only:
        string = re.sub(r'\w+', '', string)
    else:
        bad_chars = ['~', '`', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '=', '+',
                     '[', '{', ']', '}', '\\', '|', ';', ':', '"', "'", '—', '–', ',', '<', '>', '/', '?',
                     '‘', '’', '“', '”']
        string = re.sub(r'|'.join(map(re.escape, bad_chars)), '', string)

    string = string.strip()
    string = re.sub(r'\s+', ' ', string)

    if to_lower:
        string = string.lower()
    if truncate is not None:
        string = string[:truncate]

    return string
