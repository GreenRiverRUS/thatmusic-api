from typing import Optional, List, Dict

from tornado.web import RequestHandler

from settings import HASH
from utils import md5


class CachedHandler(RequestHandler):
    @staticmethod
    def _get_cache_key(query: str, page: int):
        if not len(query):
            query = md5('popular')

        return HASH['cache']('{}.{}'.format(query, page))

    # TODO
    def _get_cached_search_result(self, cache_key: str) -> Optional[List[Dict]]:
        return None

    # TODO
    def _cache_search_result(self, cache_key: str, result: List[Dict]):
        pass

    # TODO
    def _get_audio_item_cache(self, audio_id: str):
        return None

    # TODO
    def _cache_audio_item(self, item: Dict):
        pass
