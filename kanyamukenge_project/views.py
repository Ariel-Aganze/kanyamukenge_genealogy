import logging
from django.http import HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)

def safe_get_user(request):
    """Safely get user from request, handling cases where user is not available"""
    try:
        if hasattr(request, 'user') and request.user.is_authenticated:
            return str(request.user)
        else:
            return "Anonymous"
    except:
        return "Anonymous"

def custom_400_view(request, exception=None):
    """Custom 400 Bad Request handler - FIXED"""
    try:
        user = safe_get_user(request)
        path = getattr(request, 'path', 'Unknown')
        logger.warning(f'400 Error: {path} - User: {user}')
        
        return HttpResponse(
            """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Erreur 400 - Famille KANYAMUKENGE</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; }
                    .error-container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .error-code { font-size: 72px; color: #dc3545; font-weight: bold; margin: 0; }
                    .error-title { font-size: 24px; color: #343a40; margin: 20px 0 10px; }
                    .error-message { color: #6c757d; margin-bottom: 30px; }
                    .home-link { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
                    .home-link:hover { background: #218838; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-code">400</div>
                    <div class="error-title">Requête Invalide</div>
                    <p class="error-message">
                        La requête envoyée au serveur est invalide ou malformée.
                    </p>
                    <a href="/" class="home-link">Retour à l'accueil</a>
                </div>
            </body>
            </html>
            """,
            content_type="text/html",
            status=400
        )
    except Exception as e:
        # Ultimate fallback
        logger.error(f'Error in custom_400_view: {e}')
        return HttpResponse("Bad Request", status=400)

def custom_403_view(request, exception=None):
    """Custom 403 Forbidden handler - FIXED"""
    try:
        user = safe_get_user(request)
        path = getattr(request, 'path', 'Unknown')
        logger.warning(f'403 Error: {path} - User: {user}')
        
        return HttpResponse(
            """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Erreur 403 - Famille KANYAMUKENGE</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; }
                    .error-container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .error-code { font-size: 72px; color: #ffc107; font-weight: bold; margin: 0; }
                    .error-title { font-size: 24px; color: #343a40; margin: 20px 0 10px; }
                    .error-message { color: #6c757d; margin-bottom: 30px; }
                    .home-link { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
                    .home-link:hover { background: #218838; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-code">403</div>
                    <div class="error-title">Accès Interdit</div>
                    <p class="error-message">
                        Vous n'avez pas l'autorisation d'accéder à cette page.
                    </p>
                    <a href="/" class="home-link">Retour à l'accueil</a>
                </div>
            </body>
            </html>
            """,
            content_type="text/html",
            status=403
        )
    except Exception as e:
        logger.error(f'Error in custom_403_view: {e}')
        return HttpResponse("Forbidden", status=403)

def custom_404_view(request, exception=None):
    """Custom 404 Not Found handler - FIXED"""
    try:
        user = safe_get_user(request)
        path = getattr(request, 'path', 'Unknown')
        logger.info(f'404 Error: {path} - User: {user}')
        
        return HttpResponse(
            """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Page Non Trouvée - Famille KANYAMUKENGE</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; }
                    .error-container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .error-code { font-size: 72px; color: #17a2b8; font-weight: bold; margin: 0; }
                    .error-title { font-size: 24px; color: #343a40; margin: 20px 0 10px; }
                    .error-message { color: #6c757d; margin-bottom: 30px; }
                    .home-link { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
                    .home-link:hover { background: #218838; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-code">404</div>
                    <div class="error-title">Page Non Trouvée</div>
                    <p class="error-message">
                        La page que vous cherchez n'existe pas ou a été déplacée.
                    </p>
                    <a href="/" class="home-link">Retour à l'accueil</a>
                </div>
            </body>
            </html>
            """,
            content_type="text/html",
            status=404
        )
    except Exception as e:
        logger.error(f'Error in custom_404_view: {e}')
        return HttpResponse("Not Found", status=404)

def custom_500_view(request):
    """Custom 500 Internal Server Error handler - FIXED"""
    try:
        user = safe_get_user(request)
        path = getattr(request, 'path', 'Unknown')
        logger.error(f'500 Error: {path} - User: {user}')
        
        return HttpResponse(
            """
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Erreur Serveur - Famille KANYAMUKENGE</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; }
                    .error-container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .error-code { font-size: 72px; color: #dc3545; font-weight: bold; margin: 0; }
                    .error-title { font-size: 24px; color: #343a40; margin: 20px 0 10px; }
                    .error-message { color: #6c757d; margin-bottom: 30px; }
                    .home-link { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
                    .home-link:hover { background: #218838; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-code">500</div>
                    <div class="error-title">Erreur Interne du Serveur</div>
                    <p class="error-message">
                        Une erreur s'est produite sur le serveur. Nos équipes ont été notifiées.
                    </p>
                    <a href="/" class="home-link">Retour à l'accueil</a>
                </div>
            </body>
            </html>
            """,
            content_type="text/html",
            status=500
        )
    except Exception as e:
        # Ultimate fallback - no logging to avoid recursion
        return HttpResponse("Internal Server Error", status=500)