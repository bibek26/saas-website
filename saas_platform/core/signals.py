# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task, Notification

@receiver(post_save, sender=Task)
def notify_new_task(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.assigned_to,
            message=f"New task assigned: {instance.title} due on {instance.due_date}"
        )