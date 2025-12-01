# GitHub Actions CI/CD 설정 가이드

이 문서는 GitHub Actions를 이용한 자동 배포 설정 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [사전 준비사항](#사전-준비사항)
3. [GitHub Secrets 설정](#github-secrets-설정)
4. [워크플로우 설명](#워크플로우-설명)
5. [배포 프로세스](#배포-프로세스)
6. [롤백 방법](#롤백-방법)
7. [문제 해결](#문제-해결)

---

## 개요

이 프로젝트는 GitHub Actions를 사용하여 `main` 브랜치에 코드가 푸시될 때마다 자동으로 EC2 인스턴스에 배포됩니다.

### CI/CD 워크플로우

```
코드 Push → GitHub Actions 트리거 → EC2 SSH 접속 →
코드 Pull → Docker 이미지 빌드 → 컨테이너 재시작 → 헬스 체크
```

---

## 사전 준비사항

### 1. EC2 인스턴스 설정 확인

EC2 인스턴스에서 다음이 설치되어 있어야 합니다:
- ✅ Git
- ✅ Docker
- ✅ Docker Compose

### 2. SSH 키 생성 (로컬 또는 다른 머신에서)

```bash
# SSH 키 페어 생성 (로컬 컴퓨터에서 실행)
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_key

# 공개키를 EC2 인스턴스에 복사
ssh-copy-id -i ~/.ssh/github_actions_key.pub ec2-user@<EC2_PUBLIC_IP>
```

또는 수동으로:

```bash
# 공개키 내용 확인
cat ~/.ssh/github_actions_key.pub

# EC2에 접속하여 authorized_keys에 추가
ssh ec2-user@<EC2_PUBLIC_IP>
echo "<공개키 내용>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Private Key 내용 확인

```bash
# Private Key 전체 내용 복사 (이것을 GitHub Secrets에 등록)
cat ~/.ssh/github_actions_key
```

---

## GitHub Secrets 설정

### 1. GitHub Repository Settings로 이동

```
GitHub Repository → Settings → Secrets and variables → Actions → New repository secret
```

### 2. 필수 Secrets 추가

다음 3개의 Secrets를 추가해야 합니다:

#### `EC2_HOST`
- **설명**: EC2 인스턴스의 Public IP 또는 도메인
- **예시**: `3.37.186.224` 또는 `your-domain.com`
- **확인 방법**:
  ```bash
  # EC2 콘솔에서 확인하거나
  curl ifconfig.me
  ```

#### `EC2_USERNAME`
- **설명**: EC2 인스턴스 SSH 사용자명
- **값**: `ec2-user` (Amazon Linux의 경우)
- **참고**: Ubuntu의 경우 `ubuntu`, Debian의 경우 `admin`

#### `EC2_SSH_KEY`
- **설명**: SSH Private Key 전체 내용
- **값**: `~/.ssh/github_actions_key` 파일의 전체 내용
- **형식**:
  ```
  -----BEGIN RSA PRIVATE KEY-----
  [키 내용]
  -----END RSA PRIVATE KEY-----
  ```
- ⚠️ **주의**: 키 전체를 복사해야 하며, BEGIN과 END 줄도 포함해야 합니다!

### 3. Secrets 설정 확인

모든 Secrets가 정상적으로 추가되었는지 확인:
- Settings → Secrets and variables → Actions에서 3개의 Secret이 보여야 합니다

---

## 워크플로우 설명

### 워크플로우 파일 위치
`.github/workflows/deploy.yml`

### 트리거 조건

1. **자동 트리거**: `main` 브랜치에 Push할 때
   ```bash
   git push origin main
   ```

2. **수동 트리거**: GitHub Actions 탭에서 "Run workflow" 버튼 클릭

### 워크플로우 단계

1. **코드 체크아웃**: GitHub에서 최신 코드를 가져옵니다
2. **EC2 SSH 접속**: appleboy/ssh-action을 사용하여 EC2에 접속
3. **코드 업데이트**: `git pull origin main` 실행
4. **컨테이너 재배포**:
   - 기존 컨테이너 중지 (`docker-compose down`)
   - 새 이미지 빌드 및 시작 (`docker-compose up -d --build`)
5. **헬스 체크**: Backend 및 Frontend 서비스 상태 확인
6. **배포 결과 알림**: 성공/실패 여부 출력

---

## 배포 프로세스

### 자동 배포 (권장)

```bash
# 1. 코드 수정
git add .
git commit -m "feature: 새로운 기능 추가"

# 2. main 브랜치에 Push
git push origin main

# 3. GitHub Actions 탭에서 진행 상황 확인
```

### 수동 배포 (서버에서 직접)

```bash
# EC2 인스턴스에 SSH 접속
ssh ec2-user@<EC2_PUBLIC_IP>

# 배포 스크립트 실행
cd /home/ec2-user/FINAL_SERVER
./scripts/deploy.sh
```

---

## 롤백 방법

### 1. 이전 커밋으로 롤백

```bash
# EC2 인스턴스에 접속
ssh ec2-user@<EC2_PUBLIC_IP>

# 최근 커밋 목록 확인
cd /home/ec2-user/FINAL_SERVER
git log --oneline -10

# 롤백 스크립트 실행 (커밋 해시 지정)
./scripts/rollback.sh <commit-hash>

# 예시
./scripts/rollback.sh abc123
```

### 2. 최신 버전으로 복귀

```bash
cd /home/ec2-user/FINAL_SERVER
git checkout main
git pull origin main
sudo docker-compose up -d --build
```

### 3. GitHub에서 이전 커밋으로 되돌리기

```bash
# 로컬에서 이전 커밋으로 되돌리기
git revert <commit-hash>
git push origin main

# 또는 강제로 이전 상태로 되돌리기 (주의!)
git reset --hard <commit-hash>
git push -f origin main
```

---

## 문제 해결

### 1. SSH 연결 실패

**증상**: "Permission denied" 또는 "Connection refused"

**해결방법**:
```bash
# EC2 보안 그룹에서 SSH (22번 포트) 허용 확인
# GitHub Actions IP에서 접근 가능한지 확인

# SSH 키 권한 확인 (EC2에서)
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh

# SSH 서비스 재시작 (필요시)
sudo systemctl restart sshd
```

### 2. Docker 권한 오류

**증상**: "permission denied while trying to connect to the Docker daemon"

**해결방법**:
```bash
# ec2-user를 docker 그룹에 추가
sudo usermod -aG docker ec2-user

# 로그아웃 후 재접속하거나 그룹 새로고침
newgrp docker
```

### 3. .env 파일 누락

**증상**: "Error: .env file not found!"

**해결방법**:
```bash
# EC2 인스턴스에서 .env 파일 확인
cd /home/ec2-user/FINAL_SERVER
ls -la .env

# 없으면 .env.example을 복사하고 수정
cp .env.example .env
nano .env
```

### 4. 빌드 실패

**증상**: Docker 빌드 중 에러

**해결방법**:
```bash
# 로그 확인
sudo docker-compose logs

# 캐시 없이 재빌드
sudo docker-compose build --no-cache
sudo docker-compose up -d

# 디스크 공간 확인
df -h

# 사용하지 않는 이미지 정리
sudo docker system prune -a
```

### 5. 포트 충돌

**증상**: "port is already allocated"

**해결방법**:
```bash
# 실행 중인 컨테이너 확인
sudo docker ps -a

# 모든 컨테이너 중지
sudo docker-compose down

# 포트 사용 확인
sudo netstat -tulpn | grep <port>

# 해당 프로세스 종료 (필요시)
sudo kill <PID>
```

### 6. GitHub Actions 로그 확인

```
GitHub Repository → Actions → 실패한 워크플로우 클릭 → 각 단계별 로그 확인
```

---

## 추가 설정 (선택사항)

### 1. 배포 알림 설정 (Slack, Discord 등)

`.github/workflows/deploy.yml` 파일에 알림 단계 추가:

```yaml
- name: Slack Notification
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 2. 스테이징 환경 추가

`develop` 브랜치를 스테이징 환경으로 사용:

```yaml
on:
  push:
    branches:
      - main       # 프로덕션
      - develop    # 스테이징
```

### 3. 자동 테스트 추가

배포 전 테스트 실행:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest

  deploy:
    needs: test  # 테스트 성공 시에만 배포
    runs-on: ubuntu-latest
    # ... (기존 배포 단계)
```

---

## 보안 권장사항

1. ✅ **SSH 키는 절대 Git에 커밋하지 마세요!**
2. ✅ **.env 파일을 .gitignore에 추가하세요**
3. ✅ **GitHub Secrets에 민감한 정보를 저장하세요**
4. ✅ **EC2 보안 그룹에서 필요한 포트만 허용하세요**
5. ✅ **정기적으로 SSH 키를 교체하세요**
6. ✅ **배포 후 로그를 확인하여 보안 이슈를 점검하세요**

---

## 참고 자료

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [AWS EC2 문서](https://docs.aws.amazon.com/ec2/)

---

## 문의

문제가 발생하거나 도움이 필요하면 GitHub Issues에 등록해주세요.
