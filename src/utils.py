import asyncio
import hashlib
from typing import Union
from urllib.parse import urljoin
import binascii

from tornado import web


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
