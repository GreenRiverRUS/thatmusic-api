import asyncio
import logging

from tornado.web import url, Application

from download import DownloadHandler, StreamHandler
from search import SearchHandler
from utils import setup_logger


# Disable unnecessary logging
logging.getLogger('tornado.general').disabled = True
logging.getLogger('tornado.access').disabled = True


def main():
    logger = setup_logger('main')
    loop = asyncio.get_event_loop()

    app = Application(
        handlers=[
            url(r'/search/?', SearchHandler, name='search'),
            url(r'/dl/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', DownloadHandler, name='download'),
            url(r'/stream/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', StreamHandler, name='stream')
        ]
    )
    app.listen(8000)
    logger.info('Starting...')
    loop.run_forever()


if __name__ == '__main__':
    main()
