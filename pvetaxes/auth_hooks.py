from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class PvetaxesMenuItem(MenuItemHook):
    """Menu item for PVE Taxes"""
    
    def __init__(self):
        MenuItemHook.__init__(
            self,
            "PVE Taxes",
            "fa fa-coins",
            "pvetaxes:index",
            navactive=["pvetaxes:"],
        )

    def render(self, request):
        if request.user.has_perm("pvetaxes.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return PvetaxesMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "pvetaxes", r"^pvetaxes/")
