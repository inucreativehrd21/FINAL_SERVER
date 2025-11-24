from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.coding_test.models import UserBadge
from apps.coding_test.badge_logic import get_user_metrics_summary


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_statistics(request):
    user = request.user

    try:
        metrics_summary = get_user_metrics_summary(user)
        user_badges = UserBadge.objects.filter(user=user).select_related('badge').order_by('-earned_at')
        badges_data = [
            {
                'id': ub.badge.id,
                'name': ub.badge.name,
                'description': ub.badge.description,
                'icon': ub.badge.icon,
                'badge_type': ub.badge.badge_type,
                'earned_at': ub.earned_at.isoformat()
            }
            for ub in user_badges
        ]

        return Response({
            'success': True,
            'data': {
                'metrics': {
                    'avg_syntax_errors': round(metrics_summary['avg_syntax_errors'], 2),
                    'avg_test_pass_rate': round(metrics_summary['avg_test_pass_rate'], 2),
                    'avg_code_complexity': round(metrics_summary['avg_code_complexity'], 2),
                    'avg_code_quality_score': round(metrics_summary['avg_code_quality_score'], 2),
                    'avg_algorithm_pattern_match': round(metrics_summary['avg_algorithm_pattern_match'], 2),
                    'avg_pep8_violations': round(metrics_summary['avg_pep8_violations'], 2),
                    'total_problems': metrics_summary['total_problems']
                },
                'badges': badges_data,
                'total_badges': len(badges_data)
            }
        })

    except Exception as e:
        print(f'Failed to get user statistics: {str(e)}')
        return Response({
            'success': False,
            'message': f'Statistics retrieval failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_badges(request):
    user = request.user

    try:
        user_badges = UserBadge.objects.filter(user=user).select_related('badge').order_by('-earned_at')

        badges_data = [
            {
                'id': ub.badge.id,
                'name': ub.badge.name,
                'description': ub.badge.description,
                'icon': ub.badge.icon,
                'badge_type': ub.badge.badge_type,
                'earned_at': ub.earned_at.isoformat()
            }
            for ub in user_badges
        ]

        return Response({
            'success': True,
            'data': {
                'badges': badges_data,
                'total': len(badges_data)
            }
        })

    except Exception as e:
        print(f'Failed to get user badges: {str(e)}')
        return Response({
            'success': False,
            'message': f'Badge retrieval failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
