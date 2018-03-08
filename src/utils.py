import hashlib
import subprocess
from typing import Union
from urllib.parse import urljoin
import binascii

from tornado import web

from settings import PATHS


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
