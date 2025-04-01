from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Tenant, Domain, Subscription, BillingInfo,Project,TaskAttachment, TenantCustomization,Ticket,Task,LeaveRequest,Message
from django_tenants.utils import schema_context, get_public_schema_name
from django.core.management import call_command
from django.core.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth.forms import PasswordChangeForm

class CustomUserCreationForm(UserCreationForm):
    company_name = forms.CharField(max_length=100, required=True)
    domain = forms.CharField(max_length=100, required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    # plan = forms.ChoiceField(choices=[('basic', 'Basic'), ('pro', 'Pro')], required=True)
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data['username']
        # Check in the current schema (will be tenant schema after tenant creation)
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        with schema_context(get_public_schema_name()):  # 'public'
            if Domain.objects.filter(domain=domain).exists():
                raise ValidationError("This domain is already registered.")
        return domain

    def clean_company_name(self):
        company_name = self.cleaned_data['company_name']
        with schema_context(get_public_schema_name()):  # 'public'
            if Tenant.objects.filter(name=company_name).exists():
                raise ValidationError("This company name is already in use.")
        return company_name
    
    def save(self, commit=True):
        print("Starting save process")
        with schema_context('public'):
            print("In public schema")
            # Create the tenant first
            company_name = self.cleaned_data['company_name']
            domain = self.cleaned_data['domain']
            tenant = Tenant.objects.create(name=company_name, domain=domain)
            Domain.objects.create(domain=domain, tenant=tenant, is_primary=True)

            # Create subscription
            Subscription.objects.create(
                tenant=tenant,
                plan='basic',
                start_date=date.today(),
                end_date=date.today() + relativedelta(months=1)  # 1-month subscription
            )
        # Apply migrations to new tenant schema
        call_command('migrate_schemas', schema_name=tenant.schema_name, interactive=False)
        print(f"Migrated schema: {tenant.schema_name}")
        
        with schema_context(tenant.schema_name):
            print(f"Switched to schema: {tenant.schema_name}")
            # Create the user and link it to the tenant
            user = super().save(commit=False)
            user.tenant_schema = tenant.schema_name
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.phone_number = self.cleaned_data['phone_number']
            user.role = 'admin'
            user.is_staff = True
            print(f"User prepared: {user.username}, tenant_schema: {user.tenant_schema}")
            if commit:
                user.save()
            return user
        

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        
class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta:
        model = CustomUser
        
class TenantProfileForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'logo']
        
class UserManagementForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'password']
        widgets = {'password': forms.PasswordInput()}
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'phone_number': 'Phone Number',
            'role': 'Role',
            'password': 'Password',
        }
        help_texts = {
            'username': 'Required. 150 characters or fewer.',
            'email': 'Enter a valid email address.',
            'phone_number': 'e.g., +1234567890',
        }
        
class BillingInfoForm(forms.ModelForm):
    class Meta:
        model = BillingInfo
        fields = ['card_number', 'expiry_date', 'cvv']
        
class TenantCustomizationForm(forms.ModelForm):
    class Meta:
        model = TenantCustomization
        fields = ['primary_color', 'secondary_color']
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
        }
        
class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description']

class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']
        
class TaskProgressForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['progress_percentage', 'comments']
        widgets = {
            'progress_percentage': forms.NumberInput(attrs={'min': 0, 'max': 100}),
            'comments': forms.Textarea(attrs={'rows': 3}),
        }
        # def __init__(self, *args, **kwargs):
        #     super().__init__(*args, **kwargs)
        #     self.fields['attachments'].required = False
        
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        
        
class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.all()  # Or filter by tenant/user if needed

    class Meta:
        model = Task
        fields = ['title', 'project', 'priority', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
        }
        
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        
class ProjectForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Project
        fields = ['name', 'deadline', 'members']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }