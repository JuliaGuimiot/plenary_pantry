# Plenary Pantry

A Django web application for managing pantry inventory and meal planning.

## Features

- Django 5.2.5 with Python 3.12
- PostgreSQL database
- UV package manager for dependency management
- Environment-based configuration

## Prerequisites

- Python 3.12+
- UV package manager
- PostgreSQL database server

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd plenary_pantry
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up PostgreSQL database**
   - Create a PostgreSQL database named `plenary_pantry_db`
   - Update the `.env` file with your database credentials

4. **Run migrations**
   ```bash
   uv run python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   uv run python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   uv run python manage.py runserver
   ```

   The application will be available at http://127.0.0.1:8000/

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Settings
DB_NAME=plenary_pantry_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

## Development

- **Run tests**: `uv run python manage.py test`
- **Create migrations**: `uv run python manage.py makemigrations`
- **Apply migrations**: `uv run python manage.py migrate`
- **Collect static files**: `uv run python manage.py collectstatic`

## Project Structure

```
plenary_pantry/
├── plenary_pantry/          # Django project settings
│   ├── settings.py         # Project settings
│   ├── urls.py            # Main URL configuration
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
├── manage.py              # Django management script
├── pyproject.toml         # UV project configuration
├── .env                   # Environment variables
└── README.md             # This file
```
