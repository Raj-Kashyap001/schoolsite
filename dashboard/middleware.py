from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.core.management import call_command
from django.conf import settings

class DemoSeedResetMiddleware(MiddlewareMixin):
    """
    A lightweight middleware that registers login/logout signal handlers to
    seed and reset demo data when DEMO_MODE is enabled.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Ensure signal receivers are connected once
        # No heavy work per request


@receiver(user_logged_in)
def on_user_logged_in(sender, user, request, **kwargs):  # pragma: no cover
    if getattr(settings, "DEMO_MODE", False):
        # Re-seed to a known baseline at login
        try:
            call_command("demo_seed", reset=True, verbosity=0)
        except Exception:
            # Avoid breaking login flow in demo if seed fails
            pass


@receiver(user_logged_out)
def on_user_logged_out(sender, user, request, **kwargs):  # pragma: no cover
    if getattr(settings, "DEMO_MODE", False):
        # Reset to default when user logs out
        try:
            call_command("demo_seed", reset=True, verbosity=0)
        except Exception:
            # Avoid raising errors on logout in demo
            pass
