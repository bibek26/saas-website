from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,logout, login
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm, UserProfileForm,CustomPasswordChangeForm,TaskStatusForm, TicketForm,MessageForm, TenantProfileForm, UserManagementForm,BillingInfoForm,TenantCustomizationForm,TaskProgressForm,LeaveRequestForm,TaskForm,ProjectForm
from django.contrib import messages 
from django_tenants.utils import schema_context, get_public_schema_name
from core.models import Domain, CustomUser, Tenant, Notification,Task, Subscription,HelpArticle,TaskAttachment, BillingInfo,Ticket, PaymentHistory, Analytics,TenantCustomization, ActivityLog,Project,Activity,Message,LeaveRequest,UserProfile
from django.contrib.auth.decorators import login_required,user_passes_test
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils import timezone
import csv

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            company_name = form.cleaned_data['company_name']  # Assumes form has this field
            tenant_schema = company_name.lower().replace(' ', '_')  # e.g., "acme"
            domain_name = f"{tenant_schema}.local"
            
            
            # with schema_context(tenant_schema):
            #     user = form.save(commit=False)  # Don't save to DB yet
            #     user.tenant_schema = tenant_schema  # Set if your User model has this field
            #     # user.save()
            #     user.role = 'admin'
            #     user.is_staff = True
            #     user.save()
            #     login(request, user)
            messages.success(request, f"Account created successfully for {user.username}!")
            # return redirect('core:tenant_home')
            print(f"entering to {domain_name}")
            return redirect(f"http://{domain_name}:8000/login")
        else:
            # Display form errors as messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})


@login_required
def admin_home(request):
    if not request.user.is_superuser:
        return redirect('core:tenant_home')
    context = {'user': request.user}
    if request.user.is_superuser:
        with schema_context('public'):
            tenants = Tenant.objects.all()
            print(f"Tenants found: {list(tenants)}")
            context['tenants'] = tenants
    return render(request, 'core/admin_home.html', context)


@login_required
def tenant_home(request):
    if request.user.is_superuser:
        return redirect('core:admin_home')
    if request.user.role in ['admin', 'manager']:
        context = {'user': request.user}
        with schema_context('public'):
            tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
            customization, _ = TenantCustomization.objects.get_or_create(tenant=tenant)
            context['tenant'] = tenant
            context['customization'] = customization
        with schema_context(request.user.tenant_schema):
            notifications = Notification.objects.filter(user=request.user, is_read=False)
            activities = ActivityLog.objects.order_by('-timestamp')[:6]
            tasks = Task.objects.all().prefetch_related('attachments').order_by('-id')
            # Pagination for tasks
            paginator = Paginator(tasks, 10)  # 10 tasks per page
            page_number = request.GET.get('page')  # Get the page number from query params
            page_obj = paginator.get_page(page_number)
            
            projects = Project.objects.filter(members=request.user).prefetch_related('members')
            projects_paginator = Paginator(projects, 10)
            projects_page_number = request.GET.get('projects_page')
            projects_page_obj = projects_paginator.get_page(projects_page_number)
            metrics = {
                'total_tasks': Task.objects.count(),
                'completed_tasks': Task.objects.filter(status='Completed').count(),
                'overdue_tasks': Task.objects.filter(due_date__lt=timezone.now()).exclude(status='Completed').count(),
                'active_projects': Project.objects.filter(deadline__gte=timezone.now()).count(),
            }
            workload = CustomUser.objects.exclude(role='admin').annotate(
                task_count=Count('task'), 
                overdue_count=Count('task', filter=Q(task__due_date__lt=timezone.now()) & ~Q(task__status='Completed'))
            )
            context['workload'] = workload
            context['metrics'] = metrics
            context['projects_page_obj'] = projects_page_obj
            context['page_obj'] = page_obj
            context['notifications'] = notifications
            context['activities'] = activities
            context['is_admin'] = request.user.role == 'admin'
        return render(request, 'core/tenant_home.html', context)
    else:
        tasks = Task.objects.filter(assigned_to=request.user).order_by(request.GET.get('sort', 'due_date'))
        projects = Project.objects.filter(members=request.user)
        activities = Activity.objects.filter(project__members=request.user).order_by('-timestamp')[:6]
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        metrics = {
            'tasks_completed': Task.objects.filter(assigned_to=request.user, status='Completed').count(),
            'projects_in_progress': projects.count(),
            'upcoming_deadlines': Task.objects.filter(assigned_to=request.user, due_date__gte=timezone.now()).count()
        }
        todo_list = Task.objects.filter(assigned_to=request.user, due_date=timezone.now().date())
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return render(request, 'core/user_home.html', {
            'tasks': tasks, 'projects': projects, 'activities': activities, 
            'notifications': notifications, 'metrics': metrics, 'todo_list': todo_list, 
            'leave_balance': profile.leave_balance
        })
        

@login_required
def home(request):
    context = {'user': request.user}
    if request.user.is_superuser:
        with schema_context('public'):
            tenants = Tenant.objects.all()
            # print(f"Tenants found: {list(tenants)}")
            context['tenants'] = tenants
    else:
        with schema_context('public'):
            tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
            context['tenant'] = tenant
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        context['notifications'] = notifications
    return render(request, 'core/home.html', context)

def custom_logout(request):
    logout(request)  # Clear the user’s session
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:tenant_home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            domain = request.get_host().split(':')[0]  # Remove port if present
            
            tenant_schema = get_public_schema_name()  # Default to 'public'
            with schema_context('public'):
                try:
                    domain_obj = Domain.objects.get(domain=domain)
                    tenant_schema = domain_obj.tenant.schema_name

                except Domain.DoesNotExist:
                    messages.error(request, f"Domain {domain} is not registered.")
                    return render(request, 'core/login.html', {'form': form})
                
                
            # Authenticate in the correct schema
            with schema_context(tenant_schema):
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    if user.tenant_schema != tenant_schema:
                        correct_domain = Domain.objects.get(tenant__schema_name=user.tenant_schema).domain
                        messages.error(request, f"User {username} belongs to {correct_domain}, not {domain}.")
                        return render(request, 'core/login.html', {'form': form})
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.username}!")
                    return redirect('core:admin_home')
                else:
                    messages.error(request, "Invalid username or password.")
        else:
            # Log and display form errors
            print(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
            # messages.error(request, "Please correct the errors below.")
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def tenant_profile_edit(request):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
        customization, _ = TenantCustomization.objects.get_or_create(tenant=tenant)
        print(f"Tenant logo: {tenant.logo}, URL: {tenant.logo.url if tenant.logo else 'None'}")
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        tenant_form = TenantProfileForm(request.POST, request.FILES, instance=tenant)
        custom_form = TenantCustomizationForm(request.POST, instance=customization)
        if user_form.is_valid() and tenant_form.is_valid():
            user_form.save()
            tenant_form.save()
            custom_form.save()
            messages.success(request, "Profile and customization updated successfully!")
            return redirect('core:tenant_home')
    else:
        user_form = UserProfileForm(instance=request.user)
        tenant_form = TenantProfileForm(instance=tenant)
        custom_form = TenantCustomizationForm(instance=customization)
    return render(request, 'core/tenant_profile_edit.html', {
        'user_form': user_form,
        'tenant_form': tenant_form,
        'custom_form': custom_form,
    })
    
@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully.')
            return redirect('core:tenant_profile_edit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('core:home')
    with schema_context('public'):
        tenants = Tenant.objects.all()
        tenant_data = []
        for tenant in tenants:
            with schema_context(tenant.schema_name):
                user_count = CustomUser.objects.count()
            subscription = Subscription.objects.filter(tenant=tenant).first()
            tenant_data.append({'tenant': tenant, 'user_count': user_count, 'subscription': subscription})
    return render(request, 'core/admin_dashboard.html', {'tenant_data': tenant_data})


@login_required
def subscription_billing(request):
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
        subscription = Subscription.objects.get(tenant=tenant)
        payment_history = PaymentHistory.objects.filter(tenant=tenant)
        billing_info, _ = BillingInfo.objects.get_or_create(tenant=tenant)
    return render(request, 'core/subscription_billing.html', {
        'subscription': subscription,
        'payment_history': payment_history,
        'billing_info': billing_info,
        'user_count': CustomUser.objects.count()
    })

@login_required
def update_billing(request):
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
        try:
            billing_info = BillingInfo.objects.get(tenant=tenant)
            created = False
        except BillingInfo.DoesNotExist:
            billing_info = BillingInfo(tenant=tenant, card_number='', expiry_date='', cvv='')
            billing_info.save()
            created = True
        except BillingInfo.MultipleObjectsReturned:
            # Handle multiple records: use the first non-empty one or clean up DB
            billing_info = BillingInfo.objects.filter(tenant=tenant).exclude(card_number='').first() or BillingInfo.objects.filter(tenant=tenant).first()
            created = False
        print(f"Tenant: {tenant.schema_name}, Created: {created}, Billing Info: {billing_info.card_number}, {billing_info.expiry_date}, {billing_info.cvv}")

    if request.method == 'POST':
        form = BillingInfoForm(request.POST, instance=billing_info)
        if form.is_valid():
            with schema_context('public'):
                form.save()
            print(f"Updated Billing: {billing_info.card_number}, {billing_info.expiry_date}, {billing_info.cvv}")
            return redirect('core:subscription_billing')
        else:
            print(f"Form errors: {form.errors}")    
    else:
        form = BillingInfoForm(instance=billing_info)
    return render(request, 'core/update_billing.html', {'form': form})

@login_required
def manage_subscription(request):
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
        subscription, created = Subscription.objects.get_or_create(
            tenant=tenant,
            defaults={'plan': 'basic', 'start_date': date.today(), 'end_date': date.today() + relativedelta(months=1)}
        )
        billing_info, _ = BillingInfo.objects.get_or_create(
            tenant=tenant,
            defaults={'card_number': '', 'expiry_date': '', 'cvv': ''}  # Default empty values
        )
        # Debug print to verify data
        print(f"Billing Info: {billing_info.card_number}, {billing_info.expiry_date}, {billing_info.cvv}")

    if request.method == 'POST':
        if 'plan' in request.POST and 'confirm' not in request.POST:
            # Step 1: Plan selected, show billing details
            selected_plan = request.POST.get('plan')
            plan_duration = '1 Month' if selected_plan == 'basic' else '6 Months'
            plan_cost = '10.00' if selected_plan == 'basic' else '50.00'
            return render(request, 'core/manage_subscription.html', {
                'subscription': subscription,
                'billing_info': billing_info,
                'selected_plan': selected_plan,
                'plan_duration': plan_duration,
                'plan_cost': plan_cost
            })
        elif 'confirm' in request.POST:
            # Step 2: Billing confirmed, update subscription
            plan = request.POST.get('plan')
            duration = 1 if plan == 'basic' else 6
            subscription.plan = plan
            subscription.start_date = date.today()
            subscription.end_date = date.today() + relativedelta(months=duration)
            subscription.save()
            # Simulate payment
            PaymentHistory.objects.create(tenant=tenant, amount=10.00 if plan == 'basic' else 50.00, status='success')
            return redirect('core:subscription_billing')

    return render(request, 'core/manage_subscription.html', {
        'subscription': subscription,
        'billing_info': billing_info
    })


@login_required
def user_management(request):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context(request.user.tenant_schema):
        users = CustomUser.objects.exclude(role='admin')
    return render(request, 'core/user_management.html', {'users': users})

@login_required
def add_user(request):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            with schema_context(request.user.tenant_schema):
                user = form.save(commit=False)
                user.tenant_schema = request.user.tenant_schema
                user.password = make_password(form.cleaned_data['password'])
                user.save()
                # ActivityLog.objects.create(tenant=Tenant.objects.get(schema_name=request.user.tenant_schema), action=f"User {user.username} added.")
                ActivityLog.objects.create(action=f"User {user.username} added.")
            return redirect('core:user_management')
    else:
        form = UserManagementForm()
    return render(request, 'core/add_user.html', {'form': form})

@login_required
def edit_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context(request.user.tenant_schema):
        user = get_object_or_404(CustomUser, id=user_id)
        if request.method == 'POST':
            form = UserManagementForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                return redirect('core:user_management')
        else:
            form = UserManagementForm(instance=user)
    return render(request, 'core/edit_user.html', {'form': form, 'user': user})

@login_required
def delete_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context(request.user.tenant_schema):
        user = get_object_or_404(CustomUser, id=user_id)
        user.delete()
    return redirect('core:user_management')

@login_required
def deactivate_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context(request.user.tenant_schema):
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = False
        user.save()
        ActivityLog.objects.create(action=f"User {user.username} was deactivated")
    return redirect('core:user_management')

@login_required
def activate_user(request, user_id):
    if request.user.role != 'admin':  # Assuming 'role' is a field on your user model
        messages.error(request, 'Only admins can activate users.')
        return redirect('core:user_management')
    with schema_context(request.user.tenant_schema):  # Remove if not using multi-tenancy
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = True
        user.save()
        messages.success(request, f'User {user.username} activated.')
        ActivityLog.objects.create(action=f"User {user.username} was activated")
    return redirect('core:user_management')

@login_required
def analytics(request):
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
    with schema_context(request.user.tenant_schema):
        analytics_data = Analytics.objects.filter(tenant=tenant)
        date_from = request.GET.get('date_from')
        if date_from:
            analytics_data = analytics_data.filter(date__gte=date_from)
    return render(request, 'core/analytics.html', {'analytics_data': analytics_data})

@login_required
def download_report(request):
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
    with schema_context(request.user.tenant_schema):
        analytics_data = Analytics.objects.filter(tenant=tenant)
        date_from = request.GET.get('date_from')
        if date_from:
            analytics_data = analytics_data.filter(date__gte=date_from)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{tenant.schema_name}_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'User Count', 'API Calls'])
    for data in analytics_data:
        writer.writerow([data.date, data.user_count, data.api_calls])
    return response

@login_required
def export_users(request):
    with schema_context(request.user.tenant_schema):
        users = CustomUser.objects.all()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Role'])
        for user in users:
            writer.writerow([user.username, user.email, user.first_name, user.last_name, user.role])
        return response

# core/views.py
@login_required
def customization(request):
    if request.user.role != 'admin':
        return redirect('core:tenant_home')
    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
        customization, created = TenantCustomization.objects.get_or_create(tenant=tenant)

    
    if request.method == 'POST':
        tenant_form = TenantProfileForm(request.POST, request.FILES, instance=tenant)
        custom_form = TenantCustomizationForm(request.POST, instance=customization)
        if tenant_form.is_valid() and custom_form.is_valid():
            tenant_form.save()
            custom_instance = custom_form.save(commit=False)
            custom_instance.save()
            messages.success(request, "Customization updated successfully!")
            return redirect('core:tenant_home')
        else:
            messages.error(request, "Failed to save customization. Check the form for errors.")
    else:
        tenant_form = TenantProfileForm(instance=tenant)
        custom_form = TenantCustomizationForm(instance=customization)
    
    return render(request, 'core/customization.html', {
        'tenant_form': tenant_form,
        'custom_form': custom_form,
    })
    
@login_required
def help_page(request):
    articles = HelpArticle.objects.all()
    return render(request, 'core/help.html', {'articles': articles})

@login_required
def support_tickets(request):
    with schema_context(request.user.tenant_schema):
        tickets = Ticket.objects.filter(user=request.user)
    return render(request, 'core/support_tickets.html', {'tickets': tickets})

@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, 'Ticket created.')
            return redirect('core:support_tickets')
    else:
        form = TicketForm()
    return render(request, 'core/create_ticket.html', {'form': form})

@login_required
def user_home(request):
    print(f"View called: user_home for user: {request.user.username}")
    print(f"Entering user_home for user: {request.user.username}, Schema: {request.user.tenant_schema}")
    tasks = Task.objects.filter(assigned_to=request.user).order_by(request.GET.get('sort', 'due_date'))
    projects = Project.objects.filter(members=request.user)
    activities = Activity.objects.filter(project__members=request.user).order_by('-timestamp')[:10]
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    
    metrics = {
        'tasks_completed': Task.objects.filter(assigned_to=request.user, status='Completed').count(),
        'projects_in_progress': Project.objects.filter(members=request.user).count(),
        'upcoming_deadlines': Task.objects.filter(assigned_to=request.user, due_date__gte=timezone.now()).count()
    }
    todo_list = Task.objects.filter(
            assigned_to=request.user,
            due_date=timezone.now().date(),
            status__in=['Assigned', 'In Progress', 'Help Needed']  # Exclude 'Completed'
        )
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/user_home.html', {'tasks': tasks, 'projects':projects,'activities':activities, 'notifications':notifications, 'metrics':metrics, 'todo_list': todo_list, 'leave_balance': profile.leave_balance})

@login_required
@require_POST
def mark_notification_read(request):
    notification_id = request.POST.get('notification_id')
    with schema_context(request.user.tenant_schema):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
        
@login_required
@require_POST
def mark_all_notifications_read(request):
    with schema_context(request.user.tenant_schema):
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        count = notifications.count()
        notifications.update(is_read=True)  # Mark all as read
        return JsonResponse({'success': True, 'marked_count': count})
    
@login_required
def update_task_status(request, task_id):
    with schema_context(request.user.tenant_schema):
        task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
        if request.method == 'POST':
            form = TaskStatusForm(request.POST, instance=task)
            if form.is_valid():
                form.save()
                # Return JSON response for AJAX
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'status': task.status
                    })
                return redirect('core:user_home')  # Fallback for non-AJAX requests
        else:
            form = TaskStatusForm(instance=task)
        return render(request, 'core/update_task_status.html', {'form': form, 'task': task})


@login_required
def update_task_progress(request, task_id):
    with schema_context(request.user.tenant_schema):
        task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
        if request.method == 'POST':
            form = TaskProgressForm(request.POST, request.FILES, instance=task)
            if form.is_valid():
                task = form.save()
                # Handle multiple file uploads
                if 'attachments' in request.FILES:
                    for file in request.FILES.getlist('attachments'):
                        TaskAttachment.objects.create(task=task, file=file)
            
                messages.success(request, "Task progress updated successfully.")
                return redirect('core:user_home')
        else:
            form = TaskProgressForm(instance=task)
        return render(request, 'core/update_task_progress.html', {'form': form, 'task': task})

@login_required
@require_POST
def delete_task_attachment(request, attachment_id):
    attachment = get_object_or_404(TaskAttachment, id=attachment_id, task__assigned_to=request.user)
    attachment.file.delete()  # Delete file from storage
    attachment.delete()  # Delete record
    return JsonResponse({'success': True})

@login_required
def send_message(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        content = request.POST.get('content')
        recipient = get_object_or_404(CustomUser, id=recipient_id)
        Message.objects.create(sender=request.user, recipient=recipient, content=content)
        return redirect('core:user_home')
    users = CustomUser.objects.exclude(id=request.user.id)
    messages = Message.objects.filter(recipient=request.user) | Message.objects.filter(sender=request.user)
    return render(request, 'core/messages.html', {'users': users, 'messages': messages})

@login_required
def send_reply(request, message_id):
    original_message = get_object_or_404(Message, id=message_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            # Create a new message replying to the original sender
            Message.objects.create(
                sender=request.user,
                recipient=original_message.sender,
                content=content
            )
            # Get the referring page URL or default to user_messages
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
    return redirect('core:user_messages', user_id=original_message.sender.id)


@login_required
def request_leave(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    leave_balance = profile.leave_balance  # Current leave balance

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = request.user
            
            # Calculate the number of days requested
            start_date = leave.start_date
            end_date = leave.end_date
            requested_days = (end_date - start_date).days + 1  # Inclusive of start and end dates
            
            # Validate against leave balance
            if requested_days > leave_balance:
                messages.error(request, f"You only have {leave_balance} days left. Please adjust your leave request accordingly.")
                return render(request, 'core/request_leave.html', {'form': form, 'requests': LeaveRequest.objects.filter(user=request.user)})
            
            # Save the request (still pending, no deduction yet)
            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('core:user_home')
    else:
        form = LeaveRequestForm()
    
    requests = LeaveRequest.objects.filter(user=request.user)
    return render(request, 'core/request_leave.html', {'form': form, 'requests': requests, 'leave_balance': leave_balance})

# Custom decorator to restrict access to admins
def admin_required(view_func):
    decorated_view_func = login_required(user_passes_test(lambda u: u.role in ['admin', 'manager'])(view_func))
    return decorated_view_func

# View to list all users
@admin_required
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, 'ad/user_list.html', {'users': users})



@admin_required
def assign_task(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    tenant_schema = request.user.tenant_schema
    with schema_context(tenant_schema):
        if request.method == 'POST':
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.assigned_to = user
                task.save()
                project = task.project
                messages.success(request, f"Task '{task.title}' assigned and for {user.username} in {project.name}.")
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'task': {
                            'title': task.title,
                            'priority': task.priority,
                            'due_date': task.due_date.isoformat(),
                            'status': task.status,
                        }
                    })
                return redirect('core:user_management')
            else:
                return render(request, 'ad/assign_task.html', {
                    'task_form': task_form,
                    'user': user
                })
        else:
            task_form = TaskForm()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Return form HTML for AJAX GET request
            form_html = render_to_string('core/task_form.html', {
                'task_form': task_form,
                'user': user
            }, request=request)
            return JsonResponse({'form_html': form_html})
        return render(request, 'ad/assign_task.html', {
            'task_form': task_form,
            'user': user
        })



# View to see messages sent by a specific user
# @admin_required
# def view_user_messages(request, user_id):
#     user = get_object_or_404(CustomUser, id=user_id)
#     messages = Message.objects.filter(sender=user).order_by('-timestamp')
#     return render(request, 'ad/user_messages.html', {'user': user, 'messages': messages})

@login_required
def view_user_messages(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.method == 'GET':
            # Fetch all messages between admin and user
            last_message_id = request.GET.get('last_message_id', 0) 
            messages = Message.objects.filter(
                models.Q(sender=request.user, recipient=user) | 
                models.Q(sender=user, recipient=request.user)
            ).filter(id__gt=last_message_id).order_by('timestamp')  # Order by timestamp for chronological order
            messages_html = render_to_string('core/messages.html', {'messages': messages, 'user': user, 'current_user': request.user}, request=request)
            return JsonResponse({'messages_html': messages_html})
        
        elif request.method == 'POST':
            # Send a new message
            form = MessageForm(request.POST)
            if form.is_valid():
                message = form.save(commit=False)
                message.sender = request.user  # Admin sending to user
                message.recipient = user
                message.save()
                # Fetch updated conversation
                # messages = Message.objects.filter(
                #     models.Q(sender=request.user, recipient=user) | 
                #     models.Q(sender=user, recipient=request.user)
                # ).order_by('timestamp')
                new_message_html = render_to_string('core/message_item.html', {'message': message, 'current_user': request.user}, request=request)
                return JsonResponse({'success': True, 'new_messages_html': new_message_html})
            else:
                print(form.errors)
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    messages = Message.objects.filter(
        models.Q(sender=request.user, recipient=user) | 
        models.Q(sender=user, recipient=request.user)
    ).order_by('timestamp')
    return render(request, 'ad/user_messages.html', {'user': user, 'messages': messages})


@login_required
def get_chat_users(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        users = CustomUser.objects.exclude(id=request.user.id)  # Exclude current user
        users_html = render_to_string('core/chat_users.html', {'users': users}, request=request)
        return JsonResponse({'users_html': users_html})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@admin_required
def manage_leave_requests(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # AJAX request
        if request.method == 'GET':
            # Fetch pending leave requests
            leave_requests = LeaveRequest.objects.filter(status='Pending')
            data = [{
                'id': req.id,
                'user': req.user.username,
                'start_date': req.start_date.isoformat(),
                'end_date': req.end_date.isoformat(),
                'reason': req.reason,
                'status': req.status
            } for req in leave_requests]
            return JsonResponse({'leave_requests': data})
        
        elif request.method == 'POST':
            # Handle approve/deny action
            request_id = request.POST.get('request_id')
            action = request.POST.get('action')
            leave_request = get_object_or_404(LeaveRequest, id=request_id)
            profile = UserProfile.objects.get(user=leave_request.user)
            if action == 'approve':
                # Calculate requested days
                requested_days = (leave_request.end_date - leave_request.start_date).days + 1
                
                # Check if enough leave balance remains (redundant check, but safe)
                if requested_days > profile.leave_balance:
                    return JsonResponse({
                        'success': False,
                        'error': f"Cannot approve: User only has {profile.leave_balance} days left."
                    }, status=400)
                
                # Deduct leave balance and approve
                profile.leave_balance -= requested_days
                profile.save()
                leave_request.status = 'Approved'
                messages.success(request, f"Leave request for {leave_request.user.username} approved. {requested_days} days deducted.")
            elif action == 'deny':
                leave_request.status = 'Denied'
                messages.success(request, f"Leave request for {leave_request.user.username} denied.")
            leave_request.save()
            return JsonResponse({'success': True, 'status': leave_request.status})
    
    # Non-AJAX: Render the full tenant_home page
    leave_requests = LeaveRequest.objects.all()  # Show all for admin view
    return render(request, 'core/tenant_home.html' , {'leave_requests': leave_requests})

@admin_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Project '{project.name}' created successfully.")
            ActivityLog.objects.create(action=f"New Project '{project.name}' was created.")
            
            return redirect('core:user_management')  # Or a project management page
    else:
        form = ProjectForm()
    return render(request, 'ad/create_project.html', {'form': form})