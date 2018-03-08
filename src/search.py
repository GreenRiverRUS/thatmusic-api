import random
import re
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from bs4.element import Tag
from tornado import web

from cache import CachedHandler
from session import VkSession, AuthError
from settings import SEARCH_SETTINGS, HASH, ARTISTS
from utils import BasicHandler, uni_hash


class SearchHandler(BasicHandler, CachedHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self._vk_session = VkSession()

    @web.addslash
    async def get(self, *args, **kwargs):
        query = self.get_argument('q', '')
        page = self.get_argument('page', '0')
        try:
            page = int(page)
            if page < 0:
                raise ValueError()
        except ValueError:
            pass  # TODO

        try:
            data = await self.search(query, page)

            self.write_result({
                'success': 1,
                'data': data
            })
        except AuthError:
            pass  # TODO

    async def search(self, query: str, page: int):
        cache_key = self._get_search_cache_key(query, page)
        cached_result = self._get_cached_search_result(cache_key)
        if cached_result is not None:
            return self._transform_search_response(query, page, cached_result)

        result = []
        for _ in range(SEARCH_SETTINGS['page_multiplier']):
            response = await self._get_search_results(
                query, offset=page * SEARCH_SETTINGS['page_size']
            )
            curr_result = self._get_audio_items(response)
            if not len(curr_result):
                break
            result += curr_result

        self._cache_search_result(cache_key, result)
        return self._transform_search_response(query, page, result)

    async def _get_search_results(self, query: str, offset: int):
        if not len(query):
            if SEARCH_SETTINGS['popular_enabled']:
                return await self._get_popular(offset)
            query = self._random_artist()

        query = quote(query)

        return await self._vk_session.get(
            'audio?act=search&q={}&offset={}'.format(query, offset)
        )

    @staticmethod
    def _random_artist():
        return random.choice(ARTISTS)

    async def _get_popular(self, offset: int):
        return await self._vk_session.get(
            'audio?act=popular&offset={}'.format(offset)
        )

    @staticmethod
    def _get_audio_items(response: str):
        html_tree = BeautifulSoup(response, 'lxml')

        user_id = re.search(r'vk_id=(\d{1,20})', response).group(1)

        result = []
        for audio in html_tree.select_one('#au_search_items').select('.audio_item'):  # type: Tag
            artist = audio.select_one('.ai_artist').text
            title = audio.select_one('.ai_title').text
            duration = audio.select_one('.ai_dur')['data-dur']
            mp3 = audio.select_one('input[type=hidden]')['value']

            audio_id = audio['data-id'].rsplit('_', maxsplit=1)[0]
            audio_id = uni_hash(HASH['id'], audio_id)

            result.append({
                'id': audio_id,
                'user_id': user_id,
                'artist': artist,
                'title': title,
                'duration': duration,
                'mp3': mp3
            })

        return result

    def _transform_search_response(self, query: str, page: int, data: List[Dict]):
        sortable = not self._is_bad_match([query])

        head, tail = [], []
        cache_key = self._get_search_cache_key(query, page)
        for audio in data:
            download_url = self.reverse_full_url('download', cache_key, audio['id'])
            stream_url = self.reverse_full_url('stream', cache_key, audio['id'])
            artist = self._clean_audio_string(audio['artist'])
            title = self._clean_audio_string(audio['title'])

            audio = {
                'artist': artist,
                'title': title,
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
