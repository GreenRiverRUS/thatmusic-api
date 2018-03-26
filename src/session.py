import random
from hashlib import md5
import os
from typing import Optional, Union, Dict

from lxml import html
from lxml.etree import ElementTree
import aiohttp
from tornado import web

from settings import AUTH_ACCOUNTS, PATHS, MAX_AUTH_RETRIES
from utils import vk_url, setup_logger, BasicHandler, logged

logger = setup_logger('auth')


class AuthError(Exception):
    pass


class TwoFactorAuth(AuthError):
    def __init__(self, form_fields):
        self.form_fields = form_fields


class UnableToAuthorize(AuthError):
    pass


class FieldsMismatchSavedCheckForm(AuthError):
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
        if os.path.exists(self._cookie_path):
            self._cookie_jar.load(self._cookie_path)

    @property
    def _has_cookie(self) -> bool:
        return len(self._cookie_jar) > 0

    def _save_cookie(self):
        self._cookie_jar.save(self._cookie_path)

    def _clear_cookie(self):
        if self._has_cookie:
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

        if self._auth_retries > MAX_AUTH_RETRIES:
            logger.error('Reached max auth retries')
            raise UnableToAuthorize()

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
        logger.debug('Authorizing (attempt={})'.format(self._auth_retries))
        while True:
            response = await self._try_auth()

            if self._is_security_check(response):
                logger.debug('Met security check')
                response = await self._auth_security_check(response)

            if self._is_authenticated(response):
                break

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

        logger.debug('Unknown security check. User required to pass second factor')
        raise TwoFactorAuth(self.get_saved_check_form_empty_fields())

    def get_saved_check_form_empty_fields(self):
        if self._saved_check_form is None:
            raise AuthRequired()
        return set(k for k, v in self._saved_check_form['fields'].items() if v is None)

    def _build_check_form(self, **kwargs):
        if self.get_saved_check_form_empty_fields() != set(kwargs.keys()):
            raise FieldsMismatchSavedCheckForm()

        form_url = self._saved_check_form['url']
        form_fields = dict(self._saved_check_form['fields'])
        form_fields.update(kwargs)
        return form_url, form_fields

    async def complete_security_check(self, **form):
        form_url, form_fields = self._build_check_form(**form)
        response = await self._post_form(form_url, **form_fields)
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


# TODO Change auth to web-form
class AuthHandler(BasicHandler):
    @web.addslash
    @logged(logger)
    async def get(self, *args, **kwargs):
        vk_session = self.settings['vk_session']  # type: VkSession
        try:
            await vk_session.auth()
            self.write_result({'success': 1})
        except TwoFactorAuth as ex:
            self.write_result({
                'success': 0,
                'error': 'Unauthorized. Enter {}: {}'.format(
                    ', '.join(ex.form_fields),
                    self.reverse_full_url('auth_second_factor')
                ),
                'error_code': 401
            })
        except UnableToAuthorize:
            self.write_result({
                'success': 0,
                'error': 'No retries left. Sorry :(',
                'error_code': 503
            })


class AuthSecondStepHandler(BasicHandler):
    @web.addslash
    @logged(logger)
    async def get(self, *args, **kwargs):
        vk_session = self.settings['vk_session']  # type: VkSession
        try:
            form = {}
            for field_name in vk_session.get_saved_check_form_empty_fields():
                form[field_name] = self.get_argument(field_name)
            await vk_session.complete_security_check(**form)
            self.write_result({'success': 1})
        except web.MissingArgumentError as ex:
            self.write_result({
                'success': 0,
                'error': 'Missing query argument \'{}\''.format(
                    ex.arg_name
                )
            })
        except AuthRequired:
            self.write_result({
                'success': 0,
                'error': 'Unauthorized. Auth required: {}'.format(
                    self.reverse_full_url('auth')
                ),
                'error_code': 401
            })
