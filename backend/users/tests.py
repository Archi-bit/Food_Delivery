from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient


class BrowserSessionTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('persistent', password='PersistentPassword357!')
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        response = self.client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        return response.data['csrf_token']

    def login(self):
        return self.client.post('/api/auth/session/login/', {'username':'persistent', 'password':'PersistentPassword357!'}, HTTP_X_CSRFTOKEN=self.csrf())

    def test_login_persistent_httponly_cookie(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        cookie = response.cookies['sessionid']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(cookie['max-age'], 604800)
        self.assertNotIn('refresh', response.data)
        reloaded = APIClient(enforce_csrf_checks=True)
        reloaded.cookies['sessionid'] = cookie.value
        session_response = reloaded.get('/api/auth/session/')
        self.assertEqual(session_response['Cache-Control'], 'no-store')
        session = session_response.data
        self.assertEqual(session['user']['username'], 'persistent')
        reloaded.credentials(HTTP_AUTHORIZATION='Bearer '+session['access'])
        self.assertEqual(reloaded.get('/api/auth/me/').status_code, 200)

    def test_anonymous_session(self):
        self.assertEqual(self.client.get('/api/auth/session/').data, {'access':None, 'user':None})

    def test_login_register_logout_require_csrf(self):
        for path in ('login','register','logout'):
            self.assertEqual(self.client.post(f'/api/auth/session/{path}/', {}).status_code, 403)

    def test_cross_site_login_rejected(self):
        response = self.client.post('/api/auth/session/login/', {'username':'persistent','password':'PersistentPassword357!'}, HTTP_X_CSRFTOKEN=self.csrf(), HTTP_ORIGIN='https://foreign.example.invalid')
        self.assertEqual(response.status_code, 403)

    def test_logout_revokes_session_in_database(self):
        self.login()
        session_key = self.client.cookies['sessionid'].value
        response = self.client.post('/api/auth/session/logout/', {}, HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())
        self.assertIsNone(self.client.get('/api/auth/session/').data['access'])
        replay = APIClient()
        replay.cookies['sessionid'] = session_key
        self.assertIsNone(replay.get('/api/auth/session/').data['access'])

    def test_registration_creates_session(self):
        response = self.client.post('/api/auth/session/register/', {'username':'new_browser', 'email':'browser@example.invalid', 'password':'BrowserPassword789!', 'password2':'BrowserPassword789!'}, HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.get('/api/auth/session/').data['user']['username'], 'new_browser')

    def test_invalid_credentials_do_not_create_session(self):
        response = self.client.post('/api/auth/session/login/', {'username':'persistent','password':'wrong'}, HTTP_X_CSRFTOKEN=self.csrf())
        self.assertIn(response.status_code, (400,401,403))
        self.assertNotIn('sessionid', response.cookies)

    def test_inactive_user_session_is_rejected(self):
        self.login()
        self.user.is_active=False
        self.user.save()
        self.assertIsNone(self.client.get('/api/auth/session/').data['access'])

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_https_cookies_secure(self):
        csrf=self.client.get('/api/auth/csrf/', secure=True)
        response=self.client.post('/api/auth/session/login/', {'username':'persistent','password':'PersistentPassword357!'}, secure=True, HTTP_X_CSRFTOKEN=csrf.data['csrf_token'], HTTP_REFERER='https://testserver/')
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(response.cookies['sessionid']['secure'])
        self.assertTrue(response.cookies['csrftoken']['secure'])
