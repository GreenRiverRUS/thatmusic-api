# thatmusic API

This is an VK music API which uses directly m.vk.com to get audio data

This is an alternative to disabled VK music API. Inspired by [datmusic-api](https://github.com/alashow/datmusic-api).

# How it works

The app logs in to the site using credentials from [settings file](src/settings.py#L9) (multiple accounts supported) and saves cookies for re-using.
It searches songs with given query in VK website (currently from mobile version, m.vk.com), then parses it and saves data in cache.

For every search query the app returns downloading links. On download request the app decodes vk music link, download file, caches it and then sends to client.

# Auth

On the first run you need to authorize to vk or all api-endpoints will
return `401 Unauthorized`:

`https://thatmusic.example/_auth/`

Then the app will try to complete the authorization, and if it fails,
for example, when met two-factor auth, it will invite you to
pass "second factor" by entering missing fields
(they will be described in answer).

You should enter them as query args (default one is `code`):

`https://thatmusic.example/_auth_second_factor/?code=XXXXXX`


# Search

Search results are cached for 24 hours by default.

`https://thatmusic.example/search?q={query}&page={page}`

# Downloads & Streams

`https://thatmusic.example/dl/{search_hash}/{audio_hash}` (force download with proper file name (`Artist - Title.mp3`))

`https://thatmusic.example/stream/{search_hash}/{audio_hash}` (redirects to mp3 file)

# Bitrate converting

Currently not implemented

# Cache

Mp3 urls for VK are valid only for 24 hours. So search results can be cached only for 24 hours.

Default caching driver is `memory` for search results and `dbm` for songs data.
You can change this behaviour in [settings file](src/settings.py#L18).
See [Beaker docs](http://beaker.readthedocs.io/en/latest/configuration.html#options-for-sessions-and-caching) for additional info.

# Using with S3 Storage

Not supported yet

# Deployment

Project configured to run in docker container.

- Install docker & docker-compose
- Create your own `.env` by coping [default env file](.env.default) and specify container port
or you can use environment variable `CONTAINER_PORT` when running container
- Place vk credentials in your `.env`, or [settings file](src/settings.py#L9),
or use environment variable `ACCOUNTS` (see [default env](.env.default)).
- Run `docker-compose -p YOURPROJECTNAME up --build -d`
- The app will be available at your machine on the specified earlier port.
For example, `curl "http://localhost:8000/search/?q=Moby"`.
