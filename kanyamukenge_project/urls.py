from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import HttpResponse
from django.views.decorators.http import require_GET

# ======================================================================
# robots.txt view
# ======================================================================
@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /media/",
        "Disallow: /dashboard/",
        "Disallow: /genealogy/",
        "",
        "# Plateforme privée - Famille KANYAMUKENGE",
        "# Accès restreint aux membres de la famille uniquement",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

# ======================================================================
# URL patterns
# ======================================================================
urlpatterns = [
    # ----------------------------
    # Admin
    # ----------------------------
    path(settings.ADMIN_URL, admin.site.urls),
    path('admin/', RedirectView.as_view(url='/' + settings.ADMIN_URL, permanent=True)),

    # ----------------------------
    # Main app: genealogy
    # ----------------------------
    path('', include('genealogy.urls')),  # Home, dashboard, tree, search, etc.

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
# Serve media and static files in development
# ======================================================================
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# ======================================================================
# Custom error handlers
# ======================================================================
handler403 = 'genealogy.views.permission_denied_view'
handler404 = 'genealogy.views.page_not_found_view'
handler500 = 'genealogy.views.server_error_view'

# ======================================================================
# Django admin customization
# ======================================================================
admin.site.site_header = "Administration - Famille KANYAMUKENGE"
admin.site.site_title = "Famille KANYAMUKENGE"
admin.site.index_title = "Gestion de la plateforme généalogique"
admin.site.site_url = "/"
admin.site.site_header_template = None
admin.site.login_template = None
