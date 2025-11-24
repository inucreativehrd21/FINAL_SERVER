"""
성능 테스트 스크립트
실행 방법: python performance_test.py
"""
import requests
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 테스트 설정
# Docker 컨테이너 내부에서는 서비스명으로 접근
# 외부에서 실행 시 localhost, 컨테이너 내부에서 실행 시 backend
import os
BASE_URL = os.environ.get("TEST_BASE_URL", "http://backend:8000/api/v1")

# 성능 테스트용 사용자
TEST_USER = {
    "email": "admin@proj.com",
    "password": "admin1234",
    "username": "admin"
}

class PerformanceTest:
    def __init__(self):
        self.results = {}
        self.access_token = None
        self.refresh_token = None

    def setup(self):
        """테스트 사용자 생성 및 로그인"""
        print("\n" + "="*60)
        print("성능 테스트 시작")
        print("="*60)
        print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"테스트 대상: {BASE_URL}")
        print("="*60 + "\n")

        # 회원가입은 건너뜀 (이미 생성된 사용자 사용)

        # 로그인
        try:
            login_data = {
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            }
            print(f"[DEBUG] 로그인 시도: {login_data}")

            response = requests.post(f"{BASE_URL}/auth/login/", json=login_data, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # 응답 구조: { data: { tokens: { access, refresh } } }
                tokens = data.get('data', {}).get('tokens', {})
                self.access_token = tokens.get('access')
                self.refresh_token = tokens.get('refresh')
                if self.access_token:
                    print("[설정] 테스트 사용자 로그인 성공\n")
                else:
                    print(f"[경고] 토큰을 찾을 수 없습니다. 응답: {data}")
                    print("인증이 필요한 테스트는 건너뜁니다.\n")
            else:
                print(f"[경고] 로그인 실패: {response.status_code}")
                print(f"[DEBUG] 응답: {response.text[:200]}")
                print("인증이 필요한 테스트는 건너뜁니다.\n")
        except Exception as e:
            print(f"[경고] 로그인 오류: {e}")
            print("인증이 필요한 테스트는 건너뜁니다.\n")

    def get_headers(self):
        """인증 헤더 반환"""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def measure_response_time(self, name, method, url, **kwargs):
        """단일 요청의 응답 시간 측정"""
        times = []
        success_count = 0
        fail_count = 0
        iterations = kwargs.pop('iterations', 5)
        expected_codes = kwargs.pop('expected_codes', [200, 201])

        for i in range(iterations):
            try:
                start = time.time()
                if method == "GET":
                    response = requests.get(url, **kwargs)
                elif method == "POST":
                    response = requests.post(url, **kwargs)
                end = time.time()

                elapsed = (end - start) * 1000  # ms
                times.append(elapsed)

                if response.status_code in expected_codes:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"    [DEBUG] {name} - Status: {response.status_code}, URL: {url}")

            except Exception as e:
                fail_count += 1
                times.append(0)
                print(f"    [DEBUG] {name} - Error: {e}")

        # 결과 계산
        valid_times = [t for t in times if t > 0]
        if valid_times:
            avg_time = statistics.mean(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
        else:
            avg_time = min_time = max_time = 0

        self.results[name] = {
            "avg_ms": round(avg_time, 2),
            "min_ms": round(min_time, 2),
            "max_ms": round(max_time, 2),
            "success": success_count,
            "fail": fail_count,
            "iterations": iterations
        }

        return avg_time

    def test_pt001_login_response(self):
        """PT_001: 로그인 응답 시간 테스트"""
        print("[PT_001] 로그인 응답 시간 테스트...")

        avg_time = self.measure_response_time(
            "PT_001_로그인_응답시간",
            "POST",
            f"{BASE_URL}/auth/login/",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
            timeout=10,
            iterations=5,
            expected_codes=[200, 201, 400, 401]  # 로그인 실패도 응답은 받음
        )

        # 기준: 2초 이내
        passed = avg_time < 2000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 2000ms)")
        print(f"  결과: {status}\n")

        return passed

    def test_pt002_problems_list(self):
        """PT_002: 문제 목록 로딩 시간 테스트"""
        print("[PT_002] 문제 목록 로딩 시간 테스트...")

        avg_time = self.measure_response_time(
            "PT_002_문제목록_로딩시간",
            "GET",
            f"{BASE_URL}/coding-test/problems/",
            headers=self.get_headers(),
            timeout=10,
            iterations=5
        )

        # 기준: 3초 이내
        passed = avg_time < 3000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 3000ms)")
        print(f"  결과: {status}\n")

        return passed

    def test_pt003_hint_generation(self):
        """PT_003: 힌트 생성 응답 시간 테스트"""
        print("[PT_003] 힌트 생성 응답 시간 테스트...")

        if not self.access_token:
            print("  [건너뜀] 인증 토큰이 없습니다.\n")
            return None

        avg_time = self.measure_response_time(
            "PT_003_힌트생성_응답시간",
            "POST",
            f"{BASE_URL}/coding-test/hints/",
            headers=self.get_headers(),
            json={
                "problem_id": "1001",  # 문자열로 전송 (JSON 데이터 형식과 일치)
                "user_code": "n = int(input())\nprint(n)",
                "hint_level": 1
            },
            timeout=60,
            iterations=3,  # API 호출 비용 고려
            expected_codes=[200, 201]
        )

        # 기준: 10초 이내
        passed = avg_time < 10000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 10000ms)")
        print(f"  결과: {status}\n")

        return passed

    def test_pt004_code_execution(self):
        """PT_004: 코드 실행 응답 시간 테스트"""
        print("[PT_004] 코드 실행 응답 시간 테스트...")

        if not self.access_token:
            print("  [건너뜀] 인증 토큰이 없습니다.\n")
            return None

        avg_time = self.measure_response_time(
            "PT_004_코드실행_응답시간",
            "POST",
            f"{BASE_URL}/coding-test/execute/",
            headers=self.get_headers(),
            json={
                "code": "print('Hello, World!')",
                "problem_id": 1001
            },
            timeout=10,
            iterations=5
        )

        # 기준: 5초 이내
        passed = avg_time < 5000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 5000ms)")
        print(f"  결과: {status}\n")

        return passed

    def test_pt005_concurrent_users(self):
        """PT_005: 동시 사용자 부하 테스트"""
        print("[PT_005] 동시 사용자 부하 테스트 (50명)...")

        concurrent_users = 50
        success_count = 0
        fail_count = 0
        times = []

        def make_request(user_id):
            try:
                start = time.time()
                response = requests.get(
                    f"{BASE_URL}/coding-test/problems/",
                    headers=self.get_headers(),
                    timeout=10
                )
                end = time.time()

                return {
                    "user_id": user_id,
                    "status": response.status_code,
                    "time_ms": (end - start) * 1000,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "user_id": user_id,
                    "status": 0,
                    "time_ms": 0,
                    "success": False,
                    "error": str(e)
                }

        # 동시 요청 실행
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_users)]

            for future in as_completed(futures):
                result = future.result()
                if result["success"]:
                    success_count += 1
                    times.append(result["time_ms"])
                else:
                    fail_count += 1

        # 결과 계산
        if times:
            avg_time = statistics.mean(times)
            max_time = max(times)
        else:
            avg_time = max_time = 0

        self.results["PT_005_동시사용자_부하테스트"] = {
            "concurrent_users": concurrent_users,
            "success": success_count,
            "fail": fail_count,
            "avg_ms": round(avg_time, 2),
            "max_ms": round(max_time, 2)
        }

        # 기준: 90% 이상 성공
        success_rate = (success_count / concurrent_users) * 100
        passed = success_rate >= 90
        status = "통과" if passed else "실패"

        print(f"  동시 사용자: {concurrent_users}명")
        print(f"  성공: {success_count}, 실패: {fail_count} (성공률: {success_rate:.1f}%)")
        print(f"  평균 응답 시간: {avg_time:.2f}ms, 최대: {max_time:.2f}ms")
        print(f"  결과: {status}\n")

        return passed

    def test_pt006_mypage_stats(self):
        """PT_006: 마이페이지 통계 로딩 테스트"""
        print("[PT_006] 마이페이지 통계 로딩 테스트...")

        if not self.access_token:
            print("  [건너뜀] 인증 토큰이 없습니다.\n")
            return None

        avg_time = self.measure_response_time(
            "PT_006_마이페이지_통계로딩",
            "GET",
            f"{BASE_URL}/mypage/statistics/",
            headers=self.get_headers(),
            timeout=10,
            iterations=5
        )

        # 기준: 2초 이내
        passed = avg_time < 2000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 2000ms)")
        print(f"  결과: {status}\n")

        return passed

    def test_pt007_roadmap_generation(self):
        """PT_007: 로드맵 조회 시간 테스트"""
        print("[PT_007] 로드맵 조회 시간 테스트...")

        if not self.access_token:
            print("  [건너뜀] 인증 토큰이 없습니다.\n")
            return None

        avg_time = self.measure_response_time(
            "PT_007_로드맵_조회시간",
            "GET",
            f"{BASE_URL}/coding-test/roadmap/",
            headers=self.get_headers(),
            timeout=10,
            iterations=5
        )

        # 기준: 3초 이내
        passed = avg_time < 3000
        status = "통과" if passed else "실패"
        print(f"  평균 응답 시간: {avg_time:.2f}ms (기준: 3000ms)")
        print(f"  결과: {status}\n")

        return passed

    def generate_report(self):
        """테스트 결과 보고서 생성"""
        print("\n" + "="*60)
        print("성능 테스트 결과 보고서")
        print("="*60)
        print(f"테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # 결과 요약 테이블
        print("테스트 케이스 ID | 테스트 항목 | 평균 응답 시간 | 성능 기준 | 결과")
        print("-" * 80)

        test_criteria = {
            "PT_001_로그인_응답시간": ("로그인 응답 시간", 2000),
            "PT_002_문제목록_로딩시간": ("문제 목록 로딩", 3000),
            "PT_003_힌트생성_응답시간": ("힌트 생성 응답", 10000),
            "PT_004_코드실행_응답시간": ("코드 실행 응답", 5000),
            "PT_005_동시사용자_부하테스트": ("동시 사용자 부하", None),
            "PT_006_마이페이지_통계로딩": ("마이페이지 통계", 2000),
            "PT_007_로드맵_조회시간": ("로드맵 조회", 3000),
        }

        for test_id, (test_name, criteria) in test_criteria.items():
            if test_id in self.results:
                result = self.results[test_id]
                avg_ms = result.get("avg_ms", 0)

                if test_id == "PT_005_동시사용자_부하테스트":
                    success_rate = (result["success"] / result["concurrent_users"]) * 100
                    passed = success_rate >= 90
                    print(f"{test_id.split('_')[0]+'_'+test_id.split('_')[1]} | {test_name} | {avg_ms}ms | 성공률 90% | {'통과' if passed else '실패'}")
                else:
                    passed = avg_ms < criteria
                    print(f"{test_id.split('_')[0]+'_'+test_id.split('_')[1]} | {test_name} | {avg_ms}ms | {criteria}ms | {'통과' if passed else '실패'}")

        print("\n" + "="*60)

        # JSON 결과 저장
        report_path = "performance_test_results.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "results": self.results
            }, f, ensure_ascii=False, indent=2)

        print(f"\n상세 결과가 '{report_path}'에 저장되었습니다.")

    def run_all_tests(self):
        """모든 테스트 실행"""
        self.setup()

        # 테스트 실행
        self.test_pt001_login_response()
        self.test_pt002_problems_list()
        self.test_pt003_hint_generation()
        self.test_pt004_code_execution()
        self.test_pt005_concurrent_users()
        self.test_pt006_mypage_stats()
        self.test_pt007_roadmap_generation()

        # 보고서 생성
        self.generate_report()


if __name__ == "__main__":
    tester = PerformanceTest()
    tester.run_all_tests()
