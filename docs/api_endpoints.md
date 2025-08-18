
---

### 📂 `docs/api_endpoints.md`

```markdown
# API Endpoints

Base URL: `http://localhost:8000/api/`

---

## Authentication
- **OIDC Login**  
  `/oidc/authenticate/` → Redirect to provider  
  `/oidc/callback/` → Handle login callback  

---

## Categories
- **POST** `/categories/`  
  Create category hierarchy.  
  Payload:
  ```json
  { "path": ["All Products", "Produce", "Fruits"] }
