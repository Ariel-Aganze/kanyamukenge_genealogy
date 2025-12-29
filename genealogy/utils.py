from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from .models import AuditLog, Person, Partnership, ParentChild
import json
from datetime import date, datetime
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()

def create_audit_log(user, action, model_name, object_id=None, changes=None, request=None):
    """Create an audit log entry with proper JSON serialization"""
    
    def convert_to_serializable(obj):
        """Convert non-JSON serializable objects to serializable format"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, 'pk'):  # Django model instance
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif obj is None:
            return None
        else:
            try:
                # Test if value is already JSON serializable
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    # Get IP address
    ip_address = None
    if request:
        # Try to get real IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    # Convert changes to be JSON serializable
    serializable_changes = convert_to_serializable(changes or {})
    
    # Create the audit log entry
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        changes=serializable_changes, 
        ip_address=ip_address
    )

def generate_gedcom_export():
    """Generate GEDCOM format export of the family tree"""
    gedcom_lines = []
    
    # Get today's date properly
    today = date.today()
    
    # GEDCOM header
    gedcom_lines.extend([
        "0 HEAD",
        "1 SOUR Famille KANYAMUKENGE",
        "2 NAME Système Généalogique KANYAMUKENGE",
        f"2 DATE {today.strftime('%d %b %Y').upper()}",
        "1 CHAR UTF-8",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "",
    ])
    
    try:
        # Individuals
        people = Person.objects.all().order_by('id')
        for person in people:
            individual_id = f"I{person.id}"
            
            gedcom_lines.extend([
                f"0 @{individual_id}@ INDI",
                f"1 NAME {person.first_name or 'Unknown'} /{person.last_name or 'Unknown'}/",
            ])
            
            if person.maiden_name:
                gedcom_lines.append(f"1 NAME {person.first_name or 'Unknown'} /{person.maiden_name}/")
            
            if person.gender:
                gedcom_lines.append(f"1 SEX {person.gender}")
            
            if person.birth_date:
                birth_date_str = person.birth_date.strftime("%d %b %Y").upper()
                gedcom_lines.append("1 BIRT")
                gedcom_lines.append(f"2 DATE {birth_date_str}")
                if person.birth_place:
                    gedcom_lines.append(f"2 PLAC {person.birth_place}")
            
            if person.death_date:
                death_date_str = person.death_date.strftime("%d %b %Y").upper()
                gedcom_lines.append("1 DEAT")
                gedcom_lines.append(f"2 DATE {death_date_str}")
                if person.death_place:
                    gedcom_lines.append(f"2 PLAC {person.death_place}")
            
            if person.profession:
                gedcom_lines.append(f"1 OCCU {person.profession}")
            
            if person.biography:
                # Split biography into lines if too long
                bio_lines = person.biography.split('\n')
                for i, line in enumerate(bio_lines):
                    if i == 0:
                        gedcom_lines.append(f"1 NOTE {line}")
                    else:
                        gedcom_lines.append(f"2 CONT {line}")
            
            gedcom_lines.append("")
        
        # Families (marriages/partnerships)
        family_id = 1
        partnerships = Partnership.objects.filter(status='confirmed')
        
        for partnership in partnerships:
            family_gedcom_id = f"F{family_id}"
            person1_id = f"I{partnership.person1.id}"
            person2_id = f"I{partnership.person2.id}"
            
            gedcom_lines.extend([
                f"0 @{family_gedcom_id}@ FAM",
                f"1 HUSB @{person1_id}@",
                f"1 WIFE @{person2_id}@",
            ])
            
            if partnership.start_date:
                marriage_date = partnership.start_date.strftime("%d %b %Y").upper()
                gedcom_lines.append("1 MARR")
                gedcom_lines.append(f"2 DATE {marriage_date}")
                if partnership.location:
                    gedcom_lines.append(f"2 PLAC {partnership.location}")
            
            if partnership.end_date:
                divorce_date = partnership.end_date.strftime("%d %b %Y").upper()
                gedcom_lines.append("1 DIV")
                gedcom_lines.append(f"2 DATE {divorce_date}")
            
            # Add children to this family
            try:
                children = ParentChild.objects.filter(
                    parent__in=[partnership.person1, partnership.person2]
                )
                child_ids = set()
                for parent_child in children:
                    child_ids.add(parent_child.child.id)
                
                for child_id in child_ids:
                    gedcom_lines.append(f"1 CHIL @I{child_id}@")
            except Exception as e:
                print(f"Error processing children for family {family_id}: {e}")
            
            gedcom_lines.append("")
            family_id += 1
        
        # Parent-Child relationships (for children without marriage record)
        processed_children = set()
        parent_child_relations = ParentChild.objects.all()
        
        for relation in parent_child_relations:
            child_id = relation.child.id
            if child_id not in processed_children:
                # Find all parents of this child
                child_relations = ParentChild.objects.filter(child=relation.child)
                parents = [rel.parent for rel in child_relations]
                
                if len(parents) == 1:
                    # Single parent family
                    family_gedcom_id = f"F{family_id}"
                    parent_id = f"I{parents[0].id}"
                    child_gedcom_id = f"I{child_id}"
                    
                    gedcom_lines.extend([
                        f"0 @{family_gedcom_id}@ FAM",
                        f"1 {'HUSB' if parents[0].gender == 'M' else 'WIFE'} @{parent_id}@",
                        f"1 CHIL @{child_gedcom_id}@",
                        ""
                    ])
                    
                    family_id += 1
                    processed_children.add(child_id)
    
    except Exception as e:
        print(f"Error generating GEDCOM: {e}")
        # Return a minimal GEDCOM if there's an error
        gedcom_lines = [
            "0 HEAD",
            "1 SOUR Famille KANYAMUKENGE",
            f"2 DATE {today.strftime('%d %b %Y').upper()}",
            "1 CHAR UTF-8",
            "0 TRLR"
        ]
    
    # GEDCOM trailer
    gedcom_lines.append("0 TRLR")
    
    return '\n'.join(gedcom_lines)


def validate_family_tree():
    """Validate the family tree for inconsistencies and errors"""
    errors = []
    warnings = []
    
    try:
        # Check for circular relationships
        people = Person.objects.all()
        for person in people:
            try:
                if has_circular_relationship(person, set()):
                    errors.append(f"Relation circulaire détectée pour {person.get_full_name()}")
            except Exception as e:
                warnings.append(f"Erreur lors de la vérification de {person.get_full_name()}: {e}")
        
        # Check for impossible dates
        for person in people:
            try:
                if person.birth_date and person.death_date:
                    if person.birth_date > person.death_date:
                        errors.append(f"Date de naissance postérieure à la date de décès pour {person.get_full_name()}")
                
                # Check parent-child age differences
                if hasattr(person, 'get_parents'):
                    parents = person.get_parents()
                    for parent in parents:
                        if person.birth_date and parent.birth_date:
                            age_diff = (person.birth_date - parent.birth_date).days / 365.25
                            if age_diff < 12:  # Parent was younger than 12 when child was born
                                warnings.append(f"Différence d'âge suspecte entre {parent.get_full_name()} et {person.get_full_name()}")
            except Exception as e:
                warnings.append(f"Erreur lors de la validation des dates pour {person.get_full_name()}: {e}")
        
        # Check for potential duplicates
        potential_duplicates = []
        for person in people:
            try:
                similar_people = Person.objects.filter(
                    first_name__iexact=person.first_name,
                    last_name__iexact=person.last_name
                ).exclude(id=person.id)
                
                if similar_people.exists():
                    potential_duplicates.append(
                        f"Possible doublon: {person.get_full_name()} "
                        f"(ID: {person.id}) similaire à {similar_people.count()} autre(s) personne(s)"
                    )
            except Exception as e:
                warnings.append(f"Erreur lors de la vérification des doublons pour {person.get_full_name()}: {e}")
        
        errors.extend(potential_duplicates)
    
    except Exception as e:
        errors.append(f"Erreur générale lors de la validation: {e}")
    
    return errors, warnings


def has_circular_relationship(person, visited, depth=0):
    """Check for circular relationships in family tree"""
    if depth > 10:  # Prevent infinite recursion
        return False
    
    if person.id in visited:
        return True
    
    visited.add(person.id)
    
    try:
        # Check parents
        if hasattr(person, 'get_parents'):
            for parent in person.get_parents():
                if has_circular_relationship(parent, visited.copy(), depth + 1):
                    return True
        
        # Check children
        if hasattr(person, 'get_children'):
            for child in person.get_children():
                if has_circular_relationship(child, visited.copy(), depth + 1):
                    return True
    except Exception:
        pass  # Skip if methods don't exist or fail
    
    return False


def get_generation_level(person, root_person=None):
    """Calculate the generation level of a person relative to a root person"""
    try:
        if root_person is None:
            # Find the oldest ancestor as root
            current = person
            if hasattr(current, 'get_parents'):
                while current.get_parents():
                    parents = current.get_parents()
                    if parents:
                        current = parents[0]
                    else:
                        break
            root_person = current
        
        if person == root_person:
            return 0
        
        # BFS to find shortest path to root
        from collections import deque
        
        queue = deque([(person, 0)])
        visited = set([person.id])
        
        while queue:
            current_person, level = queue.popleft()
            
            # Check parents (go up one generation)
            if hasattr(current_person, 'get_parents'):
                for parent in current_person.get_parents():
                    if parent == root_person:
                        return -(level + 1)  # Negative for ancestors
                    
                    if parent.id not in visited:
                        visited.add(parent.id)
                        queue.append((parent, level + 1))
            
            # Check children (go down one generation)
            if hasattr(current_person, 'get_children'):
                for child in current_person.get_children():
                    if child == root_person:
                        return level + 1  # Positive for descendants
                    
                    if child.id not in visited:
                        visited.add(child.id)
                        queue.append((child, level + 1))
        
        return None  # No relationship found
    except Exception:
        return None


def get_family_statistics():
    """Get statistics about the family tree"""
    try:
        stats = {
            'total_people': Person.objects.count(),
            'living_people': Person.objects.filter(is_deceased=False).count(),
            'deceased_people': Person.objects.filter(is_deceased=True).count(),
            'total_partnerships': Partnership.objects.count(),
            'confirmed_partnerships': Partnership.objects.filter(status='confirmed').count(),
            'total_generations': 0,
            'oldest_person': None,
            'youngest_person': None,
        }
        
        # Calculate generations
        people_with_birth_dates = Person.objects.filter(birth_date__isnull=False)
        if people_with_birth_dates.exists():
            oldest = people_with_birth_dates.order_by('birth_date').first()
            youngest = people_with_birth_dates.order_by('-birth_date').first()
            
            stats['oldest_person'] = oldest
            stats['youngest_person'] = youngest
            
            if oldest and youngest and oldest.birth_date and youngest.birth_date:
                year_span = youngest.birth_date.year - oldest.birth_date.year
                stats['total_generations'] = max(1, year_span // 25)  # Approximate generations
        
        return stats
    except Exception as e:
        print(f"Error calculating family statistics: {e}")
        return {
            'total_people': 0,
            'living_people': 0,
            'deceased_people': 0,
            'total_partnerships': 0,
            'confirmed_partnerships': 0,
            'total_generations': 0,
            'oldest_person': None,
            'youngest_person': None,
        }


def export_family_data(format_type='json'):
    """Export family data in various formats"""
    try:
        people = Person.objects.all()
        partnerships = Partnership.objects.all()
        parent_child_relations = ParentChild.objects.all()
        
        if format_type == 'json':
            data = {
                'people': [
                    {
                        'id': person.id,
                        'first_name': person.first_name,
                        'last_name': person.last_name,
                        'maiden_name': person.maiden_name,
                        'gender': person.gender,
                        'birth_date': person.birth_date.isoformat() if person.birth_date else None,
                        'death_date': person.death_date.isoformat() if person.death_date else None,
                        'birth_place': person.birth_place,
                        'death_place': person.death_place,
                        'profession': person.profession,
                        'biography': person.biography,
                        'is_deceased': person.is_deceased,
                    }
                    for person in people
                ],
                'partnerships': [
                    {
                        'id': partnership.id,
                        'person1_id': partnership.person1.id,
                        'person2_id': partnership.person2.id,
                        'partnership_type': partnership.partnership_type,
                        'start_date': partnership.start_date.isoformat() if partnership.start_date else None,
                        'end_date': partnership.end_date.isoformat() if partnership.end_date else None,
                        'location': partnership.location,
                        'status': partnership.status,
                    }
                    for partnership in partnerships
                ],
                'parent_child_relations': [
                    {
                        'id': relation.id,
                        'parent_id': relation.parent.id,
                        'child_id': relation.child.id,
                        'relationship_type': relation.relationship_type,
                    }
                    for relation in parent_child_relations
                ]
            }
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        elif format_type == 'gedcom':
            return generate_gedcom_export()
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    except Exception as e:
        print(f"Error exporting family data: {e}")
        return f"Error exporting data: {e}"