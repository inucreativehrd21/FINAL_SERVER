"""
인증 관련 뷰
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from common.utils import success_response, error_response
from .models import User, EmailVerificationCode
from .serializers import (
    UserSerializer,
    SignupSerializer,
    LoginSerializer,
    PasswordChangeSerializer
)
from django.core.mail import send_mail
from django.conf import settings
import requests


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """회원가입"""
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user_data = UserSerializer(user).data
        return success_response(
            data=user_data,
            message="회원가입이 완료되었습니다.",
            status_code=status.HTTP_201_CREATED
        )
    return error_response(
        message="회원가입에 실패했습니다.",
        details=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """로그인"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)

            return success_response(
                data={
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                },
                message="로그인에 성공했습니다."
            )
        else:
            return error_response(
                message="아이디 또는 비밀번호가 올바르지 않습니다.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    return error_response(
        message="로그인 정보를 확인해주세요.",
        details=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """로그아웃"""
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return success_response(message="로그아웃되었습니다.")
    except Exception as e:
        return error_response(
            message="로그아웃에 실패했습니다.",
            details=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    """현재 사용자 정보 조회"""
    serializer = UserSerializer(request.user)
    return success_response(data=serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_info(request):
    """사용자 정보 수정"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return success_response(
            data=serializer.data,
            message="정보가 수정되었습니다."
        )
    return error_response(
        message="정보 수정에 실패했습니다.",
        details=serializer.errors
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """비밀번호 변경"""
    serializer = PasswordChangeSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user

        # 기존 비밀번호 확인
        if not user.check_password(serializer.validated_data['old_password']):
            return error_response(
                message="기존 비밀번호가 올바르지 않습니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 새 비밀번호 설정
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return success_response(message="비밀번호가 변경되었습니다.")

    return error_response(
        message="비밀번호 변경에 실패했습니다.",
        details=serializer.errors
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """회원 탈퇴"""
    user = request.user
    user.is_active = False
    user.save()
    return success_response(message="회원 탈퇴가 완료되었습니다.")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """전체 사용자 목록 조회 (관리자 전용)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return error_response(
            message="관리자 권한이 필요합니다.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # 활성화된 사용자만 조회
    users = User.objects.filter(is_active=True).order_by('-created_at')
    serializer = UserSerializer(users, many=True)
    return success_response(data=serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user_permissions(request, user_id):
    """사용자 권한 수정 (관리자 전용)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return error_response(
            message="관리자 권한이 필요합니다.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response(
            message="사용자를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # 본인의 권한은 수정할 수 없음
    if user.id == request.user.id:
        return error_response(
            message="본인의 권한은 수정할 수 없습니다.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # is_staff, is_superuser 필드만 수정 가능
    if 'is_staff' in request.data:
        user.is_staff = request.data['is_staff']
    if 'is_superuser' in request.data:
        user.is_superuser = request.data['is_superuser']

    user.save()

    return success_response(
        data=UserSerializer(user).data,
        message="권한이 수정되었습니다."
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    """사용자 삭제 (관리자 전용) - 실제로는 비활성화 처리"""
    if not (request.user.is_staff or request.user.is_superuser):
        return error_response(
            message="관리자 권한이 필요합니다.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response(
            message="사용자를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # 본인은 삭제 불가
    if user.id == request.user.id:
        return error_response(
            message="본인은 삭제할 수 없습니다.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 소프트 삭제 (비활성화)
    user.is_active = False
    user.save()

    return success_response(
        message="사용자가 삭제되었습니다."
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_email(request):
    """이메일 인증 코드 전송"""
    email = request.data.get('email')

    if not email:
        return error_response(
            message="이메일을 입력해주세요.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 이미 가입된 이메일인지 확인
    if User.objects.filter(email=email).exists():
        return error_response(
            message="이미 사용 중인 이메일입니다.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 기존 인증 코드 삭제
    EmailVerificationCode.objects.filter(email=email, is_verified=False).delete()

    # 새 인증 코드 생성
    verification = EmailVerificationCode.create_verification_code(email)

    # 이메일 전송 (개발 환경에서는 콘솔에만 출력)
    try:
        send_mail(
            subject='[P[AI]] 이메일 인증 코드',
            message=f'인증 코드: {verification.code}\n\n이 코드는 10분간 유효합니다.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f"[이메일 인증] {email} -> 코드: {verification.code}")
    except Exception as e:
        print(f"[이메일 전송 실패] {e}")
        # 개발 환경에서는 실패해도 계속 진행 (콘솔에 코드 출력됨)

    # 개발 환경에서는 응답에 코드 포함 (실제 운영에서는 제거해야 함)
    response_data = {"expires_in_minutes": 10}
    if settings.DEBUG:
        response_data["verification_code"] = verification.code  # 개발 환경에서만

    return success_response(
        message="인증 코드가 이메일로 전송되었습니다.",
        data=response_data
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_code(request):
    """이메일 인증 코드 확인"""
    email = request.data.get('email')
    code = request.data.get('code')

    print(f"[인증 코드 확인] email: {email}, code: {code}")

    if not email or not code:
        print(f"[인증 실패] 이메일 또는 코드 누락")
        return error_response(
            message="이메일과 인증 코드를 입력해주세요.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 최근 인증 코드 조회
    try:
        verification = EmailVerificationCode.objects.filter(
            email=email,
            code=code,
            is_verified=False
        ).latest('created_at')
        print(f"[인증 코드 발견] {verification.email} - {verification.code} (만료: {verification.expires_at})")
    except EmailVerificationCode.DoesNotExist:
        print(f"[인증 실패] 유효하지 않은 인증 코드. email={email}, code={code}")
        # 디버깅: 해당 이메일의 모든 코드 확인
        all_codes = EmailVerificationCode.objects.filter(email=email).values('code', 'is_verified', 'created_at')
        print(f"[디버깅] {email}의 모든 인증 코드: {list(all_codes)}")
        return error_response(
            message="유효하지 않은 인증 코드입니다.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 만료 확인
    if verification.is_expired():
        print(f"[인증 실패] 코드 만료됨")
        return error_response(
            message="인증 코드가 만료되었습니다. 새로운 코드를 요청해주세요.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 인증 완료 처리
    verification.is_verified = True
    verification.save()
    print(f"[인증 성공] {email} 인증 완료")

    return success_response(
        message="이메일 인증이 완료되었습니다."
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def kakao_login(request):
    """카카오 로그인 - 인가 코드로 토큰 받기"""
    code = request.data.get('code')

    if not code:
        return error_response(
            message="인가 코드가 필요합니다.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 카카오 토큰 요청
        token_url = "https://kauth.kakao.com/oauth/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code
        }

        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()

        if "error" in token_json:
            return error_response(
                message="카카오 토큰 발급에 실패했습니다.",
                details=token_json,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        access_token = token_json.get("access_token")

        # 카카오 사용자 정보 요청
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        if "id" not in user_info:
            return error_response(
                message="카카오 사용자 정보를 가져오는데 실패했습니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 카카오 ID로 사용자 찾기 또는 생성
        kakao_id = str(user_info["id"])
        kakao_account = user_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})

        # username은 kakao_id를 사용
        username = f"kakao_{kakao_id}"

        # 이메일 (선택 동의 항목이므로 없을 수 있음)
        email = kakao_account.get("email", f"{username}@kakao.user")

        # 닉네임
        nickname = profile.get("nickname", f"카카오유저_{kakao_id[:8]}")

        # 기존 사용자 확인
        user = User.objects.filter(username=username).first()

        if not user:
            # 새 사용자 생성
            user = User.objects.create_user(
                username=username,
                email=email,
                nickname=nickname,
                name=nickname,  # 실명은 카카오에서 제공하지 않으므로 nickname 사용
            )
            # 카카오 로그인 사용자는 비밀번호 불필요
            user.set_unusable_password()
            user.save()

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)

        user_data = UserSerializer(user).data

        return success_response(
            data={
                "user": user_data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }
            },
            message="카카오 로그인에 성공했습니다."
        )

    except Exception as e:
        print(f"[카카오 로그인 오류] {str(e)}")
        return error_response(
            message="카카오 로그인 처리 중 오류가 발생했습니다.",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
