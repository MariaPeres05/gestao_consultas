# core/admin.py
from django.contrib import admin
from .models import Utilizador

@admin.register(Utilizador)
class UtilizadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "role", "ativo")
    search_fields = ("nome", "email")
    list_filter = ("role", "ativo")

