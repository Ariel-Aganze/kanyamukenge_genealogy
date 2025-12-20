from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Min
from django.db import models
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.conf import settings
import json
from django.core.exceptions import ValidationError

from .models import (
    Person, Partnership, ParentChild, ModificationProposal,
    FamilyEvent, Document, AuditLog
)
from .forms import (
    PersonForm, PartnershipForm, ParentChildForm,
    ModificationProposalForm, FamilyEventForm, DocumentForm, SearchForm
)
from .utils import create_audit_log, generate_gedcom_export

User = get_user_model()

def home(request):
    """Public home page showing family tree overview"""

    # Redirect logged-in users to dashboard
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    # Public family members
    public_people = Person.objects.filter(
        visibility='public'
    ).order_by('last_name')

    # Statistics
    total_people = Person.objects.count()
    generations = Person.objects.aggregate(
        oldest_birth=models.Min('birth_date'),
        newest_birth=models.Max('birth_date')
    )

    context = {
        'public_people': public_people[:10],  # Show first 10
        'total_people': total_people,
        'generations': generations,
    }

    return render(request, 'genealogy/home.html', context)


@login_required
def dashboard(request):
    """Main dashboard for authenticated users"""
    user = request.user
    
    # Recent activities
    recent_people = Person.objects.filter(
        models.Q(created_by=user) | models.Q(owned_by=user)
    ).order_by('-created_at')[:5]
    
    # Pending proposals for review (admin only)
    pending_proposals = []
    if user.role == 'admin':
        pending_proposals = ModificationProposal.objects.filter(
            status='pending'
        ).order_by('-created_at')[:5]
    
    # User's family statistics
    user_people_count = Person.objects.filter(
        models.Q(created_by=user) | models.Q(owned_by=user)
    ).count()
    
    # Recent family events
    recent_events = FamilyEvent.objects.all().order_by('-date', '-created_at')[:5]
    
    context = {
        'recent_people': recent_people,
        'pending_proposals': pending_proposals,
        'user_people_count': user_people_count,
        'recent_events': recent_events,
        'total_people': Person.objects.count(),
        'total_generations': Person.objects.aggregate(
            count=Count('birth_date__year', distinct=True)
        )['count'] or 0,
    }
    
    return render(request, 'genealogy/dashboard.html', context)


def family_tree_view(request, person_id=None):
    """Interactive family tree view"""
    if person_id:
        center_person = get_object_or_404(Person, id=person_id)
    else:
        # Default to oldest person or first person
        center_person = Person.objects.filter(birth_date__isnull=False).order_by('birth_date').first()
        if not center_person:
            center_person = Person.objects.first()
    
    if not center_person:
        messages.info(request, "Aucune personne n'est encore enregistrée dans l'arbre familial.")
        return redirect('dashboard' if request.user.is_authenticated else 'home')
    
    # Get family tree data for the center person
    tree_data = get_family_tree_data(center_person, request.user)
    
    context = {
        'center_person': center_person,
        'tree_data': json.dumps(tree_data),
        'all_people': Person.objects.all().order_by('last_name', 'first_name'),
    }
    
    return render(request, 'genealogy/family_tree.html', context)


@login_required
def person_detail(request, person_id):
    """Detailed view of a person"""
    person = get_object_or_404(Person, id=person_id)
    
    # Check visibility permissions
    if not can_view_person(request.user, person):
        messages.error(request, "Vous n'avez pas l'autorisation de voir cette personne.")
        return redirect('genealogy:dashboard')
    
    # Get related information
    parents = person.get_parents()
    children = person.get_children()
    partners = person.get_partners()
    siblings = person.get_siblings()
    
    # Get documents and events
    documents = person.documents.all()
    events = person.events.all().order_by('-date')
    
    # Get modification proposals for this person
    proposals = ModificationProposal.objects.filter(
        person=person
    ).order_by('-created_at')
    
    context = {
        'person': person,
        'parents': parents,
        'children': children,
        'partners': partners,
        'siblings': siblings,
        'documents': documents,
        'events': events,
        'proposals': proposals,
        'can_modify': person.can_be_modified_by(request.user),
    }
    
    return render(request, 'genealogy/person_detail.html', context)


@login_required
def person_create(request):
    """Create a new person"""
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            person = form.save(commit=False)
            person.created_by = request.user
            person.owned_by = request.user
            person.save()
            
            create_audit_log(
                user=request.user,
                action='create',
                model_name='Person',
                object_id=person.id,
                changes=form.cleaned_data,
                request=request
            )
            
            messages.success(request, f'Personne {person.get_full_name()} créée avec succès.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = PersonForm()
    
    return render(request, 'genealogy/person_form.html', {
        'form': form,
        'title': 'Ajouter une personne'
    })


@login_required
def person_edit(request, person_id):
    """Edit a person's information"""
    person = get_object_or_404(Person, id=person_id)
    
    if not person.can_be_modified_by(request.user):
        messages.error(request, "Vous n'avez pas l'autorisation de modifier cette personne.")
        return redirect('genealogy:person_detail', person_id=person.id)
    
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            # Store old values for audit
            old_values = {}
            for field in form.changed_data:
                old_values[field] = getattr(person, field)
            
            form.save()
            
            create_audit_log(
                user=request.user,
                action='update',
                model_name='Person',
                object_id=person.id,
                changes={'old': old_values, 'new': form.cleaned_data},
                request=request
            )
            
            messages.success(request, f'Informations de {person.get_full_name()} mises à jour.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = PersonForm(instance=person)
    
    return render(request, 'genealogy/person_form.html', {
        'form': form,
        'person': person,
        'title': f'Modifier {person.get_full_name()}'
    })

@login_required
@require_POST
def person_delete(request, person_id):
    """Supprimer une personne (admin seulement ou propriétaire)"""
    person = get_object_or_404(Person, id=person_id)
    
    # Vérifier les permissions
    can_delete = False
    if request.user.role == 'admin':
        can_delete = True
    elif hasattr(person, 'owned_by') and person.owned_by == request.user:
        can_delete = True
    
    if not can_delete:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer cette personne.")
        return redirect('genealogy:person_detail', person_id=person.id)
    
    # Sauvegarder le nom pour le message
    person_name = person.get_full_name()
    
    # Supprimer la personne
    person.delete()
    
    messages.success(request, f"{person_name} a été supprimé(e) avec succès.")
    return redirect('genealogy:search')

@login_required
def add_partnership(request, person_id):
    """Add a partnership/marriage for a person"""
    person = get_object_or_404(Person, id=person_id)
    
    if request.method == 'POST':
        form = PartnershipForm(request.POST, person1=person)
        if form.is_valid():
            partnership = form.save(commit=False)
            partnership.person1 = person
            partnership.created_by = request.user
            partnership.save()  # ✅ Maintenant ça marche !
            
            messages.success(request, f'Union créée avec succès.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = PartnershipForm(person1=person)
    
    return render(request, 'genealogy/partnership_form.html', {
        'form': form,
        'person': person,
    })

@login_required
def add_child(request, person_id):
    """Add a child for a person"""
    parent = get_object_or_404(Person, id=person_id)

    if not parent.can_be_modified_by(request.user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier cette personne."
        )
        return redirect('genealogy:person_detail', person_id=parent.id)

    if request.method == 'POST':
        form = ParentChildForm(request.POST, parent=parent)

        if form.is_valid():
            parent_child = form.save(commit=False)

            # SET REQUIRED FIELDS BEFORE VALIDATION
            parent_child.parent = parent
            parent_child.created_by = request.user

            try:
                parent_child.full_clean()
                parent_child.save()

                create_audit_log(
                    user=request.user,
                    action='create',
                    model_name='ParentChild',
                    object_id=parent_child.id,
                    changes=form.cleaned_data,
                    request=request
                )

                messages.success(request, "Enfant ajouté avec succès.")
                return redirect('genealogy:person_detail', person_id=parent.id)

            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, error_list in e.message_dict.items():  # ✅ FIX
                        for error in error_list:
                            form.add_error(field, error)
                else:
                    form.add_error(None, e.message)

    else:
        form = ParentChildForm(parent=parent)

    return render(
        request,
        'genealogy/parent_child_form.html',
        {
            'form': form,
            'parent': parent,
            'title': f'Ajouter un enfant pour {parent.get_full_name()}',
        }
    )


@login_required
def propose_modification(request, person_id):
    """Propose a modification for a person's data"""
    person = get_object_or_404(Person, id=person_id)
    
    if request.method == 'POST':
        form = ModificationProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.person = person
            proposal.proposed_by = request.user
            
            # Get current value
            current_value = getattr(person, proposal.field_name, '')
            proposal.old_value = str(current_value) if current_value else ''
            
            proposal.save()
            
            create_audit_log(
                user=request.user,
                action='create',
                model_name='ModificationProposal',
                object_id=proposal.id,
                changes=form.cleaned_data,
                request=request
            )
            
            messages.success(request, 'Proposition de modification envoyée.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = ModificationProposalForm()
    
    return render(request, 'genealogy/modification_proposal_form.html', {
        'form': form,
        'person': person,
        'title': f'Proposer une modification pour {person.get_full_name()}'
    })


@login_required
def review_proposal(request, proposal_id):
    """Review a modification proposal (admin only)"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent examiner les propositions.")
        return redirect('genealogy:dashboard')
    
    proposal = get_object_or_404(ModificationProposal, id=proposal_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        review_notes = request.POST.get('review_notes', '')
        
        if action == 'approve':
            # Apply the modification
            setattr(proposal.person, proposal.field_name, proposal.new_value)
            proposal.person.save()
            
            proposal.status = 'approved'
            proposal.reviewed_by = request.user
            proposal.reviewed_at = timezone.now()
            proposal.review_notes = review_notes
            proposal.save()
            
            create_audit_log(
                user=request.user,
                action='approve',
                model_name='ModificationProposal',
                object_id=proposal.id,
                changes={'action': 'approved', 'notes': review_notes},
                request=request
            )
            
            messages.success(request, 'Proposition approuvée et appliquée.')
        
        elif action == 'reject':
            proposal.status = 'rejected'
            proposal.reviewed_by = request.user
            proposal.reviewed_at = timezone.now()
            proposal.review_notes = review_notes
            proposal.save()
            
            create_audit_log(
                user=request.user,
                action='reject',
                model_name='ModificationProposal',
                object_id=proposal.id,
                changes={'action': 'rejected', 'notes': review_notes},
                request=request
            )
            
            messages.success(request, 'Proposition rejetée.')
        
        return redirect('genealogy:dashboard')
    
    return render(request, 'genealogy/review_proposal.html', {
        'proposal': proposal
    })


def search_people(request):
    """Search for people in the family tree"""
    form = SearchForm(request.GET or None)
    people = Person.objects.none()
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        birth_year_from = form.cleaned_data.get('birth_year_from')
        birth_year_to = form.cleaned_data.get('birth_year_to')
        gender = form.cleaned_data.get('gender')
        is_deceased = form.cleaned_data.get('is_deceased')
        
        people = Person.objects.all()
        
        if query:
            people = people.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(maiden_name__icontains=query) |
                Q(biography__icontains=query)
            )
        
        if birth_year_from:
            people = people.filter(birth_date__year__gte=birth_year_from)
        
        if birth_year_to:
            people = people.filter(birth_date__year__lte=birth_year_to)
        
        if gender:
            people = people.filter(gender=gender)
        
        if is_deceased:
            people = people.filter(is_deceased=(is_deceased == 'True'))
        
        # Filter by visibility for non-authenticated users
        if not request.user.is_authenticated:
            people = people.filter(visibility='public')
        elif request.user.role != 'admin':
            people = people.filter(
                Q(visibility='public') | Q(visibility='family')
            )
    
    # Pagination
    paginator = Paginator(people, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'people': page_obj,
        'total_results': people.count() if people else 0,
    }
    
    return render(request, 'genealogy/search.html', context)


@login_required
def export_gedcom(request):
    """Export family tree to GEDCOM format"""
    if not request.user.can_export_data and request.user.role != 'admin':
        messages.error(request, "Vous n'avez pas l'autorisation d'exporter les données.")
        return redirect('genealogy:dashboard')
    
    gedcom_content = generate_gedcom_export()
    
    response = HttpResponse(gedcom_content, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="kanyamukenge_family.ged"'
    
    create_audit_log(
        user=request.user,
        action='export',
        model_name='GEDCOM',
        changes={'format': 'gedcom'},
        request=request
    )
    
    return response


@login_required
def manage_users(request):
    """Manage users and permissions (admin only)"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent gérer les utilisateurs.")
        return redirect('genealogy:dashboard')
    
    users = User.objects.all().order_by('last_name', 'first_name')
    
    context = {
        'users': users,
    }
    
    return render(request, 'genealogy/manage_users.html', context)


@login_required
def audit_log(request):
    """View audit log (admin only)"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent voir les journaux d'audit.")
        return redirect('genealogy:dashboard')
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
    }
    
    return render(request, 'genealogy/audit_log.html', context)


# API endpoints for AJAX requests

@require_http_methods(["GET"])
def api_person_search(request):
    """API endpoint for person search autocomplete"""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    people = Person.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(maiden_name__icontains=query)
    )
    
    # Filter by visibility if not admin
    if not request.user.is_authenticated:
        people = people.filter(visibility='public')
    elif request.user.role != 'admin':
        people = people.filter(
            Q(visibility='public') | Q(visibility='family')
        )
    
    results = []
    for person in people[:10]:  # Limit to 10 results
        results.append({
            'id': person.id,
            'name': person.get_full_name(),
            'birth_year': person.birth_date.year if person.birth_date else None,
            'photo_url': person.photo.url if person.photo else None,
        })
    
    return JsonResponse({'results': results})


@require_http_methods(["GET"])
def api_family_tree_data(request, person_id):
    """API endpoint to get family tree data for a person"""
    person = get_object_or_404(Person, id=person_id)
    
    if not can_view_person(request.user, person):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    tree_data = get_family_tree_data(person, request.user)
    return JsonResponse(tree_data)


# Helper functions

def can_view_person(user, person):
    """Check if user can view a person's details"""
    if person.visibility == 'public':
        return True
    
    if not user.is_authenticated:
        return False
    
    if user.role == 'admin':
        return True
    
    if person.visibility == 'family':
        return True
    
    if person.visibility == 'private':
        return person.can_be_modified_by(user)
    
    return False


def get_family_tree_data(center_person, user):
    """Generate complete family tree data structure for genealogical visualization"""
    
    def safe_get_person_data(person):
        """Safely get person data with null checks"""
        if not person:
            return None
            
        try:
            age = None
            if person.birth_date and not person.is_deceased:
                from datetime import date
                today = date.today()
                age = today.year - person.birth_date.year
                if today < person.birth_date.replace(year=today.year):
                    age -= 1
            
            return {
                'id': person.id,
                'name': person.get_full_name() or f"Person {person.id}",
                'gender': getattr(person, 'gender', 'U') or 'U',
                'birth_year': person.birth_date.year if person.birth_date else None,
                'death_year': person.death_date.year if person.death_date else None,
                'age': age,
                'is_deceased': getattr(person, 'is_deceased', False),
                'profession': getattr(person, 'profession', '') or '',
                'birth_place': getattr(person, 'birth_place', '') or '',
                'private': False
            }
        except Exception as e:
            print(f"Error getting person data for {person}: {e}")
            return None
    
    def build_complete_tree():
        """Build the complete family tree starting from all root ancestors"""
        
        # Find all people in the database
        from genealogy.models import Person
        all_people = Person.objects.all()
        
        # Build family structure
        families = {}  # family_id -> {parents: [], children: []}
        individuals = {}  # person_id -> person_data
        
        # Process all people
        for person in all_people:
            person_data = safe_get_person_data(person)
            if person_data:
                individuals[person.id] = person_data
                
                # Get family relationships
                try:
                    parents = person.get_parents()
                    partners = person.get_partners()
                    children = person.get_children()
                    
                    # Store relationships
                    person_data['parents'] = [p.id for p in parents]
                    person_data['partners'] = [p.id for p in partners] 
                    person_data['children'] = [c.id for c in children]
                    
                except Exception as e:
                    print(f"Error getting relationships for {person}: {e}")
                    person_data['parents'] = []
                    person_data['partners'] = []
                    person_data['children'] = []
        
        return individuals
    
    # Build the complete tree structure
    family_tree = build_complete_tree()
    
    return {
        'individuals': family_tree,
        'root_person_id': center_person.id if center_person else None
    }

def permission_denied_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def page_not_found_view(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def server_error_view(request):
    return render(request, 'errors/500.html', status=500)