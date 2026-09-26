"""
/ads.txt for Google AdSense.

Source of truth: frontend/public/ads.txt. Production routing (Render):
Cloudflare -> Render -> gunicorn -> Django. WhiteNoise only serves files
under /static/, and every other path goes to the frontend catch-all
(serve_frontend), which would answer /ads.txt with the Next.js 404 page -
so this route is registered BEFORE the catch-all in config/urls.py.

The file is read from the deployed build first (build.sh copies
frontend/out/* - including ads.txt - into STATIC_ROOT), and otherwise
straight from frontend/public/ads.txt in the deployed repository checkout,
so /ads.txt keeps working even if the copy step changes.

The AdSense Auto Ads script itself is loaded by the Next.js frontend
(components/AdSense.tsx) on public pages only.
"""

import os

from django.conf import settings
from django.http import HttpResponse

ADS_TXT_FILENAME = 'ads.txt'
# <repo>/frontend/public/ads.txt (BASE_DIR is <repo>/backend)
SOURCE_ADS_TXT = os.path.join(settings.BASE_DIR, os.pardir, 'frontend', 'public', ADS_TXT_FILENAME)


def ads_txt_candidates():
    return [os.path.join(str(settings.STATIC_ROOT), ADS_TXT_FILENAME), os.path.normpath(SOURCE_ADS_TXT)]


def ads_txt(request):
    for path in ads_txt_candidates():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read(), content_type='text/plain; charset=utf-8')
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError, PermissionError):
            continue
    return HttpResponse('Not found', status=404, content_type='text/plain; charset=utf-8')
