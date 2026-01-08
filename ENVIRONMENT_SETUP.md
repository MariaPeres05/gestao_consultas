# Environment Variables Setup

## Overview
This project uses environment variables to manage sensitive configuration data like secret keys, database credentials, and debug settings.

## Initial Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Update `.env` with your configuration:**
   - Replace `your-secret-key-here` with a secure random key
   - Set `DEBUG=False` for production environments
   - Update `ALLOWED_HOSTS` with your domain names (comma-separated)
   - Configure database settings if using PostgreSQL

## Environment Variables

### Django Core Settings
- `SECRET_KEY` - Django secret key (required, keep this secret!)
- `DEBUG` - Debug mode (`True` or `False`, default: `False`)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts (e.g., `localhost,127.0.0.1,yourdomain.com`)

### Database Settings (SQLite - Default)
- `DB_ENGINE=django.db.backends.sqlite3`
- `DB_NAME=db.sqlite3`

### Database Settings (PostgreSQL)
To use PostgreSQL, update these in your `.env`:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password-here
DB_HOST=localhost
DB_PORT=5432
```

## Generating a New SECRET_KEY

To generate a secure random SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Security Notes

⚠️ **IMPORTANT:**
- Never commit the `.env` file to version control (it's in `.gitignore`)
- Always use `.env.example` as a template for other developers
- Use strong, unique SECRET_KEY values
- Set `DEBUG=False` in production
- Keep database passwords secure

## Production Deployment

For production:
1. Set `DEBUG=False`
2. Use a strong, unique `SECRET_KEY`
3. Configure `ALLOWED_HOSTS` with your domain
4. Use environment-specific database credentials
5. Consider using a secrets management service (AWS Secrets Manager, Azure Key Vault, etc.)
