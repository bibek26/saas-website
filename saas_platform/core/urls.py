from django.contrib import admin
from django.urls import path
from . import views

app_name = "core"
urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('admin-home/', views.admin_home, name='admin_home'),
    path('', views.tenant_home, name='tenant_home'),
    
    path('tenant-profile/edit/', views.tenant_profile_edit, name='tenant_profile_edit'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    #User-management
    path('user-management/', views.user_management, name='user_management'),
    path('add-user/', views.add_user, name='add_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('activate-user/<int:user_id>/', views.activate_user, name='activate_user'),
    path('users/deactivate/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('export-users/', views.export_users, name='export_users'),
    
    #Billing
    path('subscription-billing/', views.subscription_billing, name='subscription_billing'),
    path('update-billing/', views.update_billing, name='update_billing'),
    path('manage-subscription/', views.manage_subscription, name='manage_subscription'),
    
    path('analytics/', views.analytics, name='analytics'),
    path('download-report/', views.download_report, name='download_report'),
    path('customization/', views.customization, name='customization'),
    path('change-password/', views.change_password, name='change_password'),
    
    path('help/', views.help_page, name='help'),
    path('support/tickets/', views.support_tickets, name='support_tickets'),
    path('support/tickets/create/', views.create_ticket, name='create_ticket'),
    
    path('user-home/', views.user_home, name='user_home'),
    path('mark-notification-read/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-notifications-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('update-task-status/<int:task_id>/', views.update_task_status, name='update_task_status'),
    path('update-task-progress/<int:task_id>/', views.update_task_progress, name='update_task_progress'),
    path('delete-task-attachment/<int:attachment_id>/', views.delete_task_attachment, name='delete_task_attachment'),
    path('send-message/', views.send_message, name='send_message'),
    path('request-leave/', views.request_leave, name='request_leave'),
    
    path('messages/<int:user_id>/', views.view_user_messages, name='view_user_messages'),
    path('chat-users/', views.get_chat_users, name='get_chat_users'),
    
    #admin
    path('ad/users/', views.user_list, name='user_list'),
    path('assign-task/<int:user_id>/', views.assign_task, name='assign_task'),
    # path('ad/view-messages/<int:user_id>/', views.view_user_messages, name='view_user_messages'),
    path('ad/send-reply/<int:message_id>/', views.send_reply, name='send_reply'),
    path('create-project/', views.create_project, name='create_project'),
    path('ad/manage-leave-requests/', views.manage_leave_requests, name='manage_leave_requests'),
]
