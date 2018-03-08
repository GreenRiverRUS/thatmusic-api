import asyncio
from tornado.web import url, Application

from download import DownloadHandler, StreamHandler
from search import SearchHandler
from session import VkSession, AuthHandler, AuthSecondStepHandler


def main():
    loop = asyncio.get_event_loop()
    vk_session = VkSession()

    app = Application(
        handlers=[
            url(r'/_auth/?', AuthHandler, name='auth'),
            url(r'/_auth_second_factor/?', AuthSecondStepHandler, name='auth_second_factor'),
            url(r'/search/?', SearchHandler, name='search'),
            url(r'/dl/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', DownloadHandler, name='download'),
            # url(r'/dl/(?P<key>[^\/]+)/(?P<id>[^\/]+)/(?P<bitrate>[^\/]+)/?',
            #     BitrateDownloadHandler, name='bitrate_download'),
            url(r'/stream/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', StreamHandler, name='stream'),
            # url(r'/bytes/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', BytesHandler, name='bytes')
        ],
        vk_session=vk_session
    )
    app.listen(8000)
    loop.run_forever()


if __name__ == '__main__':
    main()
