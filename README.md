# SaaS Platform

A comprehensive multi-tenant SaaS (Software as a Service) platform built with Django and PostgreSQL. This project leverages `django-tenants` to provide schema-based multi-tenancy, isolating data for each tenant while sharing the same code base.

## Features

*   **Multi-tenancy:** Schema-based isolation using `django-tenants`.
*   **User Management:** Custom user model with roles (Admin, Manager, User).
*   **SaaS Features:**
    *   Subscription Management (Basic, Pro plans)
    *   Billing & Payment History
    *   Tenant Customization (Branding, Colors)
    *   Analytics
*   **Productivity Tools:**
    *   Project & Task Management
    *   Messaging System
    *   Leave Request System
    *   Ticketing System / Help Desk
*   **Dockerized:** Ready-to-deploy setup using Docker and Docker Compose.

## Tech Stack

*   **Backend:** Python 3, Django 5.1.7
*   **Database:** PostgreSQL 15 (Required for `django-tenants`)
*   **Server:** Gunicorn
*   **Containerization:** Docker, Docker Compose

## Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

## Installation & Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd saas-website
    ```

2.  **Build and start the containers:**

    ```bash
    docker-compose up --build
    ```

    This will start the Django web server and the PostgreSQL database.

3.  **Apply Migrations:**

    The migrations need to be applied to the public schema and any existing tenant schemas.

    ```bash
    docker-compose exec web python manage.py migrate_schemas --shared
    ```

4.  **Create the Public Tenant:**

    `django-tenants` requires a "public" tenant to handle the main domain and shared data. You need to create this via the Python shell.

    ```bash
    docker-compose exec web python manage.py shell
    ```

    Inside the shell:

    ```python
    from core.models import Tenant, Domain

    # Create the public tenant
    tenant = Tenant(schema_name='public', name='Public Tenant', domain='localhost')
    tenant.save()

    # Create the domain for the public tenant
    domain = Domain()
    domain.domain = 'localhost' # or your local IP / main domain
    domain.tenant = tenant
    domain.is_primary = True
    domain.save()

    exit()
    ```

5.  **Create a Superuser:**

    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

6.  **Access the Application:**

    Open your browser and navigate to `http://localhost:8000`.

## Usage

### Creating New Tenants

To create a new tenant (e.g., for a new customer), you can use the Django Admin interface or the shell.

**Using Shell:**

```python
from core.models import Tenant, Domain

# Create a new tenant
tenant = Tenant(schema_name='acme', name='Acme Corp', domain='acme.local')
tenant.save()

# Create the domain
domain = Domain()
domain.domain = 'acme.localhost' # Subdomain for local testing
domain.tenant = tenant
domain.is_primary = True
domain.save()
```

*Note: To access subdomains locally (e.g., `acme.localhost`), you might need to configure your `/etc/hosts` file or use a browser that resolves `*.localhost` automatically (like Chrome).*

## Environment Variables

The application uses environment variables for configuration. You can set these in the `docker-compose.yml` file or a `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DJANGO_SECRET_KEY` | Secret key for Django | `django-insecure...` |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `192.168.1.31,acme.local,localhost,*.local` |
| `DB_NAME` | Database name | `saas_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `root` |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |

## Project Structure

```
saas-website/
├── saas_platform/
│   ├── core/                 # Main application logic (Models, Views)
│   ├── media/                # User uploaded files
│   ├── saas_platform/        # Project settings
│   ├── staticfiles/          # Collected static files
│   ├── templates/            # HTML Templates
│   ├── Dockerfile            # Docker build instructions
│   ├── docker-compose.yml    # Docker Compose services
│   ├── manage.py             # Django management script
│   └── requirements.txt      # Python dependencies
└── README.md                 # Project documentation
```

## Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/NewFeature`).
3.  Commit your changes (`git commit -m 'Add some NewFeature'`).
4.  Push to the branch (`git push origin feature/NewFeature`).
5.  Open a Pull Request.
