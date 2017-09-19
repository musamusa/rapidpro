# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# -----------------------------------------------------------------------------------
# RapidPro settings file for the docker setup
# -----------------------------------------------------------------------------------

from getenv import env
import dj_database_url
import django_cache_url

from temba.settings_common import *  # noqa

DEBUG = env('DJANGO_DEBUG', 'off') == 'on'
IS_PROD = True

#DC ADDED
RAVEN_CONFIG = {'dsn': env('RAVEN_CONFIG_DSN', '')}

GEOS_LIBRARY_PATH = '/usr/local/lib/libgeos_c.so'
GDAL_LIBRARY_PATH = '/usr/local/lib/libgdal.so'

SECRET_KEY = env('SECRET_KEY', required=True)
DATABASE_URL = env('DATABASE_URL', required=True)
DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['ATOMIC_REQUESTS'] = True
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
REDIS_URL = env('REDIS_URL', required=True)
BROKER_URL = env('BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', REDIS_URL)
CACHE_URL = env('CACHE_URL', REDIS_URL)
CACHES = {'default': django_cache_url.parse(CACHE_URL)}
if CACHES['default']['BACKEND'] == 'django_redis.cache.RedisCache':
    if 'OPTIONS' not in CACHES['default']:
        CACHES['default']['OPTIONS'] = {}
    CACHES['default']['OPTIONS']['CLIENT_CLASS'] = 'django_redis.client.DefaultClient'

# -----------------------------------------------------------------------------------
# Used when creating callbacks for Twilio, Nexmo etc..
# -----------------------------------------------------------------------------------
HOSTNAME = env('DOMAIN_NAME', 'rapidpro.ngrok.com')
TEMBA_HOST = env('TEMBA_HOST', HOSTNAME)

INTERNAL_IPS = ('*',)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', HOSTNAME).split(';')

LOGGING['root']['level'] = env('DJANGO_LOG_LEVEL', 'INFO')

AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', '')
CDN_DOMAIN_NAME = env('CDN_DOMAIN_NAME', '')

# DC ADDED
AWS_BUCKET_DOMAIN = env('AWS_BUCKET_DOMAIN', '')

if AWS_STORAGE_BUCKET_NAME:
    # Tell django-storages that when coming up with the URL for an item in S3 storage, keep
    # it simple - just use this domain plus the path. (If this isn't set, things get complicated).
    # This controls how the `static` template tag from `staticfiles` gets expanded, if you're using it.
    # We also use it in the next setting.
    if CDN_DOMAIN_NAME:
        AWS_S3_CUSTOM_DOMAIN = CDN_DOMAIN_NAME
    else:
        AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

    # This is used by the `static` template tag from `static`, if you're using that. Or if anything else
    # refers directly to STATIC_URL. So it's safest to always set it.
    STATIC_URL = "https://%s/" % AWS_S3_CUSTOM_DOMAIN

    # Tell the staticfiles app to use S3Boto storage when writing the collected static files (when
    # you run `collectstatic`).
    STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    COMPRESS_STORAGE = STATICFILES_STORAGE
else:
    STATIC_URL = '/sitestatic/'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES) + ['whitenoise.middleware.WhiteNoiseMiddleware']

COMPRESS_ENABLED = env('DJANGO_COMPRESSOR', 'on') == 'on'
COMPRESS_OFFLINE = False

COMPRESS_URL = STATIC_URL
# Use MEDIA_ROOT rather than STATIC_ROOT because it already exists and is
# writable on the server. It's also the directory where other cached files
# (e.g., translations) are stored
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_HASHING_METHOD = 'content'
COMPRESS_OFFLINE_MANIFEST = 'manifest-%s.json' % env('RAPIDPRO_VERSION', required=True)

MAGE_AUTH_TOKEN = env('MAGE_AUTH_TOKEN', None)
MAGE_API_URL = env('MAGE_API_URL', 'http://localhost:8026/api/v1')
SEND_MESSAGES = env('SEND_MESSAGES', 'off') == 'on'
SEND_WEBHOOKS = env('SEND_WEBHOOKS', 'off') == 'on'
SEND_EMAILS = env('SEND_EMAILS', 'off') == 'on'
SEND_AIRTIME = env('SEND_AIRTIME', 'off') == 'on'
SEND_CALLS = env('SEND_CALLS', 'off') == 'on'
IP_ADDRESSES = tuple(filter(None, env('IP_ADDRESSES', '').split(',')))

CELERY_ALWAYS_EAGER = False
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
BROKER_BACKEND = 'redis'

EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', 'server@temba.io')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'server@temba.io')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', 'mypassword')
EMAIL_USE_TLS = env('EMAIL_USE_TLS', 'on') == 'on'
SECURE_PROXY_SSL_HEADER = (
    env('SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO'), 'https')


BRANDING['rapidpro.io']['description'] = 'Unlocking Insights and Engagement.'
BRANDING['rapidpro.io']['name'] = 'Community Connect'
BRANDING['rapidpro.io']['credits'] = 'Copyright &copy; 2017. Community Connect.'
BRANDING['rapidpro.io']['welcome_packs'] = [dict(size=500, name="Trial"),
                                            dict(size=2500, name="Bronze"),
                                            dict(size=30000, name="Silver"),
                                            dict(size=100000, name="Gold")]
BRANDING['rapidpro.io']['favico'] = 'brands/rapidpro/icon.png'
BRANDING['rapidpro.io']['colors'] = dict(primary='#569D9B')
BRANDING['rapidpro.io']['org'] = 'GreatNonProfits'
BRANDING['rapidpro.io']['email'] = 'support@communityconnectlabs.com'
BRANDING['rapidpro.io']['support_email'] = 'support@communityconnectlabs.com'
BRANDING['rapidpro.io']['link'] = 'https://hs.communityconnectlabs.com'
BRANDING['rapidpro.io']['domain'] = 'hs.communityconnectlabs.com'
BRANDING['rapidpro.io']['api_link'] = 'https://hs.communityconnectlabs.com'
BRANDING['rapidpro.io']['android_surveyor'] = 'io.rapidpro.surveyor'
