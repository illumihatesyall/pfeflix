web: python manage.py migrate --noinput && python manage.py import_content && python manage.py collectstatic --noinput && gunicorn PFE.wsgi --log-file -
release: python manage.py migrate --noinput && python manage.py import_content
