#core/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Receitas, Consultas, Faturas, Utilizador


class ReceitaForm(forms.ModelForm):
    class Meta:
        model = Receitas
        fields = ['id_consultas', 'id_fatura', 'medicamento', 'dosagem', 'instrucoes', 'data_prescricao']
        widgets = {
            'data_prescricao': forms.DateInput(attrs={'type': 'date'}),
            'medicamento': forms.TextInput(attrs={'class': 'form-control'}),
            'dosagem': forms.TextInput(attrs={'class': 'form-control'}),
            'instrucoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_consultas'].queryset = Consultas.objects.filter(estado='concluida')

class FaturaForm(forms.ModelForm):
    class Meta:
        model = Faturas
        fields = ['id_consultas', 'valor', 'metodo_pagamento', 'estado', 'data_pagamento']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
            'valor': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_pagamento': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(choices=[
                ('pendente', 'Pendente'),
                ('pago', 'Pago'),
                ('cancelada', 'Cancelada')
            ])
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # permitir seleccionar apenas consultas concluídas (ou todas se já associada)
        try:
            self.fields['id_consultas'].queryset = Consultas.objects.filter(estado='concluida')
        except Exception:
            # fallback caso a tabela de consultas não exista ou haja erro
            pass

    def clean_valor(self):
        val = self.cleaned_data.get('valor')
        if not val:
            raise forms.ValidationError('O valor é obrigatório.')
        # validação simples: permitir números com vírgula/ponto; podes adaptar
        try:
            # substitui , por . se necessário e verifica conversão
            _ = float(str(val).replace(',', '.'))
        except Exception:
            raise forms.ValidationError('Valor inválido. Usa um número, ex: 50.00')
        return val

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

class RegistroForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label="Confirmar Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar Password'
        })
    )
    
    class Meta:
        model = Utilizador
        fields = ['nomeregiao', 'email', 'telefone', 'n_utente', 'role']
        widgets = {
            'nomeregiao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome Completo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Email'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Telefone'
            }),
            'n_utente': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nº Utente'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'nomeregiao': 'Nome Completo',
            'email': 'Email',
            'telefone': 'Telefone',
            'n_utente': 'Número de Utente',
            'role': 'Tipo de Utilizador'
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("As passwords não coincidem")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
    


class ReceitaForm(forms.ModelForm):
    class Meta:
        model = Receitas
        fields = ['id_consultas', 'id_fatura', 'medicamento', 'dosagem', 'instrucoes', 'data_prescricao']
        widgets = {
            'data_prescricao': forms.DateInput(attrs={'type': 'date'}),
            'medicamento': forms.TextInput(attrs={'class': 'form-control'}),
            'dosagem': forms.TextInput(attrs={'class': 'form-control'}),
            'instrucoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_consultas'].queryset = Consultas.objects.filter(estado='concluida')

class FaturaForm(forms.ModelForm):
    class Meta:
        model = Faturas
        fields = ['id_consultas', 'valor', 'metodo_pagamento', 'estado', 'data_pagamento']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
            'valor': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_pagamento': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(choices=[
                ('pendente', 'Pendente'),
                ('pago', 'Pago'),
                ('cancelada', 'Cancelada')
            ])
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['id_consultas'].queryset = Consultas.objects.filter(estado='concluida')
        except Exception:
            pass

    def clean_valor(self):
        val = self.cleaned_data.get('valor')
        if not val:
            raise forms.ValidationError('O valor é obrigatório.')
        try:
            _ = float(str(val).replace(',', '.'))
        except Exception:
            raise forms.ValidationError('Valor inválido. Usa um número, ex: 50.00')
        return val