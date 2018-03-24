from copy import deepcopy
from typing import Optional, List, Dict

from tornado.web import RequestHandler
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from settings import HASH, CACHE_SETTINGS
from utils import md5, uni_hash, setup_logger


logger = setup_logger('cache')


# noinspection PyAbstractClass
class CachedHandler(RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        cache_manager = CacheManager(
            **parse_cache_config_options(CACHE_SETTINGS)
        )
        self._search_pages_cache = cache_manager.get_cache_region('default', 'search_pages')
        self._audio_info_cache = cache_manager.get_cache_region('default', 'audio_info')

    @staticmethod
    def _get_search_cache_key(query: str, page: int):
        if not len(query):
            query = md5('popular')

        return uni_hash(HASH['cache'], '{}.{}'.format(query, page))

    def _get_cached_search_result(self, cache_key: str) -> Optional[List[Dict]]:
        logger.debug('Trying to get search result from cache: {}'.format(cache_key))
        try:
            return deepcopy(self._search_pages_cache.get(cache_key))
        except KeyError:
            logger.debug('Cache miss')
            return None

    def _cache_search_result(self, cache_key: str, result: List[Dict]):
        logger.debug('Store search result into cache...')
        self._search_pages_cache.put(cache_key, deepcopy(result))

    def _get_audio_info_cache(self, audio_id: str):
        logger.debug('Getting audio item from cache: {}'.format(audio_id))
        try:
            return deepcopy(self._audio_info_cache.get(audio_id))
        except KeyError:
            logger.debug('Cache miss')
            return None

    def _cache_audio_info(self, item: Dict):
        logger.debug('Store audio item into cache: {}'.format(item['id']))
        self._audio_info_cache.put(item['id'], deepcopy(item))
