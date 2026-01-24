Production Readiness: Database, Security, Performance & Error Handling
This plan addresses four critical issues to prepare the Ventics AI API for production deployment.

User Review Required
IMPORTANT

Critical Security Changes

CORS will be restricted from allow_origins=["*"] to specific domains (requires your frontend URL)
JWT secret key must be changed from default "change-me-in-prod" to a secure random value
Sensitive credentials in 
.env
 will be flagged for rotation before production deployment
WARNING

Breaking Changes

Some API endpoints may return different error response formats after centralized error handling implementation
Database cascade delete behaviors will be added, which may affect data retention if not properly understood
Rate limiting will be added to authentication endpoints, which may affect automated testing scripts
CAUTION

Environment Variables Required You'll need to provide:

FRONTEND_URL - Your frontend application URL for CORS configuration
JWT_SECRET_KEY - A new secure random string (will generate one for you)
PAYSTACK_WEBHOOK_SECRET - Currently missing but required for webhook signature verification
Proposed Changes
Issue #16: Database Schema & Model Validation
[MODIFY] 
schema.prisma
Add cascade delete/nullify rules to all relationships:

User
 → 
GenerationJob
: Add onDelete: SetNull (preserve generations when user deleted)
User
 → Payment: Add onDelete: Cascade (remove payment records with user)
User
 → Subscription: Add onDelete: Cascade (cancel subscriptions when user deleted)
User
 → Moodboard: Add onDelete: SetNull (already has this, verify it's working)
Project
 → 
GenerationJob
: Add onDelete: SetNull (preserve generations when project deleted)
Subscription → Payment: Add onDelete: SetNull (preserve payment history)
Add database constraints:

Add @db.Text for long text fields (
prompt
, 
error
, description, items)
Add length constraints on status fields (enum-like strings)
Add check constraints for numeric fields (credits >= 0, amount > 0, width/height > 0)
Add indexes on frequently queried fields (userId, 
status
, projectId, payment_reference)
[MODIFY] 
auth_schemas.py
Enhance validation:

Add password strength validation (uppercase, lowercase, number, special char)
Add email domain validation
Add name length constraints (min 2, max 100 characters)
Add custom validators for verification code format
[MODIFY] 
schemas.py
Add validation rules:

Validate width/height ranges (256-2048 pixels)
Add enum validation for room_type and style_preset
Add prompt length constraints (max 500 characters)
Validate image URLs format
[MODIFY] 
payment_schemas.py
Add payment validation:

Validate amount is positive
Validate plan codes against allowed values
Add reference format validation
Validate credit amounts are positive integers
Issue #17: Performance & Scalability Optimization
[MODIFY] 
users.py
Fix N+1 query in 
get_user_generations
:

Add include parameter to fetch related data in single query
Use select to limit fields returned
Add pagination metadata (total count, has_more)
[MODIFY] 
project_service.py
Optimize project queries:

Use include to fetch generations with projects in single query
Add database indexes for common query patterns
Implement query result caching for frequently accessed projects
Batch database operations where possible
[MODIFY] 
generations_service.py
Improve async processing:

Add proper task queue for background generation jobs (using asyncio.Queue)
Implement connection pooling for external API calls
Add timeout handling for long-running operations
Implement retry logic with exponential backoff for API failures
[NEW] 
cache_middleware.py
Add response caching:

Implement Redis-based caching for GET endpoints
Cache pricing data, user profiles, completed generations
Add cache invalidation on data updates
Configure TTL per endpoint type
Issue #18: Error Handling, Logging & Route Exposure
[NEW] 
exceptions.py
Create custom exception hierarchy:

class VenticsAPIException(Exception)
class AuthenticationError(VenticsAPIException)
class AuthorizationError(VenticsAPIException)
class ValidationError(VenticsAPIException)
class ResourceNotFoundError(VenticsAPIException)
class ExternalServiceError(VenticsAPIException)
class PaymentError(VenticsAPIException)
Each exception includes:

HTTP status code
Error code (for client handling)
User-friendly message
Optional details dict (never includes sensitive data)
[NEW] 
error_handlers.py
Centralized error handling:

Standardized error response format
Automatic error logging with context
Sanitize error messages (no stack traces to clients)
Request ID tracking for debugging
Error response format:

{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid credentials provided",
    "request_id": "req_abc123",
    "timestamp": "2026-01-24T01:17:13Z"
  }
}
[NEW] 
logging_config.py
Structured logging system:

JSON-formatted logs for production
Contextual logging (request_id, user_id, endpoint)
Separate log levels per module
Log rotation and retention policies
Sensitive data filtering (passwords, tokens, API keys)
Log format:

{
  "timestamp": "2026-01-24T01:17:13Z",
  "level": "INFO",
  "logger": "app.services.auth_service",
  "message": "User login successful",
  "context": {
    "request_id": "req_abc123",
    "user_id": "user_xyz",
    "endpoint": "/v1/auth/login",
    "duration_ms": 145
  }
}
[MODIFY] 
main.py
Integrate error handling and logging:

Replace basic exception handlers with centralized system
Add request ID middleware
Add request/response logging middleware
Remove debug print statements
Configure structured logging
[MODIFY] All endpoint files
Sanitize responses:

Remove internal error details from responses
Never expose database errors directly
Remove stack traces from production responses
Audit all response models to ensure no sensitive data leakage
Add response filtering for user data (no password hashes, verification codes)
Issue #19: Security - Authentication & API Configuration
[MODIFY] 
config.py
Security configuration improvements:

Change JWT_SECRET_KEY default to require environment variable
Add JWT_REFRESH_TOKEN_EXPIRE_DAYS setting
Add ALLOWED_ORIGINS list for CORS
Add RATE_LIMIT_PER_MINUTE settings
Add REQUIRE_EMAIL_VERIFICATION flag
Add PASSWORD_MIN_LENGTH and PASSWORD_REQUIRE_SPECIAL_CHARS settings
Validate all required secrets are present on startup
[MODIFY] 
main.py
Fix CORS configuration:

# BEFORE (INSECURE):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Allows any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# AFTER (SECURE):
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ✅ Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Cache preflight requests
)
[MODIFY] 
security.py
Enhance JWT security:

Add token blacklisting for logout
Implement refresh token rotation
Add token expiration validation
Add issuer and audience claims
Implement rate limiting on token generation
Add token fingerprinting (bind to user agent/IP)
[MODIFY] 
auth.py
Improve authentication middleware:

Add rate limiting to prevent brute force
Implement account lockout after failed attempts
Add IP-based suspicious activity detection
Cache user lookups to reduce database queries
Add proper error messages without leaking information
Validate token expiration before database lookup
[NEW] 
rate_limiter.py
Implement rate limiting:

Use Redis for distributed rate limiting
Different limits for different endpoint types:
Auth endpoints: 5 requests/minute
Generation endpoints: 10 requests/minute
Read endpoints: 100 requests/minute
Return 429 Too Many Requests with Retry-After header
[MODIFY] 
auth_service.py
Security improvements:

Add password strength validation
Implement account lockout mechanism
Add email verification requirement enforcement
Hash verification codes before storing
Add audit logging for authentication events
Implement session management
[MODIFY] 
payment_service.py
Webhook security:

Implement Paystack signature verification (currently missing)
Add replay attack prevention (timestamp validation)
Add idempotency keys for payment operations
Log all webhook events for audit trail
Validate webhook payload structure
[NEW] 
.env.example
Create environment template:

Document all required environment variables
Provide example values (non-sensitive)
Add security warnings for production
Remove actual credentials from version control
[MODIFY] 
.gitignore
Ensure sensitive files are ignored:

Add 
.env
 (if not already present)
Add .env.local, .env.production
Add log files
Add database files
Verification Plan
Automated Tests
1. Database Schema Validation
# Run Prisma schema validation
cd c:\Users\Main\Downloads\ventics-ai-api-master
prisma validate --schema=prisma/schema.prisma
# Generate Prisma client with new schema
prisma generate --schema=prisma/schema.prisma
# Create migration (review before applying)
prisma migrate dev --name add_cascade_rules_and_constraints --create-only
2. Model Validation Tests
Create new test file: tests/test_model_validation.py

# Run validation tests
pytest tests/test_model_validation.py -v
Tests will cover:

Password strength validation
Email format validation
Field length constraints
Numeric range validation
Enum value validation
3. Security Tests
Create new test file: tests/test_security.py

# Run security tests
pytest tests/test_security.py -v
Tests will cover:

CORS configuration
JWT token validation
Rate limiting
Authentication bypass attempts
Webhook signature verification
Manual Verification
1. CORS Configuration Test
Steps:

Start the API server: uvicorn app.main:app --reload
Open browser console on a different origin (e.g., http://localhost:3000)
Run this JavaScript:
fetch('http://localhost:8000/v1/users/me', {
  headers: { 'Authorization': 'Bearer <valid-token>' }
}).then(r => console.log('CORS test:', r.status))
Expected: Request should fail with CORS error if origin not in ALLOWED_ORIGINS
Expected: Request should succeed if origin is in ALLOWED_ORIGINS
2. Rate Limiting Test
Steps:

Start the API server
Use a tool like curl or Postman to make rapid requests:
for i in {1..10}; do
  curl -X POST http://localhost:8000/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' &
done
Expected: After 5 requests, should receive 429 Too Many Requests
Expected: Response should include Retry-After header
3. Error Response Format Test
Steps:

Start the API server
Make a request that will fail (e.g., invalid authentication):
curl -X GET http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer invalid-token"
Expected response format:
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Authentication token is invalid",
    "request_id": "req_...",
    "timestamp": "2026-01-24T..."
  }
}
Expected: No stack traces or internal error details in response
4. Cascade Delete Behavior Test
Steps:

Create a test user via API
Create a project for that user
Create generations associated with the project
Delete the project via API: DELETE /v1/projects/{project_id}
Expected: Project is deleted
Expected: Generations still exist but projectId is set to null
Query generations: GET /v1/users/me/generations
Expected: Generations are returned without project association
5. Webhook Signature Verification Test
Steps:

Use Paystack's webhook testing tool or create a test webhook payload
Send webhook without signature:
curl -X POST http://localhost:8000/v1/payments/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"charge.success","data":{"reference":"test"}}'
Expected: Webhook should be rejected (403 Forbidden)
Send webhook with valid signature (use Paystack's signature generation)
Expected: Webhook should be processed successfully
6. Logging Verification
Steps:

Start the API server
Make various API requests (successful and failed)
Check log output for structured JSON format
Expected: Logs should include:
Timestamp
Log level
Logger name
Message
Context (request_id, user_id, endpoint)
Expected: No sensitive data in logs (passwords, tokens, API keys)
7. Password Validation Test
Steps:

Attempt to register with weak password:
curl -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"weak"}'
Expected: Error response indicating password requirements
Register with strong password:
curl -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Strong@Pass123"}'
Expected: Successful registration
Post-Implementation Checklist
 Update 
.env
 with new required variables
 Generate new JWT_SECRET_KEY (use: openssl rand -hex 32)
 Configure ALLOWED_ORIGINS with actual frontend URL
 Rotate all API keys and secrets shown in 
.env
 file
 Run database migration to add cascade rules
 Run all automated tests
 Perform all manual verification tests
 Review logs for any errors or warnings
 Update API documentation with new error response formats
 Set up monitoring for rate limit violations
 Configure log aggregation service (e.g., CloudWatch, Datadog)