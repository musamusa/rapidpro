#!/bin/bash

echo Starting nginx
echo Starting gunicorn

exec gunicorn --workers 3 --bind unix:/rapidpro/rapidpro.sock temba.wsgi:application &
exec celery worker -A temba -B -Q celery,handler,flows,msgs -n rapidpro.celery -l info &
exec service nginx start
