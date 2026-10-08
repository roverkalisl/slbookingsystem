from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AssistantChatSerializer
from .services import (
    AssistantConfigurationError,
    AssistantProviderError,
    generate_assistant_reply,
)
from .throttles import AssistantRateThrottle


class AssistantChatView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AssistantRateThrottle]
    throttle_scope = 'ai_assistant'

    def post(self, request):
        serializer = AssistantChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = generate_assistant_reply(
                message=serializer.validated_data['message'],
                history=serializer.validated_data.get('history', []),
                language=serializer.validated_data['language'],
            )
        except AssistantConfigurationError:
            return Response(
                {'detail': 'The booking assistant is not configured yet.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AssistantProviderError:
            return Response(
                {'detail': 'The booking assistant is temporarily unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result, status=status.HTTP_200_OK)
