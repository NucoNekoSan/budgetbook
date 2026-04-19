from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthRedirectTest(TestCase):

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertRedirects(resp, '/accounts/login/?next=/')

    def test_annual_requires_login(self):
        resp = self.client.get(reverse('ledger:annual'))
        self.assertRedirects(resp, '/accounts/login/?next=/annual/')

    def test_settings_requires_login(self):
        resp = self.client.get(reverse('ledger:settings'))
        self.assertRedirects(resp, '/accounts/login/?next=/settings/')

    def test_export_requires_login(self):
        resp = self.client.get(reverse('ledger:transaction_export'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_login_page_accessible(self):
        resp = self.client.get('/accounts/login/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ログイン')

    def test_password_change_url_returns_404(self):
        resp = self.client.get('/accounts/password_change/')
        self.assertEqual(resp.status_code, 404)

    def test_password_reset_url_returns_404(self):
        resp = self.client.get('/accounts/password_reset/')
        self.assertEqual(resp.status_code, 404)


class AuthLoginLogoutTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser', password='testpass123',
        )

    def test_login_success_redirects_to_dashboard(self):
        resp = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertRedirects(resp, '/')

    def test_login_with_next_param(self):
        resp = self.client.post('/accounts/login/?next=/annual/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertRedirects(resp, '/annual/')

    def test_login_failure_shows_error(self):
        resp = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ユーザー名またはパスワードが正しくありません')

    def test_authenticated_user_can_access_dashboard(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_redirects_to_login(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post('/accounts/logout/')
        self.assertRedirects(resp, '/accounts/login/')

    def test_after_logout_cannot_access_dashboard(self):
        self.client.login(username='testuser', password='testpass123')
        self.client.post('/accounts/logout/')
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertRedirects(resp, '/accounts/login/?next=/')

    def test_authenticated_user_redirected_from_login_page(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get('/accounts/login/')
        self.assertRedirects(resp, '/')
