from django.contrib import admin

from .models import AdminCharacter, Character, Settings


@admin.register(AdminCharacter)
class AdminCharacterAdmin(admin.ModelAdmin):
    list_display = ("eve_character", "corporation", "created_at")
    list_filter = ("created_at",)
    search_fields = ("eve_character__character_name",)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("eve_character", "life_credits", "life_taxes", "created_at")
    list_filter = ("created_at",)
    search_fields = ("eve_character__character_name",)
    readonly_fields = ("life_credits", "life_taxes", "created_at")


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "interest_rate", "phrase")
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not Settings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
