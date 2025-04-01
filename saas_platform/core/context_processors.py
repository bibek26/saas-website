# core/context_processors.py
from django_tenants.utils import schema_context
from .models import Tenant, TenantCustomization, Domain

def tenant_context(request):
    tenant = None
    customization = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        with schema_context('public'):
            try:
                if not request.user.is_superuser:
                    tenant = Tenant.objects.get(schema_name=request.user.tenant_schema)
                    customization, _ = TenantCustomization.objects.get_or_create(tenant=tenant)
                else:
                    tenant = Tenant.objects.filter(schema_name='public').first()  # Fallback for superuser
                    if tenant:
                        customization, _ = TenantCustomization.objects.get_or_create(tenant=tenant)
            except Tenant.DoesNotExist:
                print(f"Tenant not found for schema: {request.user.tenant_schema}")
    # Fallback for unauthenticated users
    if not tenant:
        with schema_context('public'):
            domain = request.get_host().split(':')[0]
            try:
                domain_obj = Domain.objects.get(domain=domain)
                tenant = domain_obj.tenant
                customization, _ = TenantCustomization.objects.get_or_create(tenant=tenant)
            except Domain.DoesNotExist:
                tenant = None
                customization = None
    print(f"Context - Tenant: {tenant.schema_name if tenant else 'None'}, Primary: {customization.primary_color if customization else 'None'}")
    return {
        'tenant': tenant,
        'customization': customization,
    }