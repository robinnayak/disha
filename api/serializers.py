from rest_framework import serializers
from api.models import SupportRequest,Feedback

class SupportRequestSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = SupportRequest
        fields = ['id', 'subject', 'message', 'image', 'username', 'email', 'status','created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Get the user from the context passed in the view
        user = self.context['user']
        validated_data['user'] = user
        
        # Call the parent create method
        return super().create(validated_data)
    
class FeedbackSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    class Meta:
        model = Feedback
        fields = ['id', 'feedback_type', 'comments', 'track_options', 'created_at', 'updated_at', 'username','email']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    # Override create method to associate feedback with the authenticated user
    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        return super().create(validated_data)