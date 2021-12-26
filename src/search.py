import random
import re
from typing import List, Dict

from tornado import web
import aiohttp

from cache import CachedHandler
from settings import SEARCH_SETTINGS, HASH, ARTISTS
from utils import uni_hash, setup_logger, vk_url


class SearchHandler(CachedHandler):
    logger = setup_logger('search')

    @web.addslash
    async def get(self, *args, **kwargs):
        query = self.get_argument('q', '')
        page = self.get_argument('page', '0')
        try:
            page = int(page)
            if page < 0:
                raise ValueError()
        except ValueError:
            raise web.HTTPError(
                status_code=400,
                reason='\'page\' must be a non-negative integer'
            )
        try:
            captcha_kwargs = {
                key: self.get_argument(key) for key in ('captcha_sid', 'captcha_key')
            }
        except web.MissingArgumentError:
            captcha_kwargs = {}

        data = await self.search(query, page, **captcha_kwargs)
        self.write_result(data)

    async def search(self, query: str, page: int, **kwargs):
        cache_key = self._get_search_cache_key(query, page)  # TODO do not cache random
        cached_result = self._get_cached_search_result(cache_key)
        if cached_result is not None:
            return self._transform_search_response(query, page, cached_result)

        response = await self._get_search_results(
            query, offset=page * SEARCH_SETTINGS['page_size'], **kwargs
        )
        self._raise_for_error(response)
        audio_items = self._get_audio_items(response)

        self._cache_search_result(cache_key, audio_items)
        return self._transform_search_response(query, page, audio_items)

    async def _get_search_results(self, query: str, offset: int, **kwargs):
        if not len(query):
            query = self._random_artist()

        headers = {'User-Agent': SEARCH_SETTINGS['user_agent']}
        params = {
            'access_token': SEARCH_SETTINGS['access_token'],
            'q': query,
            'offset': offset,
            # 'sort': 2,
            'count': SEARCH_SETTINGS['page_size'],
            'v': '5.72'
        }

        if 'captcha_key' in kwargs and 'captcha_sid' in kwargs:
            params.update({
                'captcha_sid': kwargs['captcha_sid'],
                'captcha_key': kwargs['captcha_key']
            })

        self.logger.debug('Requesting search results (size={}) from vk...'.format(
            SEARCH_SETTINGS['page_size']
        ))
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    url=vk_url('method/audio.search'),
                    headers=headers,
                    params=params
            ) as response:
                result = await response.json()

        return result

    def _raise_for_error(self, response: dict):
        if 'error' not in response:
            return
        error_data = response['error']
        error_message = '({code}) {message}'.format(
            code=error_data['error_code'],
            message=error_data['error_msg']
        )
        if error_data['error_code'] == 14:  # captcha
            args = {
                'captcha_sid': int(error_data['captcha_sid']),
                'captcha_img': error_data['captcha_img']
            }
        else:
            args = {}
        self.logger.error(error_message)
        raise web.HTTPError(
            status_code=400,
            reason=error_message,
            args=args
        )

    @staticmethod
    def _random_artist():
        return random.choice(ARTISTS)

    @staticmethod
    def _get_audio_items(response: dict):
        result = []
        for audio_item in response['response']['items']:
            if not len(audio_item['url']):
                continue

            result.append({
                'id': uni_hash(HASH['id'], str(audio_item['id'])),
                'artist': audio_item['artist'],
                'title': audio_item['title'],
                'duration': audio_item['duration'],
                'mp3': audio_item['url']
            })

        return result

    def _transform_search_response(self, query: str, page: int, data: List[Dict]):
        self.logger.debug('Transforming search response...')
        sortable = not self._is_bad_match([query])

        head, tail = [], []
        cache_key = self._get_search_cache_key(query, page)
        for audio in data:
            download_url = self.reverse_full_url('download', cache_key, audio['id'])
            stream_url = self.reverse_full_url('stream', cache_key, audio['id'])
            artist = self._clean_audio_string(audio['artist'])
            title = self._clean_audio_string(audio['title'])
            duration = audio['duration']

            audio = {
                'artist': artist,
                'title': title,
                'duration': duration,
                'download': download_url,
                'stream': stream_url
            }

            if sortable and self._is_bad_match([artist, title]):
                tail.append(audio)
            else:
                head.append(audio)

        return head + tail

    @staticmethod
    def _is_bad_match(strings: List[str]):
        if len(''.join(strings)) > 100:
            return True

        for string in strings:
            if re.search(SEARCH_SETTINGS['sort_regex'], string):
                return True

        return False

    @staticmethod
    def _clean_audio_string(string: str):
        return re.sub(SEARCH_SETTINGS['bad_words_regex'], '', string)
