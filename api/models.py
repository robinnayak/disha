from django.db import models

# Create your models here.
from authentication.models import CustomUser
from cloudinary.models import CloudinaryField
class SupportRequest(models.Model):
    STATUS_CHOICES = [
        ('resolved', 'Resolved'),
        ('not_resolved', 'Not Resolved'),
        ('pending', 'Pending'),
    ]
    
    subject = models.CharField(max_length=255)
    message = models.TextField()
    image = CloudinaryField('support_requests', blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='not_resolved')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject
    

class Feedback(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('acknowledgment', 'Acknowledgment'),  # Previously "positive"
        ('improvement', 'Improvement'),        # Previously "negative"
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Assuming user authentication
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    comments = models.TextField()
    track_options = models.BooleanField(default=False) # Additional suggestions or actions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feedback from {self.user.username} - {self.feedback_type}"

