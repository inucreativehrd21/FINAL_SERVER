"""
코딩 테스트 Serializers
"""
from rest_framework import serializers
from .models import TestCaseProposal, SolutionProposal


class TestCaseProposalSerializer(serializers.ModelSerializer):
    """테스트 케이스 제안 Serializer"""
    proposed_by_username = serializers.CharField(source='proposed_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TestCaseProposal
        fields = [
            'id',
            'problem_id',
            'proposed_by',
            'proposed_by_username',
            'input_data',
            'expected_output',
            'description',
            'status',
            'status_display',
            'reviewed_by',
            'reviewed_by_username',
            'review_comment',
            'created_at',
            'reviewed_at',
        ]
        read_only_fields = ['id', 'proposed_by', 'reviewed_by', 'reviewed_at', 'created_at']


class TestCaseProposalCreateSerializer(serializers.ModelSerializer):
    """테스트 케이스 제안 생성 Serializer"""

    class Meta:
        model = TestCaseProposal
        fields = ['problem_id', 'input_data', 'expected_output', 'description']

    def validate_input_data(self, value):
        """입력 데이터 검증"""
        if not value.strip():
            raise serializers.ValidationError("입력 데이터는 비어있을 수 없습니다.")
        return value

    def validate_expected_output(self, value):
        """예상 출력 검증"""
        if not value.strip():
            raise serializers.ValidationError("예상 출력은 비어있을 수 없습니다.")
        return value


class SolutionProposalSerializer(serializers.ModelSerializer):
    """솔루션 제안 Serializer"""
    proposed_by_username = serializers.CharField(source='proposed_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SolutionProposal
        fields = [
            'id',
            'problem_id',
            'proposed_by',
            'proposed_by_username',
            'solution_code',
            'language',
            'description',
            'is_reference',
            'status',
            'status_display',
            'reviewed_by',
            'reviewed_by_username',
            'review_comment',
            'created_at',
            'reviewed_at',
        ]
        read_only_fields = ['id', 'proposed_by', 'reviewed_by', 'reviewed_at', 'created_at']


class SolutionProposalCreateSerializer(serializers.ModelSerializer):
    """솔루션 제안 생성 Serializer"""

    class Meta:
        model = SolutionProposal
        fields = ['problem_id', 'solution_code', 'language', 'description', 'is_reference']

    def validate_solution_code(self, value):
        """솔루션 코드 검증"""
        if not value.strip():
            raise serializers.ValidationError("솔루션 코드는 비어있을 수 없습니다.")
        return value
