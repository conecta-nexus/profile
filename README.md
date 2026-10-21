# profile
Conecta Nexus - Profile Microservice
===================================

Purpose
-------

The Profile microservice manages:

- Student academic profiles.
- Company corporate profiles.
- Law 1581 of 2012 Habeas Data consent records.
- Restricted public profile views without private contact information.

The service exposes create, read, and partial-update operations. Profile
deletion is not currently exposed by the API.


Technologies
------------

- Python 3.12 or newer.
- Django 6.1.2 or newer.
- Django REST Framework 3.18.3 or newer.
- PostgreSQL 16.
- psycopg 3 with the binary PostgreSQL driver.
- PyJWT with cryptography support for RS256 authentication.
- uv for dependency and virtual-environment management.
- pytest, pytest-django, and pytest-cov for automated testing.
- Podman or Docker for the local PostgreSQL container.


Project Structure
-----------------

apps/core       Shared authentication, permissions, exceptions, and routing.
apps/consents   Law 1581 consent registration and status queries.
apps/students   Student profile model, serializers, endpoints, and tests.
apps/companies  Company profile model, serializers, endpoints, and tests.
config          Django settings and root URL configuration.


Prerequisites
-------------

Install the following tools before running the project:

- Python >= 3.12
- uv
- Podman or Docker
- PostgreSQL client tools are optional but useful for diagnostics


Local Environment
-----------------

1. Install the project dependencies.

   # Create or synchronize the virtual environment from uv.lock.
   uv sync

2. Create the local environment file.

   # Copy the public template; .env is ignored by Git.
   cp .env.example .env

3. Configure at least these values in .env. Never commit real secrets.

   DJANGO_SECRET_KEY=replace-with-a-local-random-secret
   DJANGO_DEBUG=true
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

   POSTGRES_DB=db_profiles
   POSTGRES_USER=profile_user
   POSTGRES_PASSWORD=replace-with-a-local-password
   POSTGRES_HOST=127.0.0.1
   POSTGRES_PORT=5433
   POSTGRES_CONN_MAX_AGE=60

   JWT_PUBLIC_KEY_PATH=certs/jwt_public.pem
   JWT_ISSUER=https://auth.conectanexus.ufps.edu.co
   JWT_AUDIENCE=conecta-nexus-services

DATABASE_URL can be used instead of the individual PostgreSQL variables.


PostgreSQL 16 with Podman
-------------------------

Create the local database container once:

   # Run PostgreSQL 16 on host port 5433 without exposing it externally.
   podman run --name profile-postgres-16 \
     --restart=unless-stopped \
     -e POSTGRES_DB=db_profiles \
     -e POSTGRES_USER=profile_user \
     -e POSTGRES_PASSWORD=replace-with-the-value-from-env \
     -p 127.0.0.1:5433:5432 \
     -v profile-postgres-16-data:/var/lib/postgresql/data \
     --health-cmd="pg_isready -U profile_user -d db_profiles" \
     --health-interval=5s \
     --health-timeout=5s \
     --health-retries=10 \
     -d docker.io/library/postgres:16

For later executions, start the existing container:

   # Start the previously created PostgreSQL container.
   podman start profile-postgres-16

Confirm that PostgreSQL is healthy:

   # The expected result is: running / healthy.
   podman inspect \
     --format '{{.State.Status}} / {{.State.Health.Status}}' \
     profile-postgres-16

The PostgreSQL password in the container must match POSTGRES_PASSWORD in .env.


JWT Configuration
-----------------

All API endpoints require an RS256 access token issued by the Auth
microservice. Send the token using this header:

   Authorization: Bearer <access-token>

Profile verifies tokens with the Auth public key. Place only the public key at
certs/jwt_public.pem or configure JWT_PUBLIC_KEY_PATH/JWT_PUBLIC_KEY. Never copy
or commit the Auth private key into this repository.

For isolated local development only, the repository includes a key-generation
script. The generated files are ignored by Git:

   # Generate a development-only RS256 key pair under certs/.
   uv run python scripts/generate_keys.py

A token used against the API must be signed by the private key corresponding to
the configured public key and must contain valid iss, aud, sub, exp, role,
is_active, type, and scope claims.


Database Initialization
-----------------------

Run the database migrations and Django validation:

   # Apply migrations and verify the Django configuration.
   uv run python manage.py migrate
   uv run python manage.py check


Run the Service
---------------

Start the development server:

   # Expose the Profile API locally on port 8000.
   uv run python manage.py runserver 0.0.0.0:8000

Base URL:

   http://127.0.0.1:8000/api/v1/profiles


API Endpoints
-------------

Consent

POST /api/v1/profiles/consent
  Purpose: Register explicit Law 1581 consent.
  Role: Any authenticated active user.
  Required scope: consent:write
  Success: 201 Created
  Body:

    {
      "is_accepted": true,
      "policy_version": "v1.0-2026"
    }

GET /api/v1/profiles/consent/me
  Purpose: Return the authenticated user's latest consent record.
  Role: Any authenticated active user.
  Required scope: consent:read
  Success: 200 OK


Student Profiles

POST /api/v1/profiles/students/me
  Purpose: Create the authenticated student's initial profile.
  Role: STUDENT
  Required scope: profile:student:write
  Additional requirement: Previously accepted consent.
  Success: 201 Created
  Body:

    {
      "full_name": "Ada Lovelace",
      "student_code": "1152375",
      "academic_program": "Ingenieria de Sistemas",
      "current_semester": 8,
      "completed_courses": ["Databases", "Software Engineering"],
      "technical_skills": ["Python", "Django"],
      "interest_areas": ["Backend", "Cloud"],
      "bio": "Backend development student.",
      "contact_email": "student@example.com",
      "contact_phone": "+57 3000000000"
    }

  Notes:
  - current_semester must be between 6 and 10.
  - user_id is obtained from the authenticated JWT and must not be submitted.
  - Only one student profile is allowed per user.

GET /api/v1/profiles/students/me
  Purpose: Return the owner's complete private student profile.
  Role: STUDENT
  Required scope: profile:student:read
  Success: 200 OK

PATCH /api/v1/profiles/students/me
  Purpose: Partially update the authenticated student's profile.
  Role: STUDENT
  Required scope: profile:student:write
  Additional requirement: Previously accepted consent.
  Success: 200 OK
  Mutable fields:
  - current_semester
  - completed_courses
  - technical_skills
  - interest_areas
  - bio
  Immutable fields include student_code and academic_program.

GET /api/v1/profiles/students/{user_id}/public
  Purpose: Return a restricted student profile without contact fields.
  Role: COMPANY
  Required scope: profile:student:read_public
  Success: 200 OK


Company Profiles

POST /api/v1/profiles/companies/me
  Purpose: Create the authenticated company's initial profile.
  Role: COMPANY
  Required scope: profile:company:write
  Additional requirement: Previously accepted consent.
  Success: 201 Created
  Body:

    {
      "nit": "900123456-8",
      "business_name": "Example Company SAS",
      "economic_sector": "Technology",
      "description": "Software services company.",
      "website_url": "https://example.com",
      "public_links": ["https://www.linkedin.com/company/example"],
      "contact_name": "Grace Hopper",
      "contact_email": "contact@example.com",
      "contact_phone": "+57 3000000000"
    }

  Notes:
  - nit must use the Colombian NIT format and a valid verification digit.
  - user_id is obtained from the authenticated JWT and must not be submitted.
  - Only one company profile is allowed per user.

GET /api/v1/profiles/companies/me
  Purpose: Return the owner's complete private company profile.
  Role: COMPANY
  Required scope: profile:company:read
  Success: 200 OK

PATCH /api/v1/profiles/companies/me
  Purpose: Partially update the authenticated company's profile.
  Role: COMPANY
  Required scope: profile:company:write
  Additional requirement: Previously accepted consent.
  Success: 200 OK
  Mutable fields:
  - economic_sector
  - description
  - website_url
  - public_links
  - contact_name
  - contact_email
  - contact_phone
  The NIT is immutable.

GET /api/v1/profiles/companies/{user_id}/public
  Purpose: Return a restricted company profile without contact fields.
  Role: STUDENT
  Required scope: profile:company:read_public
  Success: 200 OK


Common HTTP Responses
---------------------

200 OK             Successful query or partial update.
201 Created        Profile or consent created successfully.
400 Bad Request    Invalid payload, duplicate profile, or immutable field.
401 Unauthorized   Missing, invalid, or expired access token.
403 Forbidden      Incorrect role, missing scope, or missing consent.
404 Not Found      Requested profile or consent record does not exist.

Errors use the following standard structure:

  {
    "error": {
      "status": 400,
      "code": "validation_error",
      "message": "Request validation failed.",
      "details": {}
    }
  }


Tests and Complete Validation
-----------------------------

Run the complete validation before committing or opening a pull request:

   # Validate configuration, migrations, tests, coverage, and the Git diff.
   uv run python manage.py check
   uv run python manage.py makemigrations --check --dry-run
   uv run python manage.py migrate --check
   uv run pytest \
     --cov=apps \
     --cov=config \
     --cov-report=term-missing \
     --cov-fail-under=80 \
     -rs
   git diff --check
   git status --short

The optional Auth integration test is skipped when the sibling Auth repository
and its development test key are unavailable. This skip does not affect the
unit and endpoint test suites. Never add a real private key to make it run.
