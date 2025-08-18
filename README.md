# Ecommerce Project 

> **Stack**: Python 3.12, Django 5, Django REST Framework, PostgreSQL, OpenID Connect (OIDC), Africa’s Talking (SMS), GitHub Actions (CI/CD), Docker, Kubernetes (minikube)

---


## Project Overview

A production-ready ecommerce backend that supports hierarchical product categories (arbitrary depth), basic customer and order management, OIDC-based authentication, REST APIs for product ingestion and order placement, SMS notifications via Africa’s Talking, and administrator email alerts. It includes unit tests with coverage, a CI pipeline, optional CD, and manifests for Kubernetes deployment using minikube or kind.

**Key Capabilities**

* Arbitrary-depth category tree (e.g., `All Products > Produce > Fruits > Citrus > Oranges`).
* Product ingestion with category assignments.
* Average price query for a category **including all descendants**.
* Order placement (cart → order) with SMS to customer and email to admin.
* OIDC login flow for customers; role-based authorization (customer/admin).
* Automated tests, coverage, linting, and CI via GitHub Actions.
* Dockerized app with K8s manifests for quick cluster bootstrapping.

---

## Architecture & Components

**Core Services**
* **Django API**: Exposes REST endpoints via DRF.
* **PostgreSQL**: Primary relational DB.

**Integrations**

* **OIDC Provider**:  Google OIDC.
* **Africa’s Talking (AT)**: SMS notifications.
* **SMTP**: SendGrid, Mailgun, or any SMTP server for admin email.


## Data Model

### Entities

* **Customer**

  * `id`, `email`, `full_name`, `phone`, created_at`, `updated_at`
  * Authentication bound to OIDC subject (`oidc_sub`) and Django user.

* **Category** (MPTT)

  * `id`, `name`, `slug`, `parent` (self-relation), `level`

* **Product**

  * `id`, `name`, `description`, `price`, `created_at`, `updated_at`
  * M2M: `categories` → `Category`

* **Order**

  * `id`, `customer` (FK), `status` (e.g., `PENDING`, `PAID`, `CANCELLED`), `total_amount`, `placed_at`

* **OrderItem**

  * `id`, `order` (FK), `product` (FK), `quantity`, `unit_price`


### Migrations

Run `python manage.py makemigrations && python manage.py migrate` to create DB schema.

---

## Authentication & Authorization (OIDC)

We use **OpenID Connect** to authenticate customers.

* `mozilla-django-oidc`

### Settings (example)

```python
# settings/base.py
INSTALLED_APPS += [
  'mozilla_django_oidc',
  'rest_framework',
 
]

AUTHENTICATION_BACKENDS = [
  'django.contrib.auth.backends.ModelBackend',
]

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

OIDC_RP_CLIENT_ID = env('OIDC_RP_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = env('OIDC_RP_CLIENT_SECRET')
OIDC_OP_AUTHORIZATION_ENDPOINT = env('OIDC_OP_AUTHORIZATION_ENDPOINT')
OIDC_OP_TOKEN_ENDPOINT = env('OIDC_OP_TOKEN_ENDPOINT')
OIDC_OP_USER_ENDPOINT = env('OIDC_OP_USER_ENDPOINT')
OIDC_OP_JWKS_ENDPOINT = env('OIDC_OP_JWKS_ENDPOINT')
OIDC_RP_SIGN_ALGO = 'RS256'

REST_FRAMEWORK = {
  'DEFAULT_AUTHENTICATION_CLASSES': (
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.BasicAuthentication',
  ),
  'DEFAULT_PERMISSION_CLASSES': (
    'rest_framework.permissions.IsAuthenticated',
  ),
}
```

### Views

* `/oidc/authenticate/` → Redirect to provider
* `/oidc/callback/` → Handle OIDC callback, create/link Django user, store `oidc_sub` in `Customer`

### Authorization

* Customers can view their own orders; admins can manage catalog and view all orders.

---
### Auth

Use OIDC for login (browser-based); for API, issue DRF token or JWT after OIDC callback if required by clients.

### Endpoints

#### 1) Upload Products & Categories

* **POST** '/products/upload/`

  * Payload:

    ```json
    {
      "products": [
        {
          "name": "Whole Wheat Bread",
          "description": "Fresh bakery bread",
          "price": "3.99",
          "currency": "USD",
          "categories": [
            ["All Products", "Bakery", "Bread"]
          ]
        }
      ]
    }
    ```
  * Behavior: Ensures full category path exists (creates missing nodes) using MPTT; links product to leaf node(s).
  * Response: `201 Created` with created/updated product IDs.

* **POST** `/categories/`

  * Payload:

    ```json
    { "path": ["All Products", "Produce", "Fruits", "Citrus"] }
    ```
  * Response: Returns the leaf category data.

#### 2) Average Product Price for a Category (incl. descendants)

* **GET** `/categories/{slug}/average_price/`

  * Response:

    ```json
    {
      "category": "fruits",
      "average_price": 2.57,
      "currency": "USD",
      "product_count": 41,
      "include_descendants": true
    }
    ```

#### 3) Make Orders

* **POST** '/orders/`

  * Auth: Customer (OIDC)
  * Payload:

    ```json
    {
      "items": [
        { "product_id": 10, "quantity": 2 },
        { "product_id": 15, "quantity": 1 }
      ],
      "currency": "USD"
    }
    ```
  * Response `201 Created`:

    ```json
    {
      "id": 123,
      "status": "PENDING",
      "total_amount": "10.97",
      "currency": "USD",
      "placed_at": "2025-08-18T10:00:00Z",
      "items": [
        { "product": 10, "quantity": 2, "unit_price": "3.99" },
        { "product": 15, "quantity": 1, "unit_price": "2.99" }
      ]
    }
    ```
  * Side-effects: Triggers SMS to customer via Africa’s Talking and email to admin.

#### 4) Order Retrieval (Customer scope)

* **GET** `/orders/` → list current customer’s orders
* **GET** `/orders/{id}/` → order detail
---


### Order Total

* `Order.total_amount` computed from `sum(item.quantity * item.unit_price)`; saved at creation.

---

## Notifications (SMS & Email)

### Africa’s Talking (Sandbox)

**Env Vars**

```
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=
AFRICASTALKING_SENDER_ID=
```

**Usage (example service)**

```python
import africastalking
from django.conf import settings

africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
sms = africastalking.SMS

def send_order_sms(msisdn: str, order_id: int, total: str):
    message = f"Your order #{order_id} has been placed. Total: {total}. Thank you!"
    sms.send(message, [msisdn], settings.AFRICASTALKING_SENDER_ID)
```

### Admin Email

**Env Vars**

```
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sg_key
EMAIL_PORT=587
EMAIL_USE_TLS=true
ADMIN_EMAIL=admin@example.com
```

**Send**

```python
from django.core.mail import send_mail
from django.conf import settings

def notify_admin_order(order):
    subject = f"New order #{order.id}"
    body = f"Customer: {order.customer.full_name}\nTotal: {order.total_amount} {order.currency}\nItems: {order.items.count()}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])
```

Trigger both in an `OrderService.create_order()` or DRF `perform_create` hook.

---

## Local Development

### Prerequisites

* Python 3.12+, Poetry or pip
* PostgreSQL 14+
* (Optional) Redis
* Node.js (if you serve API docs UI or frontend later)

### Setup

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment Variables (.env.example)

```
DEBUG=true
SECRET_KEY=changeme
DATABASE_URL=postgres://user:pass@localhost:5432/ecomms
ALLOWED_HOSTS=*

# OIDC
OIDC_RP_CLIENT_ID=xxx
OIDC_RP_CLIENT_SECRET=xxx
OIDC_OP_AUTHORIZATION_ENDPOINT=https://.../authorize
OIDC_OP_TOKEN_ENDPOINT=https://.../token
OIDC_OP_USER_ENDPOINT=https://.../userinfo
OIDC_OP_JWKS_ENDPOINT=https://.../jwks

# SMS
AFRICASTALKING_USERNAME=sandbox
AFRICASTALKING_API_KEY=xxx
AFRICASTALKING_SENDER_ID=EComms

# Email
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@example.com
ADMIN_EMAIL=admin@example.com
```

---

## Testing & Coverage

### Unit Tests

* Use `pytest`, `pytest-django`, `pytest-cov`.
* Coverage threshold: **85%** (configurable).

**Commands**

```bash
pytest -q --cov=apps --cov-report=term-missing
```

**pytest config** 

```toml
[tool.pytest.ini_options]
django_find_project = true
addopts = "--cov=apps --cov-report=term-missing -q"
filterwarnings = ["ignore::DeprecationWarning"]

[tool.coverage.report]
fail_under = 85
show_missing = true
```

### Integration/E2E (Optional, bonus)

* Spin PostgreSQL with Testcontainers or Docker Compose.
* Use `requests` against the running API, or `django.test.Client` for flows: OIDC login mock → product upload → order placement → notifications mocked.

---



## Containerization


## Deployment (Kubernetes)

### Manifests

`k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ecomms-api
spec:
  replicas: 2
  selector:
    matchLabels: { app: ecomms-api }
  template:
    metadata:
      labels: { app: ecomms-api }
    spec:
      containers:
        - name: api
          image: ghcr.io/<owner>/ecomms:latest
          ports: [{ containerPort: 8000 }]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: ecomms-secrets
                  key: DATABASE_URL
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: ecomms-secrets
                  key: SECRET_KEY
---
apiVersion: v1
kind: Service
metadata:
  name: ecomms-service
spec:
  selector: { app: ecomms-api }
  ports:
    - port: 80
      targetPort: 8000
  type: NodePort
```

`k8s/secrets.yaml` *(create with real values)*

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ecomms-secrets
stringData:
  DATABASE_URL: postgresql://postgres:postgres@db:5432/ecomms
  SECRET_KEY: changeme
```

### Minikube

* Apply manifests:

  ```bash
  kubectl apply -f k8s/
  ```
* Get service URL (minikube):

  ```bash
  minikube service ecomms-service --url
  ```
* For **kind**, use an Ingress (e.g., NGINX Ingress Controller) and create `Ingress` manifest.

---





