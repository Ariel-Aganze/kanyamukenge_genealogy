from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest
import logging

logger = logging.getLogger(__name__)

def custom_404_view(request, exception=None):
    """
    Custom 404 error handler
    """
    # Log the 404 error for monitoring
    logger.warning(f'404 Error: {request.path} - User: {request.user if request.user.is_authenticated else "Anonymous"}')
    
    context = {
        'request_path': request.path,
        'user': request.user if request.user.is_authenticated else None,
        'error_code': '404',
        'error_title': 'Page introuvable',
        'error_message': 'La page que vous recherchez semble avoir été déplacée, supprimée ou n\'existe pas.',
        'suggestions': [
            'Vérifiez l\'orthographe de l\'adresse',
            'Retournez à la page d\'accueil',
            'Utilisez le menu de navigation pour explorer le site'
        ]
    }
    
    response = render(request, 'errors/404.html', context)
    response.status_code = 404
    return response

def custom_500_view(request):
    """
    Custom 500 error handler
    """
    # Log the 500 error for monitoring
    logger.error(f'500 Error: {request.path} - User: {request.user if request.user.is_authenticated else "Anonymous"}')
    
    context = {
        'request_path': request.path,
        'user': request.user if request.user.is_authenticated else None,
        'error_code': '500',
        'error_title': 'Erreur interne du serveur',
        'error_message': 'Une erreur technique s\'est produite sur notre serveur. Nos équipes ont été informées et travaillent sur une solution.',
        'suggestions': [
            'Rafraîchissez la page dans quelques instants',
            'Retournez à la page d\'accueil',
            'Contactez l\'administrateur si le problème persiste'
        ]
    }
    
    response = render(request, 'errors/500.html', context)
    response.status_code = 500
    return response

def custom_403_view(request, exception=None):
    """
    Custom 403 error handler (Permission Denied)
    """
    logger.warning(f'403 Error: {request.path} - User: {request.user if request.user.is_authenticated else "Anonymous"}')
    
    context = {
        'request_path': request.path,
        'user': request.user if request.user.is_authenticated else None,
        'exception': str(exception) if exception else None,
        'error_code': '403',
        'error_title': 'Accès refusé',
        'error_message': 'Vous n\'avez pas les permissions nécessaires pour accéder à cette page. Cette section est réservée aux membres autorisés de la famille.',
        'suggestions': [
            'Connectez-vous avec un compte autorisé',
            'Contactez l\'administrateur pour demander l\'accès',
            'Retournez à la page d\'accueil'
        ]
    }
    
    response = render(request, 'errors/403.html', context)
    response.status_code = 403
    return response

def custom_400_view(request, exception=None):
    """
    Custom 400 error handler (Bad Request)
    """
    logger.warning(f'400 Error: {request.path} - User: {request.user if request.user.is_authenticated else "Anonymous"}')
    
    context = {
        'request_path': request.path,
        'user': request.user if request.user.is_authenticated else None,
        'exception': str(exception) if exception else None,
        'error_code': '400',
        'error_title': 'Requête incorrecte',
        'error_message': 'La requête envoyée n\'est pas valide ou contient des données incorrectes.',
        'suggestions': [
            'Vérifiez les informations saisies',
            'Retournez à la page précédente',
            'Contactez le support si l\'erreur persiste'
        ]
    }
    
    response = render(request, 'errors/400.html', context)
    response.status_code = 400
    return response