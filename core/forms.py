# core/forms.py
from django import forms
from .models import Utilizador


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    remember_me = forms.BooleanField(required=False, initial=False, label="Lembrar-me")


class RegisterForm(forms.Form):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    telefone = forms.CharField(max_length=20, required=False)
    n_utente = forms.CharField(max_length=20, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Utilizador.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email já está registado. Por favor, use outro email ou faça login.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("As passwords não coincidem")
        return cleaned
 