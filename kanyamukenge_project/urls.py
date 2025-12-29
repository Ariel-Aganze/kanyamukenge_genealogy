"""
URL configuration for kanyamukenge_project project.
CORRECTED VERSION - Fixes static file serving conflicts with WhiteNoise

Key fixes:
1. Removed conflicting static file serving that interferes with WhiteNoise
2. Simplified static file handling
3. Proper media file serving for all environments
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os

# Custom error view imports
from kanyamukenge_project import views

# ======================================================================
# Robots.txt view
# ======================================================================
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

# ======================================================================
# Main URL patterns
# ======================================================================

urlpatterns = [
    # ----------------------------
    # Admin
    # ----------------------------
    path(f'{settings.ADMIN_URL}', admin.site.urls),

    # ----------------------------
    # Main app
    # ----------------------------
    path('', include('genealogy.urls')),

    # ----------------------------
    # Accounts
    # ----------------------------
    path('accounts/', include('accounts.urls')),

    # ----------------------------
    # Shortcuts / redirects
    # ----------------------------
    path('tree/', RedirectView.as_view(pattern_name='genealogy:family_tree', permanent=False)),
    path('tree/<int:person_id>/', RedirectView.as_view(pattern_name='genealogy:family_tree_person', permanent=False)),
    path('search/', RedirectView.as_view(pattern_name='genealogy:search', permanent=False)),

    # ----------------------------
    # Utilities
    # ----------------------------
    path('robots.txt', robots_txt),
    path('health/', lambda request: HttpResponse('OK', content_type='text/plain')),
]

# ======================================================================
# Media files serving - ALWAYS needed for file uploads
# ======================================================================

# Always serve media files (user uploads)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ======================================================================
# Static files serving - SIMPLIFIED for WhiteNoise compatibility
# ======================================================================

# WhiteNoise handles static files automatically in production
# Only add manual serving for development if absolutely necessary
if settings.DEBUG:
    # In development, Django's runserver handles static files automatically
    # WhiteNoise with WHITENOISE_USE_FINDERS=True also handles this
    # No manual static file serving needed - WhiteNoise handles it
    pass

# ======================================================================
# Development tools
# ======================================================================

if settings.DEBUG:
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        try:
            import debug_toolbar
            urlpatterns = [
                path('__debug__/', include(debug_toolbar.urls)),
            ] + urlpatterns
        except ImportError:
            pass

# ======================================================================
# Custom error handlers
# ======================================================================

handler400 = 'kanyamukenge_project.views.custom_400_view'
handler403 = 'kanyamukenge_project.views.custom_403_view'
handler404 = 'kanyamukenge_project.views.custom_404_view'
handler500 = 'kanyamukenge_project.views.custom_500_view'

# ======================================================================
# Django admin customization
# ======================================================================

admin.site.site_header = "Administration - Famille KANYAMUKENGE"
admin.site.site_title = "Famille KANYAMUKENGE"
admin.site.index_title = "Gestion de la plateforme généalogique"
admin.site.site_url = "/"
admin.site.site_header_template = None
admin.site.login_template = None