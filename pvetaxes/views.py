from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models

from .decorators import main_character_required
from .models import Character, Stats, Settings
from .tasks import update_character_wallet, update_stats


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
@main_character_required
def index(request):
    """Main landing page."""
    stats = Stats.load()
    
    context = {
        "stats": stats,
        "has_characters": Character.objects.filter(
            eve_character__character_ownership__user=request.user
        ).exists(),
    }
    
    return render(request, "pvetaxes/index.html", context)


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
@main_character_required
def launcher(request):
    """Character launcher page."""
    characters = Character.objects.filter(
        eve_character__character_ownership__user=request.user
    )
    
    context = {
        "characters": characters,
    }
    
    return render(request, "pvetaxes/launcher.html", context)


@login_required
@permission_required("pvetaxes.admin_access", raise_exception=True)
def admin_launcher(request):
    """Admin launcher page."""
    from .models import AdminCharacter
    
    admins = AdminCharacter.objects.all()
    characters = Character.objects.all()
    
    context = {
        "admins": admins,
        "total_characters": characters.count(),
    }
    
    return render(request, "pvetaxes/admin_launcher.html", context)


@login_required
@permission_required("pvetaxes.admin_access", raise_exception=True)
def admin_tables(request):
    """Admin tables view."""
    stats = Stats.load()
    
    context = {
        "stats": stats,
    }
    
    return render(request, "pvetaxes/admin_tables.html", context)


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
@main_character_required
def user_summary(request):
    """User's tax summary."""
    characters = Character.objects.filter(
        eve_character__character_ownership__user=request.user
    )
    
    total_taxes = 0
    total_credits = 0
    total_balance = 0
    
    for char in characters:
        char_taxes = char.wallet_journal.aggregate(
            total=models.Sum("tax_amount")
        )["total"] or 0
        total_taxes += char_taxes
        total_credits += char.life_credits
    
    total_balance = total_taxes - total_credits
    
    context = {
        "characters": characters,
        "total_taxes": total_taxes,
        "total_credits": total_credits,
        "total_balance": total_balance,
    }
    
    return render(request, "pvetaxes/user_summary.html", context)


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
def user_ledger(request, character_id):
    """Detailed ledger for a character."""
    character = get_object_or_404(Character, pk=character_id)
    
    # Check permissions
    if not character.user_is_owner(request.user):
        if not request.user.has_perm("pvetaxes.auditor_access"):
            return render(request, "pvetaxes/error.html", {
                "error_title": "Access Denied",
                "error_message": "You don't have permission to view this character."
            })
    
    journal_entries = character.wallet_journal.all()[:100]  # Limit to recent 100
    credits = character.tax_credits.all()[:50]
    
    context = {
        "character": character,
        "journal_entries": journal_entries,
        "credits": credits,
    }
    
    return render(request, "pvetaxes/user_ledger.html", context)


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
def character_viewer(request, character_id):
    """Character viewer page."""
    character = get_object_or_404(Character, pk=character_id)
    
    # Check permissions
    if not character.user_is_owner(request.user):
        if not request.user.has_perm("pvetaxes.auditor_access"):
            return render(request, "pvetaxes/error.html", {
                "error_title": "Access Denied",
                "error_message": "You don't have permission to view this character."
            })
    
    context = {
        "character": character,
    }
    
    return render(request, "pvetaxes/character_viewer.html", context)


@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
def faq(request):
    """FAQ page."""
    return render(request, "pvetaxes/faq.html")


# API endpoints for AJAX
@login_required
@permission_required("pvetaxes.basic_access", raise_exception=True)
def api_update_character(request, character_id):
    """Trigger character update via AJAX."""
    character = get_object_or_404(Character, pk=character_id)
    
    if not character.user_is_owner(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)
    
    update_character_wallet.delay(character_id)
    
    return JsonResponse({"status": "Update started"})
