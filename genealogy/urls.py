from django.urls import path
from . import views

app_name = 'genealogy'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # Main views
    path('tree/', views.family_tree_view, name='family_tree'),
    path('tree/<int:person_id>/', views.family_tree_view, name='family_tree_person'),
    path('search/', views.search_people, name='search'),
    
    # Person management
    path('person/create/', views.person_create, name='person_create'),
    path('person/<int:person_id>/', views.person_detail, name='person_detail'),
    path('person/<int:person_id>/edit/', views.person_edit, name='person_edit'),
    path('person/<int:person_id>/delete/', views.person_delete, name='person_delete'),
    path('person/<int:person_id>/add-partnership/', views.add_partnership, name='add_partnership'),
    path('person/<int:person_id>/add-child/', views.add_child, name='add_child'),
    path('person/<int:person_id>/propose-modification/', views.propose_modification, name='propose_modification'),
    
    # Modification proposals
    path('proposal/<int:proposal_id>/review/', views.review_proposal, name='review_proposal'),
    
    # Admin views - User management
    path('manage-users/', views.manage_users, name='manage_users'),
    path('manage-users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('manage-users/<int:user_id>/toggle/', views.toggle_user, name='toggle_user'),
    path('manage-users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('audit-log/', views.audit_log, name='audit_log'),
    
    # Export
    path('export/gedcom/', views.export_gedcom, name='export_gedcom'),
    
    # API endpoints
    path('api/person-search/', views.api_person_search, name='api_person_search'),
    path('api/tree-data/<int:person_id>/', views.api_family_tree_data, name='api_family_tree_data'),
]