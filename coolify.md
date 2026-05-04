# Coolify Deployment

1. Create a new Docker Compose application in Coolify.
2. Point the repository root to this project.
3. Add the variables from `.env.example` in Coolify's environment editor.
4. Set public domains:
   - `web`: your dashboard/docs domain.
   - `api`: your API domain.
5. Configure Stripe webhook URL:
   - `https://YOUR_API_DOMAIN/v1/billing/stripe/webhook`
6. Deploy.

The API container runs schema creation on startup for the first version. Replace
that with Alembic migrations before a production data migration workflow is
needed.
