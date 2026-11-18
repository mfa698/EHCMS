# EHCMS

EHCMS has two independently hosted development projects:

- Django REST backend: `backend/ehcm/`
- Plain HTML/CSS/JavaScript frontend: `ehcms_mainfrontend-/`

## Prerequisites

- Python 3.13 or 3.14
- `pip` or `virtualenv`
- Ngrok for local Africa's Talking callbacks
- Gmail account with a 16-character App Password for SMTP

## Backend setup

```bash
cd /home/isaac/Desktop/projects/EHCMS/backend/ehcm
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver 127.0.0.1:8080
```

Create `backend/ehcm/.env` and configure the secrets locally:

```env
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

FRONTEND_BASE_URL=http://localhost:5173

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_TIMEOUT=20
EMAIL_HOST_USER=your-account@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-account@gmail.com

AT_USERNAME=sandbox
AT_API_KEY=your-africas-talking-api-key
AT_DELIVERY_REPORT_TOKEN=generate-a-long-random-token
AT_DELIVERY_REPORT_CALLBACK_URL=
AT_INBOX_CALLBACK_URL=
```

Generate a webhook token with:

```bash
openssl rand -hex 32
```

Do not commit `.env`. It contains API keys and email credentials.

## Frontend setup

Serve the frontend separately:

```bash
cd /home/isaac/Desktop/projects/EHCMS/ehcms_mainfrontend-
python3 -m http.server 5173 --bind 127.0.0.1
```

Open `http://localhost:5173/`.

The frontend API address is configured in `js/api.js`. For the setup above it is:

```javascript
BASE_URL: "http://127.0.0.1:8080"
```

If Django is started on another port, update this value in the frontend.

## Run both servers together

Use two terminals:

```bash
# Terminal 1: Django API
cd /home/isaac/Desktop/projects/EHCMS/backend/ehcm
.venv/bin/python manage.py runserver 127.0.0.1:8080
```

```bash
# Terminal 2: frontend
cd /home/isaac/Desktop/projects/EHCMS/ehcms_mainfrontend-
python3 -m http.server 5173 --bind 127.0.0.1
```

## Africa's Talking sandbox callbacks through Ngrok

Use a third terminal for Ngrok:

```bash
ngrok http 8080
```

Copy the generated public HTTPS URL, for example:

```text
https://example-subdomain.ngrok-free.app
```

Ngrok must target the Django port, not the frontend port. The URL also changes whenever the Ngrok tunnel is recreated unless a reserved domain is used.

Set both callbacks in the Africa's Talking sandbox app:

- Delivery reports: `https://example-subdomain.ngrok-free.app/api/webhooks/africastalking/delivery/<AT_DELIVERY_REPORT_TOKEN>/`
- SMS inbox: `https://example-subdomain.ngrok-free.app/api/webhooks/africastalking/inbox/<AT_DELIVERY_REPORT_TOKEN>/`

For the callback pages:

- `https://account.africastalking.com/apps/sandbox/sms/dlr/callback`
- `https://account.africastalking.com/apps/sandbox/sms/inbox/callback`

Update the same public URLs in `backend/ehcm/.env`:

```env
AT_DELIVERY_REPORT_CALLBACK_URL=https://example-subdomain.ngrok-free.app/api/webhooks/africastalking/delivery/<AT_DELIVERY_REPORT_TOKEN>/
AT_INBOX_CALLBACK_URL=https://example-subdomain.ngrok-free.app/api/webhooks/africastalking/inbox/<AT_DELIVERY_REPORT_TOKEN>/
```

Replace `<AT_DELIVERY_REPORT_TOKEN>` with the real value configured in `.env`. Restart Django after changing `.env`.

The delivery callback route is:

```text
POST /api/webhooks/africastalking/delivery/<token>/
```

The inbox callback route is:

```text
POST /api/webhooks/africastalking/inbox/<token>/
```

Ngrok's local inspection dashboard is normally available at `http://127.0.0.1:4040`.

## Main API areas

- Authentication: `/api/auth/login/`, `/api/auth/verify-otp/`, `/api/auth/change-password/`
- Admin users: `/api/admin/users/`
- Dashboards: `/api/dashboard/consul/`, `/api/dashboard/ambassador/`
- Contracts: `/api/contracts/`
- Work logs: `/api/worklogs/`
- Reports: `/api/reports/`
- Notifications: `/api/notifications/`

## Tests

```bash
cd /home/isaac/Desktop/projects/EHCMS/backend/ehcm
.venv/bin/python manage.py test
.venv/bin/python manage.py check
```
