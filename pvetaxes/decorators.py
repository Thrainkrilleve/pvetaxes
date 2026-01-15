from functools import wraps

from django.contrib.auth.decorators import login_required, permission_required
from esi.decorators import token_required


def fetch_token_for_character(*scope_names):
    """Decorator that fetches a valid token for the character and injects it
    into the function as 'token' parameter.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(character, *args, **kwargs):
            token = character.fetch_token(scopes=list(scope_names))
            return func(character, *args, token=token, **kwargs)
        return wrapper
    return decorator


def main_character_required(func):
    """Decorator requiring the user's main character to be set"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.main_character:
            from django.shortcuts import render
            return render(
                request,
                "pvetaxes/error.html",
                {
                    "error_title": "No Main Character",
                    "error_message": "You must set a main character to use PVE Taxes."
                }
            )
        return func(request, *args, **kwargs)
    return wrapper
