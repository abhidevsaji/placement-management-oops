"""
URL map.  /api/...   -> Django REST API
          /admin/    -> Django's built-in admin site
          everything else -> the built React app (frontend/dist), so ONE server can run the whole system.
"""
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve

DIST = settings.BASE_DIR.parent / 'frontend' / 'dist'


def react_app(request, *args, **kwargs):
    index = DIST / 'index.html'
    if not index.exists():
        return HttpResponse('React build not found. Run "npm run build" in the frontend folder, '
                            'or use "npm run dev" and open http://localhost:5173', status=404)
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('placement.urls')),
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': DIST / 'assets'}),
    re_path(r'^(?!api/|admin/).*$', react_app),   # React Router handles /login, /jobs, ...
]
