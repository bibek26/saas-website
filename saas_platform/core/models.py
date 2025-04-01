# Create your models here.

from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from datetime import date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)
    schema_name = models.CharField(max_length=63, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    auto_create_schema = True
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.schema_name = f'tenant_{self.name.lower().replace(" ", "_")}'  # Generate a valid schema_name
        if self.schema_name == 'public':
            raise ValueError("Schema name 'public' is reserved.")
        super().save(*args, **kwargs)
        
class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, first_name, last_name, phone_number, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        user.set_password(password)  # Hash the password
        user.save()
        return user

    def create_superuser(self, email, username, first_name, last_name, phone_number, password):
        user = self.create_user(
            email, username, first_name, last_name, phone_number, password
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    tenant_schema = models.CharField(max_length=63, null=True, blank=True)
    email = models.EmailField(unique=True)  # Email as unique identifier
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=255) 
    last_name = models.CharField(max_length=255) 
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)  # For account activation
    is_staff = models.BooleanField(default=False)  # For admin access
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('user', 'User')
    ], default='user')
    objects = CustomUserManager()  # Assign the custom manager

    USERNAME_FIELD = 'username'  # Use username for login instead of username
    REQUIRED_FIELDS = ['email', 'first_name','last_name','phone_number']  # Required when creating a superuser

    def __str__(self):
        return self.username
    
# Domain Model
class Domain(DomainMixin):
    pass

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'Message'),
        ('project', 'Project'),
        ('leave', 'Leave')
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='message')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)
    
class Subscription(models.Model):
    tenant = models.OneToOneField('core.Tenant', on_delete=models.CASCADE)
    plan = models.CharField(max_length=50, choices=[('basic', 'Basic'), ('pro', 'Pro')])
    start_date = models.DateField()
    end_date = models.DateField()
    
    def save(self, *args, **kwargs):
        if not self.start_date:
            self.start_date = date.today()
        if not self.end_date:
            duration = 1 if self.plan == 'basic' else 6  # 1 month for Basic, 6 for Pro
            self.end_date = self.start_date + relativedelta(months=duration)
        super().save(*args, **kwargs)
    
class PaymentHistory(models.Model):
    tenant = models.ForeignKey('core.Tenant', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('success', 'Success'), ('failed', 'Failed')])

class BillingInfo(models.Model):
    tenant = models.OneToOneField("core.Tenant", on_delete=models.CASCADE)
    card_number = models.CharField(max_length=16)
    expiry_date = models.CharField(max_length=5)  # MM/YY
    cvv = models.CharField(max_length=3)
    
class Analytics(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    date = models.DateField()
    user_count = models.IntegerField()
    api_calls = models.IntegerField(default=0)
    
class TenantCustomization(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    primary_color = models.CharField(max_length=7, default='#007bff')  # Hex code
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    
# core/models.py
class ActivityLog(models.Model):
    # tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now)
    
    
class HelpArticle(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

class Ticket(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    
class Task(models.Model):
    STATUS_CHOICES = [
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Help Needed', 'Help Needed'),
    ]

    title = models.CharField(max_length=100)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')])
    due_date = models.DateField()
    project = models.ForeignKey('Project', on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Assigned')
    progress_percentage = models.IntegerField(default=0)
    comments = models.TextField(blank=True)
    # attachments = models.FileField(upload_to='task_attachments/', blank=True)

    def __str__(self):
        return self.title
    def get_status_choices(self):
        return self.STATUS_CHOICES
class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.title} - {self.file.name}"
    
class Project(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(CustomUser, related_name='projects')
    deadline = models.DateField()

    def __str__(self):
        return self.name
    
    def completion_percentage(self):
        tasks = self.task_set.all()
        if not tasks.exists():
            return 0
        completed_tasks = tasks.filter(status='Completed').count()
        total_tasks = tasks.count()
        return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    
class Activity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    description = models.TextField(default='It is a project')
    timestamp = models.DateTimeField(default=timezone.now)
    
class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"From {self.sender} to {self.recipient} at {self.timestamp}"
    
class LeaveRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending', choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Denied', 'Denied')])
    
    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date}"
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    leave_balance = models.IntegerField(default=20)
    