# Django settings for lts_web project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'lts'             # Or path to database file if using sqlite3.
DATABASE_USER = 'lts'             # Not used with sqlite3.
DATABASE_PASSWORD = 'password'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago' #@UnusedVariable

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'i7*je=%9*8c(-*v0=ct$b3p=6o(p+gr&9dh6kdc9b52p1hl**#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'lts',
    'django.contrib.admin',
    'django_future',
)

LTS_SCHEDULE = {
    'crawl': '5m',
    'img_upload': '5m',
    'rating': '5m',
    'blog': '15m',
    'tweet': '12m',
    'cluster': '5m',
    'clear_cache': '1h',
    'update_twitter_accounts': '1d',
    'update_twitter_users': '6h',
    'follow_users': '1d',
    'update_tweet_mentioned': '1d',
}

import os, sys, logging.config
LOGGING_CONFIG = os.path.join(os.path.dirname(__file__), 'logging.conf')
LTS_CONFIG = os.path.join(os.path.dirname(__file__), 'lts.cfg')
SHOT_DAEMON = True
SHOT_DAEMON_PIDFILE = '/var/log/shot_daemon.pid'
SHOT_DAEMON_STDOUT = None
SHOT_DAEMON_STDERR = None
SHOT_CACHE_PATH = MEDIA_ROOT

try:
    from local_settings import * #@UnusedWildImport
except ImportError:
    pass

logging.config.fileConfig(LOGGING_CONFIG)

# walk around encoding issue
reload(sys)
sys.setdefaultencoding('utf-8') #@UndefinedVariable
