from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from .models import AuditLog, Person, Partnership, ParentChild
import datetime
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
    
    # GEDCOM header
    gedcom_lines.extend([
        "0 HEAD",
        "1 SOUR Famille KANYAMUKENGE",
        "2 NAME Système Généalogique KANYAMUKENGE",
        f"2 DATE {datetime.date.today().strftime('%d %b %Y').upper()}",
        "1 CHAR UTF-8",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "",
    ])
    
    # Individuals
    people = Person.objects.all().order_by('id')
    for person in people:
        individual_id = f"I{person.id}"
        
        gedcom_lines.extend([
            f"0 @{individual_id}@ INDI",
            f"1 NAME {person.first_name} /{person.last_name}/",
        ])
        
        if person.maiden_name:
            gedcom_lines.append(f"1 NAME {person.first_name} /{person.maiden_name}/")
        
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
        # Find children who have both persons as parents
        person1_children = set(ParentChild.objects.filter(
            parent=partnership.person1, status='confirmed'
        ).values_list('child_id', flat=True))
        
        person2_children = set(ParentChild.objects.filter(
            parent=partnership.person2, status='confirmed'
        ).values_list('child_id', flat=True))
        
        common_children = person1_children.intersection(person2_children)
        
        for child_id in common_children:
            gedcom_lines.append(f"1 CHIL @I{child_id}@")
        
        gedcom_lines.append("")
        family_id += 1
    
    # Add family links to individuals
    for person in people:
        individual_id = f"I{person.id}"
        
        # Add family as child (FAMC)
        parents = person.get_parents()
        if len(parents) >= 2:
            # Find the family record for these parents
            parent1, parent2 = parents[0], parents[1]
            try:
                partnership = Partnership.objects.get(
                    person1__in=[parent1, parent2],
                    person2__in=[parent1, parent2],
                    status='confirmed'
                )
                family_index = list(partnerships).index(partnership) + 1
                gedcom_lines.append(f"0 @I{person.id}@ INDI")
                gedcom_lines.append(f"1 FAMC @F{family_index}@")
                gedcom_lines.append("")
            except Partnership.DoesNotExist:
                pass
        
        # Add family as spouse (FAMS)
        person_partnerships = Partnership.objects.filter(
            models.Q(person1=person) | models.Q(person2=person),
            status='confirmed'
        )
        
        for partnership in person_partnerships:
            family_index = list(partnerships).index(partnership) + 1
            gedcom_lines.append(f"0 @I{person.id}@ INDI")
            gedcom_lines.append(f"1 FAMS @F{family_index}@")
            gedcom_lines.append("")
    
    # GEDCOM trailer
    gedcom_lines.append("0 TRLR")
    
    return '\n'.join(gedcom_lines)


def calculate_relationship(person1, person2):
    """Calculate the relationship between two people"""
    if person1 == person2:
        return "same_person"
    
    # Check direct relationships
    if person2 in person1.get_parents():
        return "parent"
    
    if person2 in person1.get_children():
        return "child"
    
    if person2 in person1.get_partners():
        return "partner"
    
    if person2 in person1.get_siblings():
        return "sibling"
    
    # Check for grandparents/grandchildren
    person1_parents = person1.get_parents()
    person2_parents = person2.get_parents()
    
    # Grandparent/grandchild relationships
    for parent in person1_parents:
        if person2 in parent.get_parents():
            return "grandparent"
        
        for grandparent in parent.get_parents():
            if person2 == grandparent:
                return "grandparent"
    
    for child in person1.get_children():
        if person2 in child.get_children():
            return "grandchild"
    
    # Check for cousins (share grandparents)
    person1_grandparents = []
    for parent in person1_parents:
        person1_grandparents.extend(parent.get_parents())
    
    person2_grandparents = []
    for parent in person2_parents:
        person2_grandparents.extend(parent.get_parents())
    
    if any(gp in person2_grandparents for gp in person1_grandparents):
        return "cousin"
    
    # Check for aunt/uncle, niece/nephew relationships
    person1_siblings = person1.get_siblings()
    for sibling in person1_siblings:
        if person2 in sibling.get_children():
            return "niece_nephew"
        if person2 in sibling.get_parents():
            return "aunt_uncle"
    
    person2_siblings = person2.get_siblings()
    for sibling in person2_siblings:
        if person1 in sibling.get_children():
            return "aunt_uncle"
        if person1 in sibling.get_parents():
            return "niece_nephew"
    
    return "distant_relative"


def get_relationship_display(relationship):
    """Get human-readable relationship display"""
    relationship_map = {
        "same_person": "Même personne",
        "parent": "Parent",
        "child": "Enfant",
        "partner": "Conjoint(e)",
        "sibling": "Frère/Sœur",
        "grandparent": "Grand-parent",
        "grandchild": "Petit-enfant",
        "cousin": "Cousin(e)",
        "aunt_uncle": "Oncle/Tante",
        "niece_nephew": "Neveu/Nièce",
        "distant_relative": "Parenté éloignée",
    }
    
    return relationship_map.get(relationship, "Relation inconnue")


def validate_family_tree_consistency():
    """Validate the consistency of the family tree data"""
    errors = []
    
    # Check for circular relationships
    people = Person.objects.all()
    for person in people:
        visited = set()
        if has_circular_relationship(person, visited):
            errors.append(f"Relation circulaire détectée impliquant {person.get_full_name()}")
    
    # Check for impossible dates
    parent_child_relations = ParentChild.objects.filter(status='confirmed')
    for relation in parent_child_relations:
        parent = relation.parent
        child = relation.child
        
        if parent.birth_date and child.birth_date:
            # Parent should be at least 10 years older than child
            age_difference = child.birth_date.year - parent.birth_date.year
            if age_difference < 10:
                errors.append(
                    f"Âge parent-enfant suspect: {parent.get_full_name()} "
                    f"et {child.get_full_name()} (différence: {age_difference} ans)"
                )
        
        if parent.death_date and child.birth_date:
            # Child cannot be born after parent's death (allowing 9 months grace period)
            death_year = parent.death_date.year
            birth_year = child.birth_date.year
            if birth_year > death_year + 1:
                errors.append(
                    f"Date impossible: {child.get_full_name()} né après "
                    f"la mort de {parent.get_full_name()}"
                )
    
    # Check for duplicate people
    potential_duplicates = []
    for person in people:
        similar_people = Person.objects.filter(
            first_name__iexact=person.first_name,
            last_name__iexact=person.last_name,
            birth_date=person.birth_date
        ).exclude(id=person.id)
        
        if similar_people.exists():
            potential_duplicates.append(
                f"Possible doublon: {person.get_full_name()} "
                f"(ID: {person.id}) similaire à {similar_people.count()} autre(s) personne(s)"
            )
    
    errors.extend(potential_duplicates)
    
    return errors


def has_circular_relationship(person, visited, depth=0):
    """Check for circular relationships in family tree"""
    if depth > 10:  # Prevent infinite recursion
        return False
    
    if person.id in visited:
        return True
    
    visited.add(person.id)
    
    # Check parents
    for parent in person.get_parents():
        if has_circular_relationship(parent, visited.copy(), depth + 1):
            return True
    
    # Check children
    for child in person.get_children():
        if has_circular_relationship(child, visited.copy(), depth + 1):
            return True
    
    return False


def get_generation_level(person, root_person=None):
    """Calculate the generation level of a person relative to a root person"""
    if root_person is None:
        # Find the oldest ancestor as root
        current = person
        while current.get_parents():
            current = current.get_parents()[0]
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
        for parent in current_person.get_parents():
            if parent == root_person:
                return -(level + 1)  # Negative for ancestors
            
            if parent.id not in visited:
                visited.add(parent.id)
                queue.append((parent, level + 1))
        
        # Check children (go down one generation)
        for child in current_person.get_children():
            if child == root_person:
                return level + 1  # Positive for descendants
            
            if child.id not in visited:
                visited.add(child.id)
                queue.append((child, level + 1))
    
    return None  # No relationship found


def get_family_statistics():
    """Get statistics about the family tree"""
    from django.db.models import Count, Min, Max
    
    stats = {}
    
    # Basic counts
    stats['total_people'] = Person.objects.count()
    stats['deceased_people'] = Person.objects.filter(is_deceased=True).count()
    stats['living_people'] = stats['total_people'] - stats['deceased_people']
    
    # Gender distribution
    stats['male_count'] = Person.objects.filter(gender='M').count()
    stats['female_count'] = Person.objects.filter(gender='F').count()
    stats['other_gender_count'] = Person.objects.filter(gender='O').count()
    
    # Age statistics
    birth_years = Person.objects.filter(birth_date__isnull=False).aggregate(
        oldest=Min('birth_date__year'),
        youngest=Max('birth_date__year')
    )
    
    if birth_years['oldest'] and birth_years['youngest']:
        stats['oldest_birth_year'] = birth_years['oldest']
        stats['youngest_birth_year'] = birth_years['youngest']
        stats['year_span'] = birth_years['youngest'] - birth_years['oldest']
    
    # Relationship counts
    stats['partnerships'] = Partnership.objects.filter(status='confirmed').count()
    stats['parent_child_relations'] = ParentChild.objects.filter(status='confirmed').count()
    
    # Generation analysis
    generation_levels = []
    root_people = Person.objects.filter(
        parent_relationships__isnull=True
    ).distinct()
    
    for root in root_people:
        levels = []
        descendants = get_all_descendants(root)
        for person in descendants:
            level = get_generation_level(person, root)
            if level is not None:
                levels.append(level)
        
        if levels:
            generation_levels.extend(levels)
    
    if generation_levels:
        stats['max_generations'] = max(generation_levels) - min(generation_levels) + 1
        stats['deepest_generation'] = max(generation_levels)
        stats['highest_generation'] = min(generation_levels)
    
    return stats


def get_all_descendants(person, visited=None):
    """Get all descendants of a person"""
    if visited is None:
        visited = set()
    
    if person.id in visited:
        return []
    
    visited.add(person.id)
    descendants = [person]
    
    for child in person.get_children():
        descendants.extend(get_all_descendants(child, visited))
    
    return descendants