from django.db import models
from authentication.models import Passenger
from booking.models import Booking
from django.utils import timezone
import uuid
# Create your models here.

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('mobile_wallet', 'Mobile Wallet'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='payments')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, unique=True)
    is_successful = models.BooleanField(default=False)
    
    #We can include the amount_remaining field for any advance payment system, so it can later be given to the driver on the bus.
    
    def __str__(self):
        return f"Payment by {self.passenger.user.username} for {self.booking.trip.vehicle.registration_number}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)