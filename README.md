### Important Host Machine Must install

`wkhtmltopdf` in order to use Generate Documents and other stuff.


## Demo mode (uv)

A dedicated demo branch exists with auto-seeded demo data and automatic reset on logout.

Run locally with uv:

1. Checkout the demo branch
   - `git checkout demo`
2. Sync dependencies
   - `uv sync`
3. Create an .env file with at least:
   - `SECRET_KEY=dev-secret`
   - `DEBUG=true`
   - `DEMO_MODE=true`
4. Apply migrations to the demo database
   - `uv run python manage.py migrate`
5. Seed demo data (optional, also runs on first login)
   - `uv run python manage.py demo_seed --reset`
6. Start the server
   - `uv run python manage.py runserver`

Demo users:
- Admin: demo_admin / demo1234
- Teacher: demo_teacher / demo1234
- Student: demo_student / demo1234

Behavior in demo mode:
- On login: demo dataset is (re)seeded to a known baseline.
- On logout: data resets back to the default demo dataset.
