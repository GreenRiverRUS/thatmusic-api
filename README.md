# thatmusic API

This is a workaround to use private VK music API. Inspired by [datmusic-api](https://github.com/alashow/datmusic-api).

# How it works

The app uses token from environment variable. It searches songs with given query in VK private api
and saves data in cache.

For every search query the app returns downloading links. On download request the app downloads file,
caches it and then sends to client.

# Auth

VK's private audio API's can only be used with tokens from official apps or special third party apps
(for ex. Kate mobile). User agent of that app must be used when talking to VK when using such tokens.


This is how you can get tokens using Kate Mobile app:

1. Use proxy to intercept HTTPS requests made by Kate Mobile app.
Example apps: mitmproxy, Fiddler, Charles proxy, or Wireshark

2. Listen for requests to get `refreshToken`
After Kate's login, VK will give an access token: this token won't work with Audio API's
("Token confirmation required").
Open Audios screen from the app, and you will see in your network interceptor that Kate will get
`Token confirmation required` from VK.
After which Kate will register something in Google Cloud Messaging to generate receipt field
which will it use to get `refreshToken` by sending it to private API `auth.refreshToken` along with current token.
After all, `auth.refreshToken` will return a new token.
This is the token you need to save to be able to use it in this branch.

Note: Try to use same IP's while doing it all.

# Search

Search results are cached for 24 hours by default.

`https://thatmusic.example/search?q={query}&page={page}`

# Downloads & Streams

`https://thatmusic.example/dl/{search_hash}/{audio_hash}` (downloads with proper file name `Artist - Title.mp3`)

`https://thatmusic.example/stream/{search_hash}/{audio_hash}` (streams file)

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
- Place vk access token in your `.env`,
or use environment variable `ACCESS_TOKEN` (see [default env](.env.default)).
- Run `docker-compose -p YOURPROJECTNAME up --build -d`
- The app will be available at your machine on the specified earlier port.
For example, `curl "http://localhost:8000/search/?q=Moby"`.
