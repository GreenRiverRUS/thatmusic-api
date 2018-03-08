import random
from hashlib import md5
import os
from typing import Optional, Union, Dict

from lxml import html
from lxml.etree import ElementTree
import aiohttp

from settings import AUTH_ACCOUNTS, PATHS, MAX_AUTH_RETRIES
from utils import vk_url, setup_logger


logger = setup_logger('auth')


class AuthError(Exception):
    pass


class CheckRequiresUserIntervention(AuthError):
    def __init__(self, form_fields):
        self.form = form_fields


class UnableToAuthorize(AuthError):
    pass


class FieldsMismatchSavedCheckForm(AuthError):
    pass


class NoSavedCheckForm(AuthError):
    pass


class AuthRequired(AuthError):
    pass


class VkSession:
    def __init__(self):
        self._auth_phone, self._auth_password = random.choice(AUTH_ACCOUNTS)  # type: str, str
        self._auth_retries: int = 0
        self._saved_check_form: Optional[Dict] = None

        self._cookie_path: str = os.path.join(
            PATHS['cookie'],
            md5(self._auth_phone.encode()).hexdigest()
        )
        os.makedirs(os.path.split(self._cookie_path)[0], exist_ok=True)

        self._cookie_jar = aiohttp.CookieJar()
        if self._has_cookie:
            self._cookie_jar.load(self._cookie_path)

    @property
    def _has_cookie(self) -> bool:
        return os.path.exists(self._cookie_path)

    def _save_cookie(self):
        self._cookie_jar.save(self._cookie_path)

    def _clear_cookie(self):
        self._cookie_jar.clear()
        os.remove(self._cookie_path)

    async def _post_form(self, url: str, **kwargs):
        async with aiohttp.ClientSession(cookie_jar=self._cookie_jar) as session:
            async with session.post(url, data=kwargs) as response:
                response = await response.text()

        return response

    @staticmethod
    def _get_form(response: Union[str, ElementTree]):
        if isinstance(response, str):
            html_tree = html.fromstring(response)
        else:
            html_tree = response

        forms = html_tree.cssselect('form')
        if not len(forms):
            return None
        form = forms[0]

        url = vk_url(form.get('action'))
        field_names = {
            inp.get('name'): inp.get('value', None)
            for inp in form.cssselect('input')
            if inp.get('type') in ('text', 'hidden')
        }

        return {
            'url': url,
            'fields': field_names
        }

    @staticmethod
    def _is_authenticated(response: str) -> bool:
        return 'https://login.vk.com/?act=logout' in response

    async def _try_auth(self):
        self._auth_retries += 1
        self._cookie_jar.clear()

        async with aiohttp.ClientSession(cookie_jar=self._cookie_jar) as session:
            async with session.get(vk_url('login')) as response:
                response_body = await response.text()

            auth_form = self._get_form(response_body)

            async with session.post(auth_form['url'], data={
                'email': self._auth_phone,
                'pass': self._auth_password
            }) as response:
                response_body = await response.text()

        self._save_cookie()
        return response_body

    async def auth(self):
        if not self._has_cookie:
            response = await self._try_auth()
        else:
            async with aiohttp.ClientSession(cookie_jar=self._cookie_jar) as session:
                async with session.get(vk_url('feed')) as response:
                    response = await response.text()

        while True:
            if self._is_security_check(response):
                response = await self._auth_security_check(response)

            if self._is_authenticated(response):
                break

            if self._auth_retries >= MAX_AUTH_RETRIES:
                raise UnableToAuthorize()

            response = await self._try_auth()

    @staticmethod
    def _is_security_check(response: str) -> bool:
        return 'login?act=authcheck_code' in response

    async def _auth_security_check(self, response: str):
        html_tree = html.fromstring(response)
        self._saved_check_form = self._get_form(html_tree)

        prefixes = html_tree.cssselect('.field_prefix')
        is_phone_check = (
            len(prefixes) == 2
            and self._auth_phone.startswith(prefixes[0].text)
            and self._auth_phone.endswith(prefixes[1].text)
            and len(self._saved_check_form['fields']) == 1
        )

        if is_phone_check:
            code = self._auth_phone[len(prefixes[0].text) - 1:-len(prefixes[1].text)]
            return await self.complete_security_check(code=code)

        raise CheckRequiresUserIntervention(self._saved_check_form['fields'])

    async def complete_security_check(self, **form):
        if self._saved_check_form is None:
            raise NoSavedCheckForm()
        if set(self._saved_check_form['fields'].keys()) != set(form.keys()):
            raise FieldsMismatchSavedCheckForm()

        response = await self._post_form(self._saved_check_form['url'], **form)
        self._saved_check_form = None
        self._save_cookie()

        if not self._is_authenticated(response):
            self._clear_cookie()
            raise AuthRequired()

        return response

    async def get(self, url, **kwargs):
        if not self._has_cookie:
            raise AuthRequired()

        async with aiohttp.ClientSession(cookie_jar=self._cookie_jar) as session:
            async with session.get(vk_url(url), **kwargs) as response:
                response = await response.text()

        if not self._is_authenticated(response):
            self._clear_cookie()
            raise AuthRequired()

        return response


async def main():
    session = VkSession()
    try:
        await session.auth()
        response = await session.get('feed')
    except CheckRequiresUserIntervention as ex:
        form = {}
        for field, value in ex.form.items():
            if value is None:
                form[field] = input(field + ': ')
            else:
                form[field] = value
        response = await session.complete_security_check(**form)

    print('Success!')
    print(response)


if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
