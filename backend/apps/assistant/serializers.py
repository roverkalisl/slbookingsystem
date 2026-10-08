from rest_framework import serializers


class ConversationMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=('user', 'assistant'))
    content = serializers.CharField(max_length=1200, trim_whitespace=True)


class AssistantChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1200, trim_whitespace=True)
    language = serializers.ChoiceField(choices=('en', 'si'), default='en')
    history = ConversationMessageSerializer(many=True, required=False, max_length=8)

    def validate_history(self, value):
        return value[-8:]
