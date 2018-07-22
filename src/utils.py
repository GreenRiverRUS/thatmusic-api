import hashlib
import re
from typing import Union, Optional, Dict
from urllib.parse import urljoin
import binascii
import logging

import eyed3
from eyed3.id3 import ID3_V1
from unidecode import unidecode
from tornado import web

from settings import LOG_LEVEL


class BasicHandler(web.RequestHandler):
    logger = None

    def prepare(self):
        self.logger.debug('{} request from {}: {}'.format(
            self.request.method.capitalize(),
            self.request.remote_ip,
            self.request.uri)
        )
        self.logger.debug('Request body: {}'.format(self.request.body.decode()))

    def on_finish(self):
        self.log_request()

    def write_result(self, result):
        self.finish({'success': 1, 'data': result})

    def write_error(self, status_code, **kwargs):
        result = {'success': 0, 'error': self._reason, 'error_code': status_code}
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            if isinstance(exception, web.HTTPError):
                result.update(exception.args)  # TODO
        self.finish(result)

    def log_request(self):
        self.logger.info(
            '{remote_ip} {method} {request_uri} => HTTP: {status_code} ({time:.0f} ms)'.format(
                remote_ip=self.request.remote_ip,
                method=self.request.method.upper(),
                request_uri=self.request.uri,
                status_code=self.get_status(),
                time=1000.0 * self.request.request_time()
            )
        )

    def data_received(self, chunk):
        pass

    def reverse_full_url(self, name, *args):
        host_url = "{protocol}://{host}".format(**vars(self.request))
        return urljoin(host_url, self.reverse_url(name, *args))


def setup_logger(name, lvl=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(lvl)
    basic_stream_handler = logging.StreamHandler()
    basic_stream_handler.setFormatter(
        logging.Formatter('%(levelname)-8s %(asctime)s %(message)s')
    )
    basic_stream_handler.setLevel(LOG_LEVEL)
    logger.addHandler(basic_stream_handler)
    logger.propagate = False
    return logger


def vk_url(path: str):
    return urljoin('https://api.vk.com/', path)


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


def sanitize(string, to_lower: bool = True, alpha_numeric_only: bool = False, truncate: Optional[int] = None):
    if alpha_numeric_only:
        string = re.sub(r'\w+', '', string)
    else:
        bad_chars = ['~', '`', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '=', '+',
                     '[', '{', ']', '}', '\\', '|', ';', ':', '"', "'", '—', '–', ',', '<', '>', '/', '?',
                     '‘', '’', '“', '”']
        string = re.sub(r'|'.join(map(re.escape, bad_chars)), '', string)

    string = unidecode(string)  # transliteration and other staff: converts to ascii
    string = string.strip()
    string = re.sub(r'\s+', ' ', string)

    if to_lower:
        string = string.lower()
    if truncate is not None:
        string = string[:truncate]

    return string


def set_id3_tag(path: str, audio_info: Dict):
    audio = eyed3.load(path)
    audio.initTag(version=ID3_V1)
    audio.tag.title = unidecode(audio_info['title']).strip()
    audio.tag.artist = unidecode(audio_info['artist']).strip()
    audio.tag.save(version=ID3_V1)
