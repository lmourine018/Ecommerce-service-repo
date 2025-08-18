
```markdown
# Architecture Overview

## Components
- **Django API (DRF)** → business logic, REST endpoints.
- **PostgreSQL** → relational database.
- **OIDC Provider (Google)** → authentication.
- **Africa’s Talking** → SMS notifications.
- **SMTP (SendGrid or Postfix)** → admin email.
- **Kubernetes (Minikube/kind)** → deployment.

## Data Flow
1. Customer logs in via OIDC.
2. Product catalog managed via API.
3. Customer places an order.
4. System stores order in DB.
5. Triggers:
   - SMS notification to customer.
   - Email notification to admin.

## Deployment
- **Local Dev** → `runserver` or Docker.
- **CI/CD** → GitHub Actions.
- **Production** → Docker + Kubernetes.

## Diagram
