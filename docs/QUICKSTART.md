# FINAL_SERVER Quickstart (Local Docker)

이 리포지터리를 로컬(또는 EC2)에서 프론트엔드/백엔드를 바로 확인하고 테스트할 수 있는 최소 단계입니다.

## 1) 필수 도구
- Docker, Docker Compose
- sudo 권한(리눅스에서 docker 접속 시 필요할 수 있음)

## 2) 환경 변수 준비
```
cp .env.example .env
```
필수 항목을 채웁니다.
- `ALLOWED_HOSTS`: `localhost,127.0.0.1,<EC2_프라이빗IP>,<EC2_퍼블릭IP>` 식으로 접속에 사용할 호스트/IP 모두 추가
- `VITE_API_BASE_URL`: 로컬에서 확인 시 `http://localhost:8000/api/v1` 권장 (EC2 프라이빗 IP로 테스트하면 `http://172.31.46.177:8000/api/v1`처럼 맞춰 입력)
- DB/REDIS 패스워드는 기본값 그대로 사용 가능 (docker-compose가 같은 값을 사용)

## 3) 컨테이너 빌드 및 실행
```
sudo docker compose up -d --build
```
첫 실행 후 스키마/정적 파일을 준비합니다:
```
sudo docker compose exec backend python manage.py migrate
sudo docker compose exec backend python manage.py collectstatic --noinput
```

## 4) 접속 포트
- 프론트엔드 Vite dev: http://localhost:3000
- 백엔드 API: http://localhost:8000/api/v1
- Nginx 리버스 프록시: http://localhost (80), https://localhost (443, 인증서 설정 시)

## 5) 원격에서 접속하려면
- EC2 보안 그룹에서 80(또는 3000/8000 필요 시) 인바운드 오픈
- `.env`의 `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `VITE_API_BASE_URL`에 퍼블릭 도메인/IP 추가

## 6) 정지/재시작
```
sudo docker compose down          # 중지
sudo docker compose up -d         # 재기동
```

## 7) 실시간 로그 보기
`./tail-logs.sh` 스크립트로 확인 (아래 파일 참조).
예)
```
./tail-logs.sh            # 전체 서비스 로그
./tail-logs.sh backend    # 특정 서비스만
```

## 8) 자주 쓰는 문제 해결
- 포트 충돌: 80/3000/8000을 쓰는 다른 프로세스가 없는지 확인 후 중지
- `ALLOWED_HOSTS` 에러: 접속한 IP/도메인이 `.env`에 없으면 400 반환 → 추가 후 `docker compose up -d`로 재시작
- DB 초기화 필요: `sudo docker compose down -v`로 볼륨 포함 초기화 가능(데이터 삭제 주의)
