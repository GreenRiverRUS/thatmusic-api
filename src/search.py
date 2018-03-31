import random
import re
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from bs4.element import Tag
from tornado import web

from cache import CachedHandler
from session import VkSession, AuthRequired
from settings import SEARCH_SETTINGS, HASH, ARTISTS
from utils import BasicHandler, uni_hash, setup_logger, logged
from decode import decode_vk_mp3_url


logger = setup_logger('search')


class SearchHandler(BasicHandler, CachedHandler):
    @web.addslash
    @logged(logger)
    async def get(self, *args, **kwargs):
        query = self.get_argument('q', '')
        page = self.get_argument('page', '0')
        try:
            page = int(page)
            if page < 0:
                raise ValueError()
        except ValueError:
            self.write_result({
                'success': 0,
                'error': '\'page\' must be a non-negative integer'
            })
            return

        try:
            data = await self.search(query, page)

            self.write_result({
                'success': 1,
                'data': data
            })
        except AuthRequired:
            self.write_result({
                'success': 0,
                'error': 'Unauthorized. Auth required: {}'.format(
                    self.reverse_full_url('auth')
                ),
                'error_code': 401
            })

    async def search(self, query: str, page: int):
        cache_key = self._get_search_cache_key(query, page)  # TODO do not cache popular
        cached_result = self._get_cached_search_result(cache_key)
        if cached_result is not None:
            return self._transform_search_response(query, page, cached_result)

        result = []
        for i in range(SEARCH_SETTINGS['page_multiplier']):
            logger.debug('Trying page {} (size={})...'.format(i, SEARCH_SETTINGS['page_size']))
            response = await self._get_search_results(
                query, offset=(i + 1) * page * SEARCH_SETTINGS['page_size']
            )
            audio_items = self._get_audio_items(response)
            if not len(audio_items):
                break
            result += audio_items

        self._cache_search_result(cache_key, result)
        return self._transform_search_response(query, page, result)

    async def _get_search_results(self, query: str, offset: int):
        if not len(query):
            if SEARCH_SETTINGS['popular_enabled']:
                return await self._get_popular(offset)
            query = self._random_artist()

        query = quote(query)

        vk_session = self.settings['vk_session']  # type: VkSession
        logger.debug('Requesting search page from vk...')
        return await vk_session.get(
            'audio?act=search&q={}&offset={}'.format(query, offset)
        )

    @staticmethod
    def _random_artist():
        return random.choice(ARTISTS)

    async def _get_popular(self, offset: int):
        vk_session = self.settings['vk_session']  # type: VkSession
        logger.debug('Searching popular in vk...')
        return await vk_session.get(
            'audio?act=popular&offset={}'.format(offset)
        )

    @staticmethod
    def _get_audio_items(response: str):
        html_tree = BeautifulSoup(response, 'lxml')

        user_id = re.search(r'vk_id=(\d{1,20})', response).group(1)

        result = []
        for audio_item in html_tree.select_one('#au_search_items').select('.audio_item'):  # type: Tag
            artist = audio_item.select_one('.ai_artist').text
            title = audio_item.select_one('.ai_title').text
            duration = int(audio_item.select_one('.ai_dur')['data-dur'])

            encoded_mp3_url = audio_item.select_one('input[type=hidden]')['value']
            mp3_url = decode_vk_mp3_url(encoded_mp3_url, user_id)
            if mp3_url is None:
                logger.error('Cannot decode url: {}'.format(encoded_mp3_url))
                continue

            audio_id = audio_item['data-id'].rsplit('_', maxsplit=1)[0]
            audio_id = uni_hash(HASH['id'], audio_id)

            result.append({
                'id': audio_id,
                'artist': artist,
                'title': title,
                'duration': duration,
                'mp3': mp3_url
            })

        return result

    def _transform_search_response(self, query: str, page: int, data: List[Dict]):
        logger.debug('Transforming search response...')
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
