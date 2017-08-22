#!/bin/bash
set -e

case $1 in
 runserver)
  cd /rapidpro; gunicorn --bind 0.0.0.0:8000 temba.wsgi:application
  ;;
 gunicorn)
  service gunicorn start; service ngnix restart
  ;;
esac

exec "$@"