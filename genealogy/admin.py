from django.contrib import admin
from .models import (
    Person, Partnership, ParentChild, ModificationProposal,
    FamilyEvent, Document, AuditLog
)

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Admin interface for Person model - UPDATED WITH TRIBUS AND CLAN"""
    
    list_display = [
        'get_full_name', 'gender', 'tribus', 'clan', 'birth_date', 'death_date',
        'is_deceased', 'visibility', 'created_by', 'created_at'
    ]
    list_filter = [
        'gender', 'tribus', 'clan', 'is_deceased', 'visibility', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'maiden_name', 'tribus', 'clan', 
        'birth_place', 'death_place'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': (
                'first_name', 'last_name', 'maiden_name', 'gender'
            )
        }),
        ('Identification tribale et clanique', {  # NOUVELLE SECTION
            'fields': (
                'tribus', 'clan'
            ),
            'description': 'Informations sur l\'appartenance tribale et clanique'
        }),
        ('Dates et lieux', {
            'fields': (
                'birth_date', 'birth_place', 'death_date', 'death_place', 'is_deceased'
            )
        }),
        ('Informations additionnelles', {
            'fields': (
                'biography', 'profession', 'education', 'photo'
            ),
            'classes': ('collapse',)
        }),
        ('Système', {
            'fields': (
                'created_by', 'owned_by', 'user_account', 'visibility',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )

    # Permettre le filtrage par tribu et clan dans la liste
    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        
        # Ajouter des filtres dynamiques pour les tribus et clans existants
        if Person.objects.filter(tribus__isnull=False).exists():
            list_filter.insert(2, 'tribus')
        if Person.objects.filter(clan__isnull=False).exists():
            list_filter.insert(3, 'clan')
            
        return list_filter


@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    """Admin interface for Partnership model"""
    
    list_display = [
        '__str__', 'partnership_type', 'start_date', 'end_date', 'status', 'created_at'
    ]
    list_filter = ['partnership_type', 'status', 'created_at']
    search_fields = [
        'person1__first_name', 'person1__last_name',
        'person2__first_name', 'person2__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Partenaires', {
            'fields': ('person1', 'person2')
        }),
        ('Détails de l\'union', {
            'fields': ('partnership_type', 'start_date', 'end_date', 'location')
        }),
        ('Statut', {
            'fields': ('status', 'notes')
        }),
        ('Système', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ParentChild)
class ParentChildAdmin(admin.ModelAdmin):
    """Admin interface for ParentChild model"""
    
    list_display = [
        '__str__', 'relationship_type', 'status', 'created_at'
    ]
    list_filter = ['relationship_type', 'status', 'created_at']
    search_fields = [
        'parent__first_name', 'parent__last_name',
        'child__first_name', 'child__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ModificationProposal)
class ModificationProposalAdmin(admin.ModelAdmin):
    """Admin interface for ModificationProposal model"""
    
    list_display = [
        'person', 'field_name', 'proposed_by', 'status', 'created_at'
    ]
    list_filter = ['status', 'field_name', 'created_at']
    search_fields = [
        'person__first_name', 'person__last_name',
        'proposed_by__first_name', 'proposed_by__last_name'
    ]
    readonly_fields = ['created_at', 'reviewed_at']
    
    fieldsets = (
        ('Proposition', {
            'fields': ('person', 'field_name', 'old_value', 'new_value', 'justification')
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'review_notes')
        }),
        ('Système', {
            'fields': ('proposed_by', 'created_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FamilyEvent)
class FamilyEventAdmin(admin.ModelAdmin):
    """Admin interface for FamilyEvent model"""
    
    list_display = ['title', 'event_type', 'date', 'location', 'created_at']
    list_filter = ['event_type', 'date', 'created_at']
    search_fields = ['title', 'description', 'location']
    filter_horizontal = ['people']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model"""
    
    list_display = ['title', 'document_type', 'uploaded_by', 'upload_date']
    list_filter = ['document_type', 'upload_date']
    search_fields = ['title', 'description']
    filter_horizontal = ['people']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model"""
    
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'timestamp', 'ip_address']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False