# Ventics AI Database Schema

## Overview
This document describes the database schema for the Ventics AI API, which manages AI-powered interior design generation, user authentication, payments, and project management.

## Database Configuration
- **Provider**: PostgreSQL
- **Client**: Prisma Client (Python)

---

## Models

### User
Represents registered users of the platform.

**Fields:**
- `id` (UUID, Primary Key) - Unique user identifier
- `email` (String, Unique) - User's email address
- `name` (String, Optional) - User's display name
- `passwordHash` (String, Optional) - Hashed password for password-based authentication
- `provider` (String) - Authentication provider: "password" or "google"
- `emailVerified` (Boolean, Default: false) - Whether the email has been verified
- `verificationCode` (String, Optional) - Email verification code
- `codeExpiresAt` (DateTime, Optional) - Expiration time for verification code
- `codeAttempts` (Integer, Default: 0) - Number of verification attempts
- `credits` (Integer, Default: 1) - Available generation credits
- `createdAt` (DateTime) - Account creation timestamp

**Relations:**
- Has many `GenerationJob` records
- Has many `Payment` records
- Has many `Subscription` records
- Has many `Project` records
- Has many `Moodboard` records

---

### GenerationJob
Represents AI image generation jobs for interior design.

**Fields:**
- `id` (UUID, Primary Key) - Unique job identifier
- `userId` (String, Optional, Foreign Key) - Owner of the generation (null for anonymous users)
- `projectId` (String, Optional, Foreign Key) - Associated project
- `status` (String) - Job status: "queued", "running", "done", or "failed"
- `reference` (String) - Reference image URL/path
- `prompt` (String, Optional) - Text prompt for generation
- `room_type` (String, Optional) - Type of room (e.g., "living_room", "bedroom")
- `style_preset` (String, Optional) - Style preset (e.g., "modern", "minimalist")
- `width` (Integer) - Output image width in pixels
- `height` (Integer) - Output image height in pixels
- `output` (String, Optional) - Generated image URL/path
- `error` (String, Optional) - Error message if job failed
- `createdAt` (DateTime) - Job creation timestamp
- `updatedAt` (DateTime) - Last update timestamp

**Relations:**
- Belongs to `User` (optional)
- Belongs to `Project` (optional)

---

### Payment
Tracks payment transactions for credits and subscriptions.

**Fields:**
- `id` (UUID, Primary Key) - Unique payment identifier
- `userId` (String, Foreign Key) - User who made the payment
- `payment_reference` (String, Unique) - Payment gateway reference
- `plan` (String, Optional) - Subscription plan name
- `amount` (Integer) - Payment amount in kobo (Nigerian currency subunit)
- `credits` (Integer) - Number of credits purchased
- `status` (String) - Payment status: "pending", "processing", "successful", "failed", or "cancelled"
- `description` (String) - Payment description
- `isSubscription` (Boolean, Default: false) - Whether this is a subscription payment
- `subscriptionId` (String, Optional, Foreign Key) - Associated subscription
- `createdAt` (DateTime) - Payment creation timestamp
- `completedAt` (DateTime, Optional) - Payment completion timestamp

**Relations:**
- Belongs to `User`
- Belongs to `Subscription` (optional)

---

### Subscription
Manages recurring subscription plans.

**Fields:**
- `id` (UUID, Primary Key) - Unique subscription identifier
- `userId` (String, Foreign Key) - Subscribed user
- `plan` (String) - Subscription plan name
- `planCode` (String) - Paystack plan code
- `status` (String) - Subscription status: "active", "cancelled", or "expired"
- `nextPaymentDate` (DateTime, Optional) - Next billing date
- `lastPaymentDate` (DateTime, Optional) - Last successful payment date
- `createdAt` (DateTime) - Subscription creation timestamp
- `updatedAt` (DateTime) - Last update timestamp

**Relations:**
- Belongs to `User`
- Has many `Payment` records

---

### Project
Organizes generations into projects/sessions for better workflow management.

**Fields:**
- `id` (UUID, Primary Key) - Unique project identifier
- `userId` (String, Foreign Key) - Project owner
- `name` (String) - Project name
- `description` (String, Optional) - Project description
- `isActive` (Boolean, Default: true) - Whether the project is active
- `referenceImage` (String, Optional) - Current reference image URL
- `prompt` (String, Optional) - Current generation prompt
- `room_type` (String, Optional) - Current room type setting
- `style_preset` (String, Optional) - Current style preset
- `createdAt` (DateTime) - Project creation timestamp
- `updatedAt` (DateTime) - Last update timestamp

**Relations:**
- Belongs to `User` (cascade delete)
- Has many `GenerationJob` records
- Has many `Moodboard` records

---

### Moodboard
Represents mood board generations for design inspiration.

**Fields:**
- `id` (UUID, Primary Key) - Unique moodboard identifier
- `projectId` (String, Foreign Key) - Associated project
- `userId` (String, Optional, Foreign Key) - Creator (set to null if user deleted)
- `referenceImage` (String) - Reference image URL
- `prompt` (String, Optional) - Generation prompt
- `style` (String, Optional) - Style preference
- `colorPalette` (String, Optional) - Color palette specification
- `status` (String) - Generation status: "generating", "completed", or "failed"
- `items` (String) - JSON string containing moodboard items
- `output` (String, Optional) - S3 URL of generated moodboard image
- `createdAt` (DateTime) - Creation timestamp
- `updatedAt` (DateTime) - Last update timestamp

**Relations:**
- Belongs to `Project` (cascade delete)
- Belongs to `User` (optional, set null on delete)

---

### EmailSubscriber
Stores email subscribers for marketing and newsletters.

**Fields:**
- `id` (UUID, Primary Key) - Unique subscriber identifier
- `email` (String, Unique) - Subscriber email address
- `name` (String, Optional) - Subscriber name
- `source` (String, Optional) - Subscription source: "website", "api", or "landing_page"
- `isActive` (Boolean, Default: true) - Whether subscription is active
- `createdAt` (DateTime) - Subscription timestamp

**Relations:**
- None (standalone model)

---

## Key Features

### Authentication System
- Supports both password-based and Google OAuth authentication
- Email verification with expiring codes
- Tracks verification attempts for security

### Credit System
- Users start with 1 free credit
- Credits can be purchased through payments
- Credits are consumed for generation jobs

### Payment Integration
- Integrated with Paystack payment gateway
- Supports one-time credit purchases
- Supports recurring subscriptions
- Amounts stored in kobo (1/100 of Nigerian Naira)

### Project Management
- Users can organize generations into projects
- Projects store current generation parameters
- Supports multiple generations per project
- Cascade delete ensures data integrity

### Generation System
- Supports authenticated and anonymous generations
- Tracks job status through lifecycle
- Stores input parameters and output results
- Links to projects for organized workflow

### Moodboard Feature
- Creates design inspiration boards
- Stores items as JSON for flexibility
- Integrates with project workflow
- Handles generation status tracking
