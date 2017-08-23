#!/bin/bash

echo Starting nginx
echo Starting gunicorn

exec gunicorn --workers 3 --bind unix:/rapidpro/rapidpro.sock temba.wsgi:application &
exec service nginx start
