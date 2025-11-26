"""Module containing tests for testing third party libraries implementation.

These tests are sometimes false positives so we pu them out of CI/CD
"""

import re
import time
from unittest import mock

from captcha.models import CaptchaStore
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

user_model = get_user_model()


class DeactivateProfile3rdpartyTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create(
            email="deactivate_profile@testuser.com",
            username="deactivate_profile",
        )
        self.user.set_password("12345o")
        self.user.save()
        self.client.login(username="deactivate_profile", password="12345o")

    def __extract_hash_and_response(self, r):
        hash_ = re.findall(
            r'value="([0-9a-f]+)" required id="id_captcha_', str(r.content)
        )[0]
        response = CaptchaStore.objects.get(hashkey=hash_).response
        return hash_, response

    def valid_captcha(self):
        r = self.client.get(reverse("deactivate_profile"))
        self.assertEqual(r.status_code, 200)
        hash_, response = self.__extract_hash_and_response(r)
        return self.client.post(
            reverse("deactivate_profile"), dict(captcha_0=hash_, captcha_1=response)
        )

    def test_deactivate_profile_page_deactivate_valid_form_redirects_to_inactive(
        self,
    ):
        time.sleep(5)
        response = self.valid_captcha()
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/accounts/inactive/", response.url)

    def test_deactivate_profile_page_deactivate_valid_form_calls_deactivate_profile(
        self,
    ):
        time.sleep(5)
        with mock.patch(
            "core.forms.DeactivateProfileForm.deactivate_profile"
        ) as mock_deactivate:
            self.valid_captcha()
            self.assertNotEqual(mock_deactivate.call_args_list, [])
