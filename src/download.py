import os
import stat
from typing import Dict

from tornado import web
import aiohttp
import magic

from cache import CachedHandler
from settings import PATHS, HASH, DOWNLOAD_SETTINGS

from utils import uni_hash, sanitize, setup_logger, logged, md5_file, set_id3_tag
from decode import decode_vk_mp3_url


logger = setup_logger('download')


# TODO add S3 support
# noinspection PyAbstractClass
class DownloadHandler(CachedHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self._cache_path = PATHS['mp3']
        os.makedirs(self._cache_path, exist_ok=True)

    @web.addslash
    @logged(logger)
    async def get(self, *args, **kwargs):
        await self.download(kwargs['key'], kwargs['id'], stream=False)

    def write_error(self, status_code, **kwargs):
        self.finish({'success': 0, 'error': self._reason, 'error_code': status_code})

    async def download(self, cache_key: str, audio_id: str, stream: bool = False):  # TODO add bitrate convertor
        file_path = self._build_file_path(audio_id)

        if os.path.exists(file_path):
            logger.debug('Audio file already exist: {}'.format(file_path))
            audio_info = self._get_audio_info_cache(audio_id)
            if audio_info is None:
                audio_info = self._get_audio_info_from_cached_search(cache_key, audio_id)
            if audio_info is None:
                audio_name = '{}.mp3'.format(audio_id)
            else:
                audio_name = self._format_audio_name(audio_info)
        else:
            audio_info = self._get_audio_info_from_cached_search(cache_key, audio_id)
            if audio_info is None:
                raise web.HTTPError(404)
            audio_name = self._format_audio_name(audio_info)

            if not await self._download_audio(audio_info, file_path):
                raise web.HTTPError(502)

        if not await self._send_from_local_cache(file_path, audio_name, stream):
            raise web.HTTPError(502)

    # TODO add proxy support
    @staticmethod
    async def _download_audio(audio_info: Dict, path: str):
        logger.debug('Downloading from vk: {}'.format(audio_info['mp3']))
        try:
            with open(path, 'wb') as f:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        audio_info['mp3'],
                        timeout=DOWNLOAD_SETTINGS['timeout']
                    ) as response:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            f.write(chunk)
            set_id3_tag(path, audio_info)
        except (aiohttp.ClientError, IOError):
            if os.path.exists(path):
                os.remove(path)
            return False

        return True

    async def _send_from_local_cache(self, path: str, file_name: str, stream: bool):
        logger.debug('Sending file from local storage [streaming={}]: {}'.format(stream, file_name))
        if not self._check_valid_mp3(path):
            return False

        self._set_headers(path, file_name, stream)
        for chunk in self._get_content(path):
            self.write(chunk)
            if stream:
                await self.flush()
        if not stream:
            await self.flush()
        self.finish()
        return True

    def _set_headers(self, path: str, file_name: str, stream: bool):
        self.set_header('Cache-Control', 'private')
        self.set_header('Cache-Description', 'File Transfer')
        self.set_header('Content-Type', 'audio/mpeg')
        if not stream:
            self.set_header('Content-Length', self._get_content_size(path))
        self.set_header('Content-Disposition', 'attachment; filename={}'.format(file_name))

    @staticmethod
    def _get_content_size(path: str):
        stat_result = os.stat(path)
        return stat_result[stat.ST_SIZE]

    @staticmethod
    def _get_content(path: str, chunk_size=64 * 1024):
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                yield chunk

    def _get_audio_info_from_cached_search(self, cache_key: str, audio_id: str):
        logger.debug('Getting audio item from search cache')
        cached_search_result = self._get_cached_search_result(cache_key)
        if cached_search_result is None:
            return None

        audio_info = None
        for item in cached_search_result:
            if item['id'] == audio_id:
                audio_info = item
                break
        if audio_info is None:
            return None

        self._cache_audio_info(audio_info)

        if DOWNLOAD_SETTINGS['mp3_decoder_enabled']:
            logger.debug('Decoding mp3 url')
            decoded_mp3_url = decode_vk_mp3_url(audio_info['mp3'], audio_info['user_id'])
            if decoded_mp3_url is None:
                logger.error('Cannot decode url: {}'.format(audio_info['mp3']))
                logger.debug(decoded_mp3_url)
                return None
            audio_info['mp3'] = decoded_mp3_url
        return audio_info

    @staticmethod
    def _build_file_path(audio_id: str):
        file_name = '{}.mp3'.format(uni_hash(HASH['mp3'], audio_id))
        file_path = os.path.join(PATHS['mp3'], file_name)
        return file_path

    @staticmethod
    def _format_audio_name(audio_info: Dict):
        name = '{} - {}'.format(audio_info['artist'], audio_info['title'])
        name = sanitize(name, to_lower=False, alpha_numeric_only=False)
        return '{}.mp3'.format(name)

    @staticmethod
    def _check_valid_mp3(path: str):
        if not os.path.exists(path):
            logger.error('Missing file: {}'.format(path))
            return False

        valid_mimes = ['audio/mpeg', 'audio/mp3', 'application/octet-stream']
        if magic.from_file(path, mime=True) not in valid_mimes:
            logger.error('Invalid mp3: bad mime-type. Deleting: {}'.format(path))
            os.remove(path)
            return False

        bad_md5_hashes = [
            '9d6ddee7a36a6b1b638c2ca1e26ad46e',
            '8efd23e1cf7989a537a8bf0fb3ed7f62',
            '21a9fef2f321de657d7b54985be55888'
        ]
        if md5_file(path) in bad_md5_hashes:
            logger.error('Invalid mp3: bad md5. Deleting: {}'.format(path))
            os.remove(path)
            return False

        return True


# noinspection PyAbstractClass
class StreamHandler(DownloadHandler):
    @web.addslash
    @logged(logger)
    async def get(self, *args, **kwargs):
        await self.download(kwargs['key'], kwargs['id'], stream=True)
