from django.apps import AppConfig

from . import __version__


class PvetaxesConfig(AppConfig):
    name = "pvetaxes"
    label = "pvetaxes"
    verbose_name = f"PVE Taxes v{__version__}"
    default_auto_field = 'django.db.models.AutoField'
