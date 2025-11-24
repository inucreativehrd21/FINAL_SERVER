"""
인증 앱 테스트
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = '/api/v1/auth/signup/'
        self.login_url = '/api/v1/auth/login/'

    def test_user_signup(self):
        """회원가입 테스트"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123!',
            'password_confirm': 'testpass123!'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_user_login(self):
        """로그인 테스트"""
        # 먼저 사용자 생성
        User.objects.create_user(username='testuser', email='test@example.com', password='testpass123!')

        # 로그인 시도
        data = {
            'username': 'testuser',
            'password': 'testpass123!'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data['data'])
