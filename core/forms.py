# core/forms.py
from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    remember_me = forms.BooleanField(required=False, initial=False, label="Lembrar-me")


class RegisterForm(forms.Form):
    nome = forms.CharField(max_length=255, label="Nome Completo")
    email = forms.EmailField(label="Email")
    telefone = forms.CharField(max_length=20, required=False, label="Telefone")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Password")
    # Note: n_utente is auto-generated, not provided by user

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("As passwords não coincidem")
        return cleaned


class PacienteDetailsForm(forms.Form):
    """Form para paciente preencher/atualizar seus dados pessoais"""
    GENERO_CHOICES = [
        ('Masculino', 'Masculino'),
        ('Feminino', 'Feminino'),
        ('Outro', 'Outro'),
        ('Não especificado', 'Prefiro não especificar'),
    ]
    
    data_nasc = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data de Nascimento"
    )
    genero = forms.ChoiceField(
        choices=GENERO_CHOICES,
        label="Género"
    )
    morada = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Morada"
    )
    alergias = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Alergias (opcional)",
        help_text="Liste quaisquer alergias conhecidas"
    )
    observacoes = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Observações (opcional)",
        help_text="Informações adicionais relevantes para o histórico médico"
    )


class HorarioForm(forms.Form):
    """Form para criar/editar horários recorrentes"""
    DIA_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    unidade = forms.IntegerField(widget=forms.Select(), label="Unidade de Saúde")
    dia_semana = forms.ChoiceField(choices=DIA_SEMANA_CHOICES, label="Dia da Semana")
    hora_inicio = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label="Hora de Início"
    )
    hora_fim = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label="Hora de Fim"
    )
    duracao_slot = forms.IntegerField(
        initial=30,
        min_value=15,
        max_value=120,
        label="Duração do Slot (minutos)"
    )
    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data de Início"
    )
    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Data de Fim (opcional)"
    )
    
    def clean(self):
        cleaned = super().clean()
        hora_inicio = cleaned.get('hora_inicio')
        hora_fim = cleaned.get('hora_fim')
        data_inicio = cleaned.get('data_inicio')
        data_fim = cleaned.get('data_fim')
        
        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            raise forms.ValidationError("Hora de fim deve ser posterior à hora de início")
        
        if data_inicio and data_fim and data_fim < data_inicio:
            raise forms.ValidationError("Data de fim deve ser posterior à data de início")
        
        return cleaned


class IndisponibilidadeForm(forms.Form):
    """Form para registrar indisponibilidades"""
    TIPO_CHOICES = [
        ('ferias', 'Férias'),
        ('ausencia', 'Ausência'),
        ('formacao', 'Formação'),
        ('doenca', 'Doença'),
        ('outro', 'Outro'),
    ]
    
    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data de Início"
    )
    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data de Fim"
    )
    dia_completo = forms.BooleanField(
        required=False,
        initial=True,
        label="Dia Completo"
    )
    hora_inicio = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False,
        label="Hora de Início (se não for dia completo)"
    )
    hora_fim = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False,
        label="Hora de Fim (se não for dia completo)"
    )
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        initial='outro',
        label="Tipo"
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Motivo (opcional)"
    )
    
    def clean(self):
        cleaned = super().clean()
        data_inicio = cleaned.get('data_inicio')
        data_fim = cleaned.get('data_fim')
        dia_completo = cleaned.get('dia_completo')
        hora_inicio = cleaned.get('hora_inicio')
        hora_fim = cleaned.get('hora_fim')
        
        if data_fim and data_inicio and data_fim < data_inicio:
            raise forms.ValidationError("Data de fim deve ser posterior à data de início")
        
        if not dia_completo:
            if not hora_inicio or not hora_fim:
                raise forms.ValidationError("Para período parcial, preencha hora de início e fim")
            if hora_fim <= hora_inicio:
                raise forms.ValidationError("Hora de fim deve ser posterior à hora de início")
        
        return cleaned


class ListaEsperaForm(forms.Form):
    """Form para inscrição em lista de espera"""
    especialidade = forms.IntegerField(widget=forms.Select(), label="Especialidade")
    unidade = forms.IntegerField(
        widget=forms.Select(),
        required=False,
        label="Unidade Preferencial (opcional)"
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observações"
    )

 