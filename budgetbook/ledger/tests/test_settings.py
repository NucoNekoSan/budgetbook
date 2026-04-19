from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, Category


class SettingsPageTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', password='pass')
        cls.account = Account.objects.create(name='メイン口座', opening_balance=10000)
        cls.category = Category.objects.create(name='食費', kind=Category.Kind.EXPENSE)

    def setUp(self):
        self.client.login(username='test', password='pass')

    def test_settings_page_loads(self):
        resp = self.client.get(reverse('ledger:settings'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '設定')
        self.assertContains(resp, '家計簿に戻る')

    def test_settings_page_shows_accounts_and_categories(self):
        resp = self.client.get(reverse('ledger:settings'))
        self.assertContains(resp, 'メイン口座')
        self.assertContains(resp, '食費')


class AccountCrudTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', password='pass')

    def setUp(self):
        self.client.login(username='test', password='pass')

    def test_create_account(self):
        resp = self.client.post(reverse('ledger:account_create'), {
            'name': '新規口座',
            'opening_balance': 5000,
            'notes': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Account.objects.filter(name='新規口座').exists())
        self.assertContains(resp, '口座を追加しました')

    def test_duplicate_name_shows_friendly_error(self):
        Account.objects.create(name='既存口座')
        resp = self.client.post(reverse('ledger:account_create'), {
            'name': '既存口座',
            'opening_balance': 0,
            'notes': '',
        })
        self.assertEqual(resp.status_code, 422)
        self.assertContains(resp, '既に使われています', status_code=422)

    def test_edit_account_name(self):
        acct = Account.objects.create(name='旧名', opening_balance=1000)
        resp = self.client.post(reverse('ledger:account_update', args=[acct.pk]), {
            'name': '新名',
            'opening_balance': 1000,
            'notes': '',
        })
        self.assertEqual(resp.status_code, 200)
        acct.refresh_from_db()
        self.assertEqual(acct.name, '新名')

    def test_edit_account_opening_balance_is_ignored(self):
        acct = Account.objects.create(name='残高テスト', opening_balance=5000)
        self.client.post(reverse('ledger:account_update', args=[acct.pk]), {
            'name': '残高テスト',
            'opening_balance': 99999,
            'notes': '',
        })
        acct.refresh_from_db()
        self.assertEqual(acct.opening_balance, 5000)

    def test_toggle_account(self):
        acct = Account.objects.create(name='トグル口座')
        self.assertTrue(acct.is_active)
        self.client.post(reverse('ledger:account_toggle', args=[acct.pk]))
        acct.refresh_from_db()
        self.assertFalse(acct.is_active)
        self.client.post(reverse('ledger:account_toggle', args=[acct.pk]))
        acct.refresh_from_db()
        self.assertTrue(acct.is_active)


class CategoryCrudTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', password='pass')

    def setUp(self):
        self.client.login(username='test', password='pass')

    def test_create_category(self):
        resp = self.client.post(reverse('ledger:category_create'), {
            'name': '交通費',
            'kind': 'expense',
            'notes': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Category.objects.filter(name='交通費').exists())

    def test_duplicate_category_name_shows_friendly_error(self):
        Category.objects.create(name='食費', kind=Category.Kind.EXPENSE)
        resp = self.client.post(reverse('ledger:category_create'), {
            'name': '食費',
            'kind': 'income',
            'notes': '',
        })
        self.assertEqual(resp.status_code, 422)
        self.assertContains(resp, '既に使われています', status_code=422)

    def test_edit_category_kind_is_immutable(self):
        cat = Category.objects.create(name='給与', kind=Category.Kind.INCOME)
        self.client.post(reverse('ledger:category_update', args=[cat.pk]), {
            'name': '給与改名',
            'kind': 'expense',
            'notes': '',
        })
        cat.refresh_from_db()
        self.assertEqual(cat.name, '給与改名')
        self.assertEqual(cat.kind, Category.Kind.INCOME)

    def test_toggle_category(self):
        cat = Category.objects.create(name='趣味', kind=Category.Kind.EXPENSE)
        self.client.post(reverse('ledger:category_toggle', args=[cat.pk]))
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)


class SettingsAffectsTransactionFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', password='pass')
        cls.account = Account.objects.create(name='口座X')
        cls.category = Category.objects.create(name='光熱費', kind=Category.Kind.EXPENSE)

    def setUp(self):
        self.client.login(username='test', password='pass')

    def test_disabled_account_hidden_from_transaction_form(self):
        self.account.is_active = False
        self.account.save()
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertNotContains(resp, '口座X')

    def test_new_account_appears_in_transaction_form(self):
        Account.objects.create(name='新しい口座')
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertContains(resp, '新しい口座')

    def test_disabled_category_hidden_from_transaction_form(self):
        self.category.is_active = False
        self.category.save()
        resp = self.client.get(reverse('ledger:dashboard'))
        self.assertNotContains(resp, '光熱費')