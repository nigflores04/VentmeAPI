# Ventics AI API (FastAPI)

Minimal FastAPI service with a stub GenAI image generation endpoint, structured to be swapped with a real provider later.

## Features
- FastAPI app with versioned routes under `/v1`
- Health check at `/healthz`
- Image generation endpoint: `POST /v1/images/generate`
- Config via environment variables using pydantic-settings

## Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI at: http://localhost:8000/docs

## Endpoint Summary
- GET `/healthz` → `{ "status": "ok" }`
- POST `/v1/images/generate`
  - Request body:
    ```json
    {
      "prompt": "string",
      "width": 512,
      "height": 512,
      "seed": 123
    }
    ```
  - Response body:
    ```json
    {
      "image_base64": "...",
      "width": 512,
      "height": 512,
      "model": "stub"
    }
    ```

## Configuration
Configure via environment variables (optional):
- `APP_NAME` (default: "Ventics AI API")
- `VERSION` (default: "0.1.0")
- `MODEL_PROVIDER` (default: "stub")
- `TIMEOUT` (default: 30)

Create a `.env` file if you want to override defaults.

## Payment System (Paystack)

The API integrates with Paystack for payment processing and credit purchases.

### Configuration

Add these environment variables to your `.env` file:

```
PAYSTACK_SECRET_KEY=sk_test_your_secret_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key_here
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret_here
```

### Payment Flow

1. **Create Payment Intent**
   - Endpoint: `POST /v1/payments/create-intent`
   - Request: `{"plan": "basic", "return_url": "https://your-frontend.com/payment-callback"}`
   - Response: Contains `payment_intent_id` (Paystack reference) and `client_secret` (Paystack access code)

2. **Frontend Integration**
   - Use the Paystack reference and access code to redirect users to the Paystack payment page
   - After payment, Paystack redirects to your `return_url`

3. **Verify Payment**
   - Endpoint: `GET /v1/payments/verify/{reference}`
   - Call this endpoint from your frontend after Paystack redirects back
   - This confirms the payment and adds credits to the user's account

4. **Webhook Integration**
   - Configure your Paystack dashboard to send webhooks to: `https://your-api.com/v1/payments/webhook`
   - This ensures payments are processed even if users don't return to your site

### Subscription Plans

The system offers these subscription plans:
- **Starter**: 10 credits for ₦3,999.00
- **Basic**: 30 credits for ₦7,999.00
- **Premium**: 50 credits for ₦11,999.00

### Payment History

Users can view their payment history:
- Endpoint: `GET /v1/payments/history`
- Requires authentication
