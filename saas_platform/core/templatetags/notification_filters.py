from django import template

register = template.Library()

@register.filter
def filter_by_type(notifications, notification_type):
    """Filter notifications by their type.
    
    Args:
        notifications: QuerySet of notifications
        notification_type: Type of notification to filter (message, project, leave)
    
    Returns:
        Filtered notifications of the specified type
    """
    return [n for n in notifications if n.notification_type == notification_type]

