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
from datetime import datetime 
from django.db import transaction

from accounts.forms import DirectUserCreationForm
from genealogy.notification_utils import notify_user_created


import logging
from django.core.mail import send_mail
from django.conf import settings

# from .email_utils import (
#     notify_person_created,
#     notify_person_edited, 
#     notify_person_deleted,
#     notify_child_added,
#     notify_modification_proposed,
#     notify_user_created,
#     notify_user_deleted,
#     notify_user_deactivated
# )

from .notification_utils import (
    notify_person_created,
    notify_person_edited, 
    notify_person_deleted,
    notify_child_added,
    notify_modification_proposed,
    notify_proposal_reviewed,
    notify_user_deactivated,
    notify_user_deleted,
)

from .models import (
    Notification, Person, Partnership, ParentChild, ModificationProposal,
    FamilyEvent, Document, AuditLog
)
from .forms import (
    PersonForm, PartnershipForm, ParentChildForm,
    ModificationProposalForm, FamilyEventForm, DocumentForm, SearchForm
)
from .utils import create_audit_log, generate_gedcom_export

import logging
logger = logging.getLogger(__name__)

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
    """Main dashboard for authenticated users - FIXED GENERATIONS CALCULATION"""
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
    
    # FIXED: Proper generations calculation
    def calculate_generations():
        """Calculate the actual number of generations in the family tree"""
        try:
            # Find all root people (those without parents in our database)
            all_people = Person.objects.all()
            
            if not all_people.exists():
                return {
                    'total_generations': 0,
                    'oldest_birth': None,
                    'newest_birth': None
                }
            
            # Find oldest and newest birth dates
            date_stats = Person.objects.filter(
                birth_date__isnull=False
            ).aggregate(
                oldest_birth=models.Min('birth_date'),
                newest_birth=models.Max('birth_date')
            )
            
            # Calculate generations using family tree structure
            generations_found = set()
            processed = set()
            
            # Find root people (those without parents in our system)
            root_people = []
            for person in all_people:
                try:
                    parents = person.get_parents() if hasattr(person, 'get_parents') else []
                    if not parents:
                        root_people.append(person)
                except:
                    root_people.append(person)
            
            if not root_people:
                # If no clear roots found, use oldest person
                oldest_person = all_people.filter(
                    birth_date__isnull=False
                ).order_by('birth_date').first()
                if oldest_person:
                    root_people = [oldest_person]
            
            # BFS to find all generations
            current_generation = 0
            queue = [(person, 0) for person in root_people]
            
            while queue:
                person, generation = queue.pop(0)
                
                if person.id in processed:
                    continue
                    
                processed.add(person.id)
                generations_found.add(generation)
                
                # Add children to next generation
                try:
                    children = person.get_children() if hasattr(person, 'get_children') else []
                    for child in children:
                        if child and child.id not in processed:
                            queue.append((child, generation + 1))
                except:
                    pass
            
            total_generations = len(generations_found) if generations_found else 1
            
            return {
                'total_generations': total_generations,
                'oldest_birth': date_stats['oldest_birth'],
                'newest_birth': date_stats['newest_birth']
            }
            
        except Exception as e:
            print(f"Error calculating generations: {e}")
            # Fallback calculation based on birth years
            try:
                oldest = Person.objects.filter(birth_date__isnull=False).order_by('birth_date').first()
                newest = Person.objects.filter(birth_date__isnull=False).order_by('-birth_date').first()
                
                if oldest and newest:
                    year_span = newest.birth_date.year - oldest.birth_date.year
                    estimated_generations = max(1, (year_span // 25) + 1)  # Rough estimate: 25 years per generation
                    
                    return {
                        'total_generations': estimated_generations,
                        'oldest_birth': oldest.birth_date,
                        'newest_birth': newest.birth_date
                    }
                else:
                    return {
                        'total_generations': 1,
                        'oldest_birth': None,
                        'newest_birth': None
                    }
            except:
                return {
                    'total_generations': 1,
                    'oldest_birth': None,
                    'newest_birth': None
                }
    
    # Calculate generations data
    generations_data = calculate_generations()
    
    context = {
        'recent_people': recent_people,
        'pending_proposals': pending_proposals,
        'user_people_count': user_people_count,
        'recent_events': recent_events,
        'total_people': Person.objects.count(),
        # FIXED: Proper generations data
        'total_generations': generations_data['total_generations'],
        'generations': {
            'oldest_birth': generations_data['oldest_birth'],
            'newest_birth': generations_data['newest_birth']
        },
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
        return redirect('genealogy:dashboard' if request.user.is_authenticated else 'genealogy:home')
    
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
    
    # Get related data
    try:
        parents = person.get_parents()
        children = person.get_children()
        partners = person.get_partners()
        siblings = person.get_siblings()
    except:
        parents = []
        children = []
        partners = []
        siblings = []
    
    # Documents and events
    documents = person.documents.all() if hasattr(person, 'documents') else []
    events = person.events.all().order_by('-date') if hasattr(person, 'events') else []
    
    # Modification proposals for this person (if admin)
    proposals = []
    if request.user.role == 'admin':
        proposals = ModificationProposal.objects.filter(
            person=person, status='pending'
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
    """Create a new person - WITH NOTIFICATION"""
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
            
            # Send notification instead of email
            try:
                notify_person_created(person, request.user)
                logger.info(f"Notification sent for person creation: {person.get_full_name()}")
            except Exception as e:
                logger.error(f"Failed to send notification for person creation: {str(e)}")
            
            messages.success(request, f'{person.get_full_name()} ajouté(e) avec succès.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = PersonForm()
    
    return render(request, 'genealogy/person_form.html', {
        'form': form,
        'title': 'Ajouter une personne'
    })


@login_required
def person_edit(request, person_id):
    """Edit a person's information - WITH NOTIFICATION"""
    person = get_object_or_404(Person, id=person_id)
    
    if not person.can_be_modified_by(request.user):
        messages.error(request, "Vous n'avez pas l'autorisation de modifier cette personne.")
        return redirect('genealogy:person_detail', person_id=person.id)
    
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            # Store old values for audit and notification
            old_values = {}
            changed_fields = []
            for field in form.changed_data:
                old_values[field] = getattr(person, field)
                changed_fields.append(field)
            
            form.save()
            
            create_audit_log(
                user=request.user,
                action='update',
                model_name='Person',
                object_id=person.id,
                changes={'old': old_values, 'new': form.cleaned_data},
                request=request
            )
            
            # Send notification instead of email if there were changes
            if changed_fields:
                try:
                    notify_person_edited(person, request.user, changed_fields)
                    logger.info(f"Notification sent for person edit: {person.get_full_name()}")
                except Exception as e:
                    logger.error(f"Failed to send notification for person edit: {str(e)}")
            
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
    """Delete a person - WITH EMAIL NOTIFICATION"""
    person = get_object_or_404(Person, id=person_id)
    
    # Check permissions
    can_delete = False
    if request.user.role == 'admin':
        can_delete = True
    elif hasattr(person, 'owned_by') and person.owned_by == request.user:
        can_delete = True
    
    if not can_delete:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer cette personne.")
        return redirect('genealogy:person_detail', person_id=person.id)
    
    # Store person info for notification before deletion
    person_name = person.get_full_name()
    
    # Delete the person
    person.delete()
    
    # Send email notification to admins
    try:
        notify_person_deleted(person_name, request.user)
        logger.info(f"Email notification sent for person deletion: {person_name}")
    except Exception as e:
        logger.error(f"Failed to send email notification for person deletion: {str(e)}")
    
    messages.success(request, f"{person_name} a été supprimé(e) avec succès.")
    return redirect('genealogy:dashboard')


@login_required
def add_partnership(request, person_id):
    """Add a partnership for a person"""
    person = get_object_or_404(Person, id=person_id)
    
    if not person.can_be_modified_by(request.user):
        messages.error(request, "Vous n'avez pas l'autorisation de modifier cette personne.")
        return redirect('genealogy:person_detail', person_id=person.id)
    
    if request.method == 'POST':
        form = PartnershipForm(request.POST)
        if form.is_valid():
            partnership = form.save(commit=False)
            partnership.person1 = person
            partnership.created_by = request.user
            partnership.save()
            
            create_audit_log(
                user=request.user,
                action='create',
                model_name='Partnership',
                object_id=partnership.id,
                changes=form.cleaned_data,
                request=request
            )
            
            messages.success(request, 'Union ajoutée avec succès.')
            return redirect('genealogy:person_detail', person_id=person.id)
    else:
        form = PartnershipForm()
    
    return render(request, 'genealogy/partnership_form.html', {
        'form': form,
        'person': person,
        'title': f'Ajouter une union pour {person.get_full_name()}'
    })


@login_required
def add_child(request, person_id):
    """Add child relationship - WITH NOTIFICATION"""
    parent = get_object_or_404(Person, id=person_id)
    
    if request.method == 'POST':
        form = ParentChildForm(request.POST, parent=parent)
        if form.is_valid():
            try:
                with transaction.atomic():
                    parent_child = form.save(commit=False)
                    parent_child.parent = parent
                    parent_child.created_by = request.user
                    parent_child.save()
                    
                    create_audit_log(
                        user=request.user,
                        action='create',
                        model_name='ParentChild',
                        object_id=parent_child.id,
                        changes=form.cleaned_data,
                        request=request
                    )
                    
                    # Send notification instead of email
                    try:
                        notify_child_added(parent, parent_child.child, request.user)
                        logger.info(f"Notification sent for child added: {parent.get_full_name()} -> {parent_child.child.get_full_name()}")
                    except Exception as e:
                        logger.error(f"Failed to send notification for child added: {str(e)}")
                    
                    messages.success(request, f'Relation parent-enfant ajoutée: {parent.get_full_name()} → {parent_child.child.get_full_name()}')
                    return redirect('genealogy:person_detail', person_id=parent.id)

            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, error_list in e.message_dict.items():
                        for error in error_list:
                            form.add_error(field, error)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                messages.error(request, f'Erreur lors de la création de la relation parent-enfant: {str(e)}')
                return redirect('genealogy:person_detail', person_id=parent.id)

    else:
        form = ParentChildForm(parent=parent)

    return render(request, 'genealogy/parent_child_form.html', {
        'form': form,
        'parent': parent,
        'title': f'Ajouter un enfant pour {parent.get_full_name()}',
    })


@login_required
def propose_modification(request, person_id):
    """Propose a modification for a person's data - WITH NOTIFICATION"""
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
            
            # Send notification instead of email to admins
            try:
                notify_modification_proposed(
                    person, 
                    request.user, 
                    proposal.field_name, 
                    proposal.old_value, 
                    proposal.new_value
                )
                logger.info(f"Notification sent for modification proposal: {person.get_full_name()}")
            except Exception as e:
                logger.error(f"Failed to send notification for modification proposal: {str(e)}")
            
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
    """Review a modification proposal (admin only) - WITH NOTIFICATION"""
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
            
            # Send notification to proposer
            try:
                notify_proposal_reviewed(proposal, request.user, approved=True)
                logger.info(f"Notification sent for approved proposal: {proposal.id}")
            except Exception as e:
                logger.error(f"Failed to send notification for approved proposal: {str(e)}")
            
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
            
            # Send notification to proposer
            try:
                notify_proposal_reviewed(proposal, request.user, approved=False)
                logger.info(f"Notification sent for rejected proposal: {proposal.id}")
            except Exception as e:
                logger.error(f"Failed to send notification for rejected proposal: {str(e)}")
            
            messages.success(request, 'Proposition rejetée.')
        
        return redirect('genealogy:manage_users')  # or wherever you want to redirect
    
    return render(request, 'genealogy/review_proposal.html', {
        'proposal': proposal,
        'title': f'Examiner proposition pour {proposal.person.get_full_name()}'
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
    """Complete manage users view with all data properly loaded"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent gérer les utilisateurs.")
        return redirect('genealogy:dashboard')
    
    # Get the active tab from URL parameter
    active_tab = request.GET.get('tab', 'users')  # Default to 'users' tab
    
    # Load all basic data
    users = User.objects.all().order_by('last_name', 'first_name')
    
    # User statistics
    user_stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'admin': User.objects.filter(role='admin').count(),
        'member': User.objects.filter(role='member').count(),
    }
    
    # Proposal statistics and data
    proposals_queryset = ModificationProposal.objects.select_related(
        'person', 'proposed_by', 'reviewed_by'
    ).order_by('-created_at')
    
    proposal_stats = {
        'total': proposals_queryset.count(),
        'pending': proposals_queryset.filter(status='pending').count(),
        'approved': proposals_queryset.filter(status='approved').count(),
        'rejected': proposals_queryset.filter(status='rejected').count(),
    }
    
    # Load proposals data (with pagination)
    proposals = None
    if active_tab == 'proposals':
        status_filter = request.GET.get('status')
        if status_filter:
            proposals_queryset = proposals_queryset.filter(status=status_filter)
        
        # Pagination for proposals
        paginator = Paginator(proposals_queryset, 20)  # Show 20 proposals per page
        page_number = request.GET.get('page')
        proposals = paginator.get_page(page_number)
    
    # Load invitations data - Import the model if it exists
    invitations = None
    invitation_stats = {'total': 0, 'pending': 0, 'accepted': 0, 'expired': 0}
    
    try:
        # Try to import UserInvitation model - adjust import path as needed
        from accounts.models import UserInvitation
        
        invitations_queryset = UserInvitation.objects.all().order_by('-created_at')
        
        invitation_stats = {
            'total': invitations_queryset.count(),
            'pending': invitations_queryset.filter(accepted_at__isnull=True, expires_at__gt=timezone.now()).count() if hasattr(UserInvitation, 'expires_at') else 0,
            'accepted': invitations_queryset.filter(accepted_at__isnull=False).count() if hasattr(UserInvitation, 'accepted_at') else 0,
            'expired': invitations_queryset.filter(expires_at__lt=timezone.now()).count() if hasattr(UserInvitation, 'expires_at') else 0,
        }
        
        if active_tab == 'invitations':
            invitations = invitations_queryset
            
    except ImportError:
        # UserInvitation model doesn't exist
        pass
    except Exception as e:
        # Handle other potential errors
        print(f"Error loading invitations: {e}")
    
    # Search functionality for users
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    context = {
        'active_tab': active_tab,
        'users': users,
        'user_stats': user_stats,
        'proposals': proposals,
        'proposal_stats': proposal_stats,
        'invitations': invitations,
        'invitation_stats': invitation_stats,
        'search_query': search_query,
    }
    
    return render(request, 'genealogy/manage_users.html', context)

@login_required
def toggle_user(request, user_id):
    """Toggle user active status - WITH EMAIL NOTIFICATION FOR DEACTIVATION"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent admin from deactivating themselves
    if user == request.user:
        return JsonResponse({'error': 'Vous ne pouvez pas désactiver votre propre compte'}, status=400)
    
    try:
        # Toggle active status
        activate = not user.is_active
        user.is_active = activate
        user.save()
        
        action = 'activate' if activate else 'deactivate'
        
        # Create audit log
        create_audit_log(
            user=request.user,
            action=action,
            model_name='User',
            object_id=user.id,
            changes={
                'action': action,
                'is_active': activate,
                'target_user': user.get_full_name()
            },
            request=request
        )
        
        # Send email notification only for deactivation
        if not activate:
            try:
                notify_user_deactivated(user, request.user)
                logger.info(f"Email notification sent for user deactivation: {user.email}")
            except Exception as e:
                logger.error(f"Failed to send email notification for user deactivation: {str(e)}")
        
        message = f'Utilisateur {"activé" if activate else "désactivé"} avec succès'
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def delete_user(request, user_id):
    """Delete user account - WITH EMAIL NOTIFICATION"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent admin from deleting themselves
    if user == request.user:
        return JsonResponse({'error': 'Vous ne pouvez pas supprimer votre propre compte'}, status=400)
    
    try:
        # Store user info for notifications before deletion
        user_name = user.get_full_name()
        user_email = user.email
        
        # Create audit log before deletion
        create_audit_log(
            user=request.user,
            action='delete',
            model_name='User',
            object_id=user.id,
            changes={
                'deleted_user': user_name,
                'email': user_email,
                'role': user.role
            },
            request=request
        )
        
        # Delete the user
        user.delete()
        
        # Send email notification
        try:
            notify_user_deleted(user_name, user_email, request.user)
            logger.info(f"Email notification sent for user deletion: {user_email}")
        except Exception as e:
            logger.error(f"Failed to send email notification for user deletion: {str(e)}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Utilisateur {user_name} supprimé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def edit_user(request, user_id):
    """Edit user permissions and role"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user = get_object_or_404(User, id=user_id)
    
    try:
        old_values = {
            'role': user.role,
            'can_add_children': getattr(user, 'can_add_children', False),
            'can_modify_own_info': getattr(user, 'can_modify_own_info', False),
            'can_view_private_info': getattr(user, 'can_view_private_info', False),
            'can_export_data': getattr(user, 'can_export_data', False),
        }
        
        # Update basic info
        new_role = request.POST.get('role')
        if new_role in ['admin', 'member', 'visitor']:
            user.role = new_role
        
        # Update permissions (if user model has these fields)
        permissions = [
            'can_add_children',
            'can_modify_own_info', 
            'can_view_private_info',
            'can_export_data'
        ]
        
        changes = {}
        for perm in permissions:
            if hasattr(user, perm):
                old_val = getattr(user, perm, False)
                new_val = request.POST.get(perm) == 'on'
                setattr(user, perm, new_val)
                if old_val != new_val:
                    changes[perm] = {'old': old_val, 'new': new_val}
        
        if user.role != old_values['role']:
            changes['role'] = {'old': old_values['role'], 'new': user.role}
        
        user.save()
        
        # Create audit log
        if changes:
            from .utils import create_audit_log
            create_audit_log(
                user=request.user,
                action='update',
                model_name='User',
                object_id=user.id,
                changes={
                    'target_user': user.get_full_name(),
                    'changes': changes
                },
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Utilisateur {user.get_full_name()} mis à jour avec succès'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def audit_log(request):
    """View audit log with filtering (admin only)"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent voir les journaux d'audit.")
        return redirect('genealogy:dashboard')
    
    # Get all logs initially
    logs = AuditLog.objects.all()
    
    # Apply filters based on GET parameters
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    model_filter = request.GET.get('model')
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    # Date filtering
    date_from = request.GET.get('date_from')
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from_obj)
        except ValueError:
            messages.warning(request, "Format de date invalide pour 'Date de'")
    
    date_to = request.GET.get('date_to')
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to_obj)
        except ValueError:
            messages.warning(request, "Format de date invalide pour 'Date à'")
    
    # User filtering (handle deleted users)
    user_search = request.GET.get('user')
    if user_search:
        logs = logs.filter(
            Q(user__username__icontains=user_search) |
            Q(user__first_name__icontains=user_search) |
            Q(user__last_name__icontains=user_search) |
            Q(user__email__icontains=user_search)
        )
    
    # Order by most recent first
    logs = logs.order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(logs, 20)  # Show 20 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'total_logs': logs.count(),
        'filters': {
            'action': action_filter,
            'model': model_filter,
            'date_from': date_from,
            'date_to': date_to,
            'user': user_search,
        }
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
    """Check if user can view person"""
    if not person:
        return False
    
    # Public visibility
    if person.visibility == 'public':
        return True
    
    # Private visibility - only the person themselves or admin
    if person.visibility == 'private':
        if not user or not user.is_authenticated:
            return False
        if user.role == 'admin':
            return True
        if person.user_account == user:
            return True
        return False
    
    # Family visibility - any authenticated family member
    if person.visibility == 'family':
        return user and user.is_authenticated
    
    return False


def get_family_tree_data(center_person, user):
    """Generate family tree data for D3.js visualization - FIXED PHOTO URLs"""
    
    def safe_get_person_data(person):
        """Safely get person data with null checks - FIXED PHOTO URL"""
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
            
            # FIXED: Proper photo URL handling
            photo_url = None
            if person.photo:
                try:
                    photo_url = person.photo.url
                except (AttributeError, ValueError):
                    # Handle cases where photo file is missing or invalid
                    photo_url = None
            
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
                'photo_url': photo_url,  # ADDED: Photo URL for tree display
                'private': False
            }
        except Exception as e:
            print(f"Error getting person data for {person}: {e}")
            return None
    
    def build_family_tree():
        """Build family tree structure"""
        try:
            # Find all people in the database
            all_people = Person.objects.all()
            
            # Build family structure
            individuals = {}
            
            # Process all people
            for person in all_people:
                if not can_view_person(user, person):
                    continue
                    
                person_data = safe_get_person_data(person)
                if person_data:
                    individuals[person.id] = person_data
                    
                    # Get family relationships
                    try:
                        parents = person.get_parents() if hasattr(person, 'get_parents') else []
                        partners = person.get_partners() if hasattr(person, 'get_partners') else []
                        children = person.get_children() if hasattr(person, 'get_children') else []
                        
                        # Store relationships
                        person_data['parents'] = [p.id for p in parents if p]
                        person_data['partners'] = [p.id for p in partners if p] 
                        person_data['children'] = [c.id for c in children if c]
                        
                    except Exception as e:
                        print(f"Error getting relationships for {person}: {e}")
                        person_data['parents'] = []
                        person_data['partners'] = []
                        person_data['children'] = []
            
            return individuals
        except Exception as e:
            print(f"Error building family tree: {e}")
            return {}
    
    # Build the complete tree structure
    try:
        family_tree = build_family_tree()
        
        return {
            'individuals': family_tree,
            'root_person_id': center_person.id if center_person else None
        }
    except Exception as e:
        print(f"Error in get_family_tree_data: {e}")
        return {
            'individuals': {},
            'root_person_id': None
        }


# Error handlers
def permission_denied_view(request, exception=None):
    """Custom 403 error page"""
    return render(request, 'errors/403.html', status=403)


def page_not_found_view(request, exception=None):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)


def server_error_view(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', status=500)

def public_tree_view(request, person_id=None):
    """Public family tree view - limited information"""
    
    # Get only public people
    public_people = Person.objects.filter(visibility='public').order_by('last_name', 'first_name')
    
    if not public_people.exists():
        messages.info(request, "Aucun membre public n'est disponible dans l'arbre généalogique.")
        return redirect('genealogy:home')
    
    if person_id:
        center_person = get_object_or_404(Person, id=person_id, visibility='public')
    else:
        # Default to oldest public person
        center_person = public_people.filter(birth_date__isnull=False).order_by('birth_date').first()
        if not center_person:
            center_person = public_people.first()
    
    # Get public family tree data
    tree_data = get_public_family_tree_data(center_person)
    
    context = {
        'center_person': center_person,
        'tree_data': json.dumps(tree_data),
        'public_people': public_people,
    }
    
    return render(request, 'genealogy/public_tree.html', context)


def get_public_family_tree_data(center_person):
    """Generate public family tree data - limited information only"""
    
    def safe_get_public_person_data(person):
        """Get limited person data for public view"""
        if not person or person.visibility != 'public':
            return None
            
        try:
            return {
                'id': person.id,
                'name': person.get_full_name() or f"Membre famille",
                'gender': getattr(person, 'gender', 'U') or 'U',
                'birth_year': person.birth_date.year if person.birth_date else None,
                'death_year': person.death_date.year if person.death_date else None,
                'is_deceased': getattr(person, 'is_deceased', False),
                # NO: profession, biography, photo_url, birth_place, etc.
                'private': False
            }
        except Exception as e:
            print(f"Error getting public person data for {person}: {e}")
            return None
    
    def build_public_family_tree():
        """Build family tree structure with only public people"""
        try:
            # Find all PUBLIC people only
            all_people = Person.objects.filter(visibility='public')
            
            individuals = {}
            
            # Process all public people
            for person in all_people:
                person_data = safe_get_public_person_data(person)
                if person_data:
                    individuals[person.id] = person_data
                    
                    # Get family relationships (only to other public people)
                    try:
                        # Get parents, partners, children - but only if they're also public
                        parents = []
                        partners = []
                        children = []
                        
                        if hasattr(person, 'get_parents'):
                            parents = [p for p in person.get_parents() if p and p.visibility == 'public']
                        
                        if hasattr(person, 'get_partners'):
                            partners = [p for p in person.get_partners() if p and p.visibility == 'public']
                        
                        if hasattr(person, 'get_children'):
                            children = [c for c in person.get_children() if c and c.visibility == 'public']
                        
                        # Store relationships
                        person_data['parents'] = [p.id for p in parents if p]
                        person_data['partners'] = [p.id for p in partners if p] 
                        person_data['children'] = [c.id for c in children if c]
                        
                    except Exception as e:
                        print(f"Error getting public relationships for {person}: {e}")
                        person_data['parents'] = []
                        person_data['partners'] = []
                        person_data['children'] = []
            
            return individuals
        except Exception as e:
            print(f"Error building public family tree: {e}")
            return {}
    
    # Build the public tree structure
    try:
        public_tree = build_public_family_tree()
        
        return {
            'individuals': public_tree,
            'root_person_id': center_person.id if center_person else None
        }
    except Exception as e:
        print(f"Error in get_public_family_tree_data: {e}")
        return {
            'individuals': {},
            'root_person_id': None
        }

# Also update the existing home view to include public people for statistics
def home(request):
    """Public home page showing family tree overview - UPDATED"""

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
def notifications_view(request):
    """Display notifications page with filtering and pagination"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    
    # Base queryset
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Apply filters
    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status_filter == 'read':
        notifications = notifications.filter(is_read=True)
    
    if type_filter != 'all':
        notifications = notifications.filter(notification_type=type_filter)
    
    # Order by creation date
    notifications = notifications.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get notification type choices for filter dropdown
    type_choices = Notification.NOTIFICATION_TYPES
    
    # Statistics
    stats = {
        'total': Notification.objects.filter(recipient=request.user).count(),
        'unread': Notification.objects.filter(recipient=request.user, is_read=False).count(),
        'read': Notification.objects.filter(recipient=request.user, is_read=True).count(),
    }
    
    context = {
        'notifications': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'type_choices': type_choices,
        'stats': stats,
        'paginator': paginator,
    }
    
    return render(request, 'genealogy/notifications.html', context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marquée comme lue'
        })
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la mise à jour'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    try:
        updated_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} notifications marquées comme lues',
            'updated_count': updated_count
        })
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la mise à jour'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification supprimée'
        })
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors de la suppression'
        }, status=500)


@login_required
def get_notifications_api(request):
    """API endpoint for getting notifications (for AJAX updates)"""
    try:
        limit = int(request.GET.get('limit', 10))
        offset = int(request.GET.get('offset', 0))
        
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[offset:offset + limit]
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'icon': notification.get_icon(),
                'color_class': notification.get_color_class(),
                'action_url': notification.action_url,
                'priority': notification.priority,
            })
        
        unread_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count,
            'has_more': len(notifications) == limit
        })
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors du chargement des notifications'
        }, status=500)
    
@login_required
def create_user_direct(request):
    """Create user directly without email invitation (admin only)"""
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent créer des utilisateurs.")
        return redirect('genealogy:manage_users')
    
    if request.method == 'POST':
        form = DirectUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the user
                    user = form.save()
                    
                    # Create audit log
                    create_audit_log(
                        user=request.user,
                        action='create',
                        model_name='User',
                        object_id=user.id,
                        changes={
                            'username': user.username,
                            'email': user.email,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'role': user.role,
                            'created_by': request.user.get_full_name()
                        },
                        request=request
                    )
                    
                    # Send notification instead of email
                    try:
                        notify_user_created(user, request.user)
                        logger.info(f"Notification sent for user creation: {user.get_full_name()}")
                    except Exception as e:
                        logger.error(f"Failed to send notification for user creation: {str(e)}")
                    
                    messages.success(
                        request, 
                        f'Utilisateur {user.get_full_name()} créé avec succès. '
                        f'Nom d\'utilisateur: {user.username}'
                    )
                    return redirect('genealogy:manage_users')
                    
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                messages.error(request, f'Erreur lors de la création de l\'utilisateur: {str(e)}')
    else:
        form = DirectUserCreationForm()
    
    return render(request, 'genealogy/create_user_direct.html', {
        'form': form,
        'title': 'Créer un nouvel utilisateur'
    })




