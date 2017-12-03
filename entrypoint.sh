#!/bin/bash

echo Starting gunicorn
gunicorn --workers 3 --bind unix:/rapidpro/rapidpro.sock temba.wsgi:application &

echo Starting celery worker
celery worker -A temba -B -Q celery,handler,flows,msgs -n rapidpro.celery -l info &

echo Starting nginx
service nginx start
