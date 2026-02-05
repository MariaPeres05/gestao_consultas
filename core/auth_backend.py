from django.contrib.auth.backends import BaseBackend
from .models import Utilizador


class UtilizadorBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            user = Utilizador.objects.get(email=email)
        except Utilizador.DoesNotExist:
            return None

        if user.check_password(password) and user.ativo:
            return user
        return None

    def get_user(self, user_id):
        try:
            return Utilizador.objects.get(pk=user_id)
        except Utilizador.DoesNotExist:
            return None
