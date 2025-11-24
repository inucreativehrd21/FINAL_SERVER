"""
코딩 테스트 앱 테스트
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import User
from .models import Problem


class CodingTestTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass')
        self.client.force_authenticate(user=self.user)

        # 테스트 문제 생성
        self.problem = Problem.objects.create(
            problem_id='1000',
            title='A+B',
            level=1,
            tags=['수학', '구현'],
            description='두 정수 A와 B를 입력받은 다음, A+B를 출력하는 프로그램을 작성하시오.',
            input_description='첫째 줄에 A와 B가 주어진다.',
            output_description='첫째 줄에 A+B를 출력한다.',
            examples=[{'input': '1 2', 'output': '3'}]
        )

    def test_get_problems(self):
        """문제 목록 조회 테스트"""
        response = self.client.get('/api/v1/coding-test/problems/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_problem_detail(self):
        """문제 상세 조회 테스트"""
        response = self.client.get(f'/api/v1/coding-test/problems/{self.problem.problem_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
