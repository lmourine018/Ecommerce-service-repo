# Ecommerce Platform – Full Project Documentation

> **Stack**: Python 3.12, Django 5, Django REST Framework, PostgreSQL, Redis (optional), OpenID Connect (OIDC), Africa’s Talking (SMS), GitHub Actions (CI/CD), Docker, Kubernetes (minikube/kind)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Components](#architecture--components)
3. [Data Model](#data-model)
4. [Authentication & Authorization (OIDC)](#authentication--authorization-oidc)
5. [API Design (REST)](#api-design-rest)
6. [Business Logic](#business-logic)
7. [Notifications (SMS & Email)](#notifications-sms--email)
8. [Local Development](#local-development)
9. [Testing & Coverage](#testing--coverage)
10. [CI/CD](#cicd)
11. [Containerization](#containerization)
12. [Deployment (Kubernetes)](#deployment-kubernetes)
13. [Observability & Monitoring](#observability--monitoring)
14. [Security Considerations](#security-considerations)
15. [Sample Data & Seeding](#sample-data--seeding)
16. [Docs & GitHub Pages](#docs--github-pages)
17. [Project Structure](#project-structure)
18. [Contributing](#contributing)
19. [License](#license)

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
* **Redis** *(optional)*: Caching / rate limiting / background jobs.

**Integrations**

* **OIDC Provider**: e.g., Keycloak, Auth0, Azure AD B2C, or Google OIDC.
* **Africa’s Talking (AT)**: SMS notifications.
* **SMTP**: SendGrid, Mailgun, or any SMTP server for admin email.

**Patterns**

* Category tree via **MPTT** (Modified Preorder Tree Traversal) using `django-mptt`.
* Clean separation of concerns: `apps/catalog`, `apps/orders`, `apps/accounts`.
* Settings split: `settings/base.py`, `settings/local.py`, `settings/prod.py`.

---

## Data Model

### Entities

* **Customer**

  * `id`, `email`, `full_name`, `phone`, `address_line1`, `address_line2`, `city`, `country`, `created_at`, `updated_at`
  * Authentication bound to OIDC subject (`oidc_sub`) and Django user.

* **Category** (MPTT)

  * `id`, `name`, `slug`, `parent` (self-relation), `lft`, `rght`, `tree_id`, `level`

* **Product**

  * `id`, `sku`, `name`, `description`, `price`, `currency`, `is_active`, `created_at`, `updated_at`
  * M2M: `categories` → `Category`

* **Order**

  * `id`, `customer` (FK), `status` (e.g., `PENDING`, `PAID`, `CANCELLED`), `total_amount`, `currency`, `placed_at`

* **OrderItem**

  * `id`, `order` (FK), `product` (FK), `quantity`, `unit_price`

### ER Diagram (textual)

```
Customer (1) ───< Order (n)
Order (1) ───< OrderItem (n) >─── (1) Product (n)
Product (n) ───< ProductCategories (n:m) >─── (1) Category (tree via parent)
```

### Migrations

Run `python manage.py makemigrations && python manage.py migrate` to create DB schema.

---

## Authentication & Authorization (OIDC)

We use **OpenID Connect** to authenticate customers. Recommended libraries:

* `mozilla-django-oidc` (lightweight) **or** `django-allauth` with OIDC. Example uses `mozilla-django-oidc`.

### Settings (example)

```python
# settings/base.py
INSTALLED_APPS += [
  'mozilla_django_oidc',
  'rest_framework',
  'apps.accounts', 'apps.catalog', 'apps.orders',
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

## API Design (REST)

Base URL: `/api/v1/`

### Auth

Use OIDC for login (browser-based); for API, issue DRF token or JWT after OIDC callback if required by clients.

### Endpoints

#### 1) Upload Products & Categories

* **POST** `/api/v1/products/bulk_upload/`

  * Payload:

    ```json
    {
      "products": [
        {
          "sku": "SKU-1001",
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

* **POST** `/api/v1/categories/ensure_path/`

  * Payload:

    ```json
    { "path": ["All Products", "Produce", "Fruits", "Citrus"] }
    ```
  * Response: Returns the leaf category data.

#### 2) Average Product Price for a Category (incl. descendants)

* **GET** `/api/v1/categories/{slug}/average_price/`

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

* **POST** `/api/v1/orders/`

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

* **GET** `/api/v1/orders/` → list current customer’s orders
* **GET** `/api/v1/orders/{id}/` → order detail

#### 5) Catalog Browsing

* **GET** `/api/v1/categories/tree/` → entire category tree
* **GET** `/api/v1/products/` → filters: `category`, `search`, `min_price`, `max_price`, `is_active`

---

## Business Logic

### Category Hierarchy

* Implemented with `django-mptt`. Category paths are created/ensured during product upload.
* Average price endpoint queries all products attached to **descendants** of the selected category (including the category itself).

**Example ORM**

```python
from django.db.models import Avg
from apps.catalog.models import Category, Product

def average_price_for_category_slug(slug: str):
    category = Category.objects.get(slug=slug)
    descendants = category.get_descendants(include_self=True)
    return (Product.objects.filter(categories__in=descendants, is_active=True)
            .aggregate(avg=Avg('price'))['avg'])
```

### Order Total

* `Order.total_amount` computed from `sum(item.quantity * item.unit_price)`; saved at creation.

---

## Notifications (SMS & Email)

### Africa’s Talking (Sandbox)

**Env Vars**

```
AFRICASTALKING_USERNAME=sandbox
AFRICASTALKING_API_KEY=your_key
AFRICASTALKING_SENDER_ID=EComms
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

**Example pytest config** (`pyproject.toml`)

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

## CI/CD

### GitHub Actions (CI)

`.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: ecomms
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ['5432:5432']
        options: >-
          --health-cmd=\"pg_isready -U postgres\" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          python -m pip install -U pip
          pip install -r requirements.txt
      - name: Wait for DB
        run: |
          python - <<'PY'
import time, socket
s=socket.socket();
for _ in range(30):
  try:
    s.connect(('localhost',5432)); s.close(); break
  except: time.sleep(2)
PY
      - name: Migrate & Test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/ecomms
          SECRET_KEY: test
          DEBUG: 'true'
        run: |
          python manage.py migrate
          pytest --cov=apps --cov-report=xml
      - name: Lint
        run: |
          pip install ruff
          ruff check .
```

### CD (Optional)

* Build & push Docker image to GHCR.
* Deploy to Kubernetes using `kubectl` with a GitHub Environment + secrets.

`.github/workflows/cd.yml` (excerpt)

```yaml
- name: Build & Push
  run: |
    docker build -t ghcr.io/<owner>/ecomms:${{ github.sha }} .
    echo $CR_PAT | docker login ghcr.io -u ${{ github.actor }} --password-stdin
    docker push ghcr.io/<owner>/ecomms:${{ github.sha }}
```

---

## Containerization

**Dockerfile**

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000", "-w", "3"]
```

**docker-compose.yml (dev)**

```yaml
version: '3.9'
services:
  api:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [db]
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ecomms
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
volumes:
  pgdata:
```

---

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

### Minikube/kind Notes

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

## Observability & Monitoring

* **Logging**: JSON logs with `structlog` or standard logging; capture request IDs.
* **Metrics**: `django-prometheus` to expose `/metrics` for Prometheus; create ServiceMonitor in K8s.
* **Health**: `/healthz` endpoint returning DB connectivity and migrations state.

---

## Security Considerations

* Enforce HTTPS (HSTS in production).
* Secure cookies, CSRF for browser clients.
* Validate OIDC issuer/audience and rotate client secrets.
* Rate limit order placement endpoint (DRF throttling + Redis).
* Input validation & server-side price calculation (never trust client totals).
* Least-privilege DB credentials.

---

## Sample Data & Seeding

Provide a `manage.py` command `load_seed_data` that:

* Creates category paths (All Products → Produce → Fruits → Citrus, etc.).
* Creates 20+ products with prices across categories.
* Creates a demo customer with OIDC subject stub.

Run: `python manage.py load_seed_data`

---

## Docs & GitHub Pages

* This README is the primary doc. Optionally generate API docs using **drf-spectacular** and serve at `/api/schema/` and Swagger UI at `/api/docs/`.
* To host docs on GitHub Pages:

  1. Create `docs/` with additional guides (setup, API, deployment).
  2. Enable Pages from `main` → `/docs` in repo settings.

**Example `docs/` structure**

```
docs/
  api.md
  deployment.md
  troubleshooting.md
```

---

## Project Structure

```
.
├── apps/
│   ├── accounts/
│   │   ├── models.py  # Customer extends AbstractUser or OneToOne
│   │   ├── oidc.py    # OIDC callback handlers
│   │   └── permissions.py
│   ├── catalog/
│   │   ├── models.py  # Category (MPTT), Product
│   │   ├── serializers.py
│   │   └── views.py
│   └── orders/
│       ├── models.py  # Order, OrderItem
│       ├── services.py # create_order, totals, notifications
│       └── views.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── k8s/
│   ├── deployment.yaml
│   └── secrets.yaml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── .github/workflows/
│   ├── ci.yml
│   └── cd.yml
└── docs/
    ├── api.md
    └── deployment.md
```

---

## Contributing

1. Fork & clone.
2. Create a feature branch: `feat/<short-desc>`.
3. Run tests & linters before PR: `pytest`, `ruff`.
4. Open PR with description & screenshots (if any).

---

## License

MIT (or your preferred license). Add `LICENSE` file at repo root.

---

### Appendix A: DRF Serializers (excerpt)

```python
# apps/catalog/serializers.py
class CategoryPathSerializer(serializers.Serializer):
    path = serializers.ListField(child=serializers.CharField())

class ProductUploadSerializer(serializers.Serializer):
    sku = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    categories = serializers.ListField(child=serializers.ListField(child=serializers.CharField()))
```

### Appendix B: DRF Views (excerpt)

```python
# apps/orders/views.py
class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.create_order(customer=request.user.customer, **serializer.validated_data)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
```

### Appendix C: Troubleshooting

* **minikube service not found**: Ensure `kubectl get svc` shows `ecomms-service` in the same namespace. If using a different namespace, run `minikube service ecomms-service -n <namespace>`.
* **`mozilla_django_oidc` ModuleNotFound**: Add to `requirements.txt`, run `pip install mozilla-django-oidc`. Configure OIDC endpoints.
* **Africa’s Talking sandbox errors**: Verify `AFRICASTALKING_USERNAME=sandbox` and correct API key; ensure the MSISDN is whitelisted in sandbox.
