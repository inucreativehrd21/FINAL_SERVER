"""
코드 실행 유틸리티
안전하게 사용자 코드를 실행하고 결과를 반환합니다.
"""
import subprocess
import tempfile
import os
from pathlib import Path
from django.conf import settings


class CodeExecutor:
    """Python 코드 실행기"""

    def __init__(self, timeout=None, max_output=None):
        self.timeout = timeout or settings.CODE_EXECUTION_TIMEOUT
        self.max_output = max_output or settings.CODE_EXECUTION_MAX_OUTPUT

    def execute_python(self, code: str, input_data: str = "") -> dict:
        """
        Python 코드를 실행하고 결과를 반환합니다.

        Args:
            code: 실행할 Python 코드
            input_data: 표준 입력으로 전달할 데이터

        Returns:
            dict: {
                'success': bool,
                'output': str,
                'error': str,
                'execution_time': float
            }
        """
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name

        try:
            # 코드 실행
            process = subprocess.Popen(
                ['python', temp_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=self.timeout
                )

                # 출력 길이 제한
                if len(stdout) > self.max_output:
                    stdout = stdout[:self.max_output] + "\n... (출력이 너무 깁니다)"

                if len(stderr) > self.max_output:
                    stderr = stderr[:self.max_output] + "\n... (오류 메시지가 너무 깁니다)"

                # 성공 여부 판단
                success = process.returncode == 0

                return {
                    'success': success,
                    'output': stdout if success else '',
                    'error': stderr if not success else '',
                    'return_code': process.returncode
                }

            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    'success': False,
                    'output': '',
                    'error': f'실행 시간 초과 ({self.timeout}초)',
                    'return_code': -1
                }

        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f'실행 오류: {str(e)}',
                'return_code': -1
            }

        finally:
            # 임시 파일 삭제
            try:
                os.unlink(temp_file)
            except:
                pass

    def run_test_cases(self, code: str, test_cases: list) -> dict:
        """
        여러 테스트 케이스를 실행합니다.

        Args:
            code: 실행할 Python 코드
            test_cases: 테스트 케이스 리스트 [{'input': str, 'output': str}, ...]

        Returns:
            dict: {
                'success': bool,
                'passed': int,
                'total': int,
                'results': list,
                'error': str
            }
        """
        results = []
        passed = 0

        for idx, test_case in enumerate(test_cases):
            input_data = test_case.get('input', '')
            expected_output = test_case.get('output', '').strip()

            # 코드 실행
            result = self.execute_python(code, input_data)

            if result['success']:
                actual_output = result['output'].strip()
                is_passed = actual_output == expected_output

                if is_passed:
                    passed += 1

                results.append({
                    'test_case': idx + 1,
                    'passed': is_passed,
                    'input': input_data,
                    'expected': expected_output,
                    'actual': actual_output,
                    'error': ''
                })
            else:
                results.append({
                    'test_case': idx + 1,
                    'passed': False,
                    'input': input_data,
                    'expected': expected_output,
                    'actual': '',
                    'error': result['error']
                })

        total = len(test_cases)
        all_passed = passed == total

        return {
            'success': all_passed,
            'passed': passed,
            'total': total,
            'results': results,
            'error': '' if all_passed else f'{total - passed}개의 테스트 케이스 실패'
        }
