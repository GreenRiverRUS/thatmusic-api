import asyncio
from tornado.web import url, Application
from search import SearchHandler


def main():
    loop = asyncio.get_event_loop()

    app = Application(
        handlers=[
            url(r'/search/?', SearchHandler, name='search'),
            # url(r'/dl/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', DownloadHandler, name='download'),
            # url(r'/dl/(?P<key>[^\/]+)/(?P<id>[^\/]+)/(?P<bitrate>[^\/]+)/?',
            #     BitrateDownloadHandler, name='bitrate_download'),
            # url(r'/stream/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', StreamHandler, name='stream'),
            # url(r'/bytes/(?P<key>[^\/]+)/(?P<id>[^\/]+)/?', BytesHandler, name='bytes')
        ]
    )
    app.listen(8000)
    loop.run_forever()


if __name__ == '__main__':
    main()
