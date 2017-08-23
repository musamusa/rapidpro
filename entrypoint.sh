#!/bin/bash
set -e

case $1 in
 runserver)
  cd /rapidpro; exec gunicorn --workers 3 --bind 0.0.0.0:8000 temba.wsgi:application
  ;;
 gunicorn)
  exec gunicorn --workers 3 --bind unix:/rapidpro/rapidpro.sock temba.wsgi:application; exec service nginx start
  ;;
esac

exec "$@"
