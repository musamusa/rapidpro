from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import LiveServerTestCase

from temba.tests import TembaTest

from temba.utils import get_chrome_drive_suffix
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class UserTest(TembaTest):
    def test_user_model(self):
        long_username = 'bob12345678901234567890123456789012345678901234567890@msn.com'
        User.objects.create(username=long_username, email=long_username)


class SeleniumUserLogin(TembaTest, LiveServerTestCase):
    def setUp(self):
        chrome_driver_path = '%s/selenium/chromedriver_%s' % (settings.MEDIA_ROOT, get_chrome_drive_suffix())

        self.default_url = 'http://127.0.0.1:8000'

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920x1080")

        self.driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver_path)

        super(SeleniumUserLogin, self).setUp()

    def test_login(self):
        driver = self.driver
        url = '%s%s' % (self.default_url, reverse('users.user_login'))
        driver.get(url)
        self.assertContains('Sign in', driver.page_source)

    def tearDown(self):
        self.driver.close()

        super(SeleniumUserLogin, self).tearDown()
