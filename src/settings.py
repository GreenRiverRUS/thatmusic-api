import os


MAX_AUTH_RETRIES = 3

PATHS = {
    'cookie': 'cookies',
    'mp3': 'data',
    'nodejs': os.getenv('NODEJS_PATH', 'node'),
    'decode-js': 'decode.js',
}

AUTH_ACCOUNTS = [
    ('login', 'password')
]

HASH = {
    'cache': 'crc32',
    'id': 'crc32',
    'mp3': 'md5'
}

CACHE_SETTINGS = {
    'cache.type': 'memory',
    'cache.regions': 'search_pages, audio_items',
    'cache.search_pages.expire': 24 * 60,  # in minutes
    'cache.audio_items.expire': None  # never
}

SEARCH_SETTINGS = {
    'popular_enabled': False,
    'page_size': 50,
    'page_multiplier': 2,
    'sort_regex': r'(?i)[ \[\],.:\)\(\-_](bass ?boost(ed)?|dub sound|remake|low bass'
                  r'|cover|(re)?mix|dj|bootleg|edit|aco?ustic|instrumental|karaoke'
                  r'|tribute|vs|rework|mash|rmx|(night|day|slow)core|remode|ringtone?'
                  r'|рингтон|РИНГТОН|Рингтон|звонок|минус)([ ,.:\[\]\)\(\-_].*)?$',
    'bad_words_regex': '(?i)(https?:\/\/)?(vkontakte|vk)\.?(com|ru)?\/?(club|id)?',
}

DOWNLOAD_SETTINGS = {
    'mp3_decoder_enabled': True,
    'timeout': 60
}

# Random artist search
ARTISTS = [
    '2 Cellos', 'Agnes Obel', 'Aloe Black', 'Andrew Belle', 'Angus Stone', 'Aquilo', 'Arctic Monkeys',
    'Avicii', 'Balmorhea', 'Barcelona', 'Bastille', 'Ben Howard', 'Benj Heard', 'Birdy', 'Broods',
    'Calvin Harris', 'Charlotte OC', 'City of The Sun', 'Civil Twilight', 'Clint Mansel', 'Coldplay',
    'Daft Punk', 'Damien Rice', 'Daniela Andrade', 'Daughter', "David O'Dowda", 'Dawn Golden', 'Dirk Maassen',
    'Ed Sheeran', 'Eminem', 'Fabrizio Paterlini', 'Fink', 'Fleurie', 'Florence and The Machine', 'Gem club',
    'Glass Animals', 'Greg Haines', 'Greg Maroney', 'Groen Land', 'Halsey', 'Hans Zimmer', 'Hozier',
    'Imagine Dragons', 'Ingrid Michaelson', 'Jamie XX', 'Jarryd James', 'Jasmin Thompson', 'Jaymes Young',
    'Jessie J', 'Josef Salvat', 'Julia Kent', 'Kai Engel', 'Keaton Henson', 'Kendra Logozar', 'Kina Grannis',
    'Kodaline', 'Kygo', 'Kyle Landry', 'Lana Del Rey', 'Lera Lynn', 'Lights & Motion', 'Linus Young', 'Lo-Fang',
    'Lorde', 'Ludovico Einaudi', 'M83', 'MONO', 'MS MR', 'Macklemore', 'Mammals', 'Maroon 5', 'Martin Garrix',
    'Mattia Cupelli', 'Max Richter', 'Message To Bears', 'Mogwai', 'Mumford & Sons', 'Nils Frahm', 'ODESZA',
    'Of Monsters and Men', 'Oh Wonder', 'Philip Glass', 'Phoebe Ryan', 'Rachel Grimes', 'Radiohead', 'Ryan Keen',
    'Sam Smith', 'Seinabo Sey', 'Sia', 'Takahiro Kido', 'The Irrepressibles', 'The Neighbourhood', 'The xx',
    'VLNY', 'Wye Oak', 'X ambassadors', 'Yann Tiersen', 'Yiruma', 'Young Summer', 'Zack Hemsey', 'Zinovia',
    'deadmau5', 'pg.lost', 'Ólafur Arnalds', 'Oasis',
]
