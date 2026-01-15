from django import forms
from django.contrib.auth.models import User

from .models import Character, CharacterTaxCredits


class AddCharacterForm(forms.Form):
    """Form for adding a character to track."""
    character = forms.ModelChoiceField(
        queryset=None,
        label="Select Character",
        help_text="Choose a character to add to PVE Taxes tracking"
    )

    def __init__(self, user: User, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get user's characters that aren't already registered
        from allianceauth.eveonline.models import EveCharacter
        registered_ids = Character.objects.values_list(
            "eve_character__character_id", flat=True
        )
        self.fields["character"].queryset = (
            EveCharacter.objects
            .filter(character_ownership__user=user)
            .exclude(character_id__in=registered_ids)
        )


class TaxCreditForm(forms.ModelForm):
    """Form for adding tax credits/debits."""
    
    class Meta:
        model = CharacterTaxCredits
        fields = ["character", "amount", "credit_type", "reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "amount": "Positive for credit, negative for debit",
            "reason": "Explain why this credit/debit is being applied",
        }
