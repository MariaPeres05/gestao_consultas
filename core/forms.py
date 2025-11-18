# core/forms.py
from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")


class RegisterForm(forms.Form):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    telefone = forms.CharField(max_length=20, required=False)
    n_utente = forms.CharField(max_length=20, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("As passwords não coincidem")
        return cleaned
 