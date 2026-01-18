# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# ---------- Custom user manager (simples) ----------
class UtilizadorManager(BaseUserManager):
    def _generate_n_utente(self):
        """Generate unique numero de utente (10 digits)"""
        import random
        while True:
            n_utente = ''.join([str(random.randint(0, 9)) for _ in range(10)])
            if not self.filter(n_utente=n_utente).exists():
                return n_utente
    
    def create_user(self, email, nome, senha=None, **extra_fields):
        if not email:
            raise ValueError("O utilizador deve ter email")

        # Remove n_utente if provided (it will be auto-generated)
        extra_fields.pop('n_utente', None)
        
        user = self.model(
            email=self.normalize_email(email),
            nome=nome,
            **extra_fields
        )
        # Garantir que data_registo está preenchida
        if not getattr(user, 'data_registo', None):
            user.data_registo = timezone.now()
        
        # Auto-generate n_utente
        user.n_utente = self._generate_n_utente()

        user.set_password(senha)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, senha=None, **extra_fields):
        # Remove is_staff if present (it's a property based on role)
        extra_fields.pop("is_staff", None)
        # Set role to admin which makes is_staff=True automatically
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, nome, senha, **extra_fields)


class Utilizador(AbstractBaseUser, PermissionsMixin):
    id_utilizador = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    n_utente = models.CharField(max_length=20, null=True, blank=True)
    # Note: password field is inherited from AbstractBaseUser
    # explicit role choices
    ROLE_PACIENTE = "paciente"
    ROLE_MEDICO = "medico"
    ROLE_ENFERMEIRO = "enfermeiro"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_PACIENTE, "Paciente"),
        (ROLE_MEDICO, "Médico"),
        (ROLE_ENFERMEIRO, "Enfermeiro"),
        (ROLE_ADMIN, "Administrador"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PACIENTE)
    data_registo = models.DateTimeField()
    ativo = models.BooleanField(default=True)
    foto_perfil = models.TextField(null=True, blank=True)
    
    # Email verification fields
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, null=True, blank=True)
    reset_token = models.CharField(max_length=100, null=True, blank=True)
    reset_token_expires = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects = UtilizadorManager()

    @property
    def is_staff(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_active(self):
        return self.ativo

    def __str__(self):
        return self.nome

    # convenience helpers
    @property
    def is_paciente(self):
        return self.role == self.ROLE_PACIENTE

    @property
    def is_medico(self):
        return self.role == self.ROLE_MEDICO

    @property
    def is_enfermeiro(self):
        return self.role == self.ROLE_ENFERMEIRO

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    # Note: set_password and check_password are inherited from AbstractBaseUser
    # and work correctly with the 'password' field

# ---------- Regiao ----------
class Regiao(models.Model):
    id_regiao = models.AutoField(primary_key=True, db_column='id_regiao')
    nome = models.CharField(max_length=50, db_column='nome')
    tipo_regiao = models.CharField(max_length=50, db_column='tipo_regiao')

    class Meta:
        db_table = '"REGIAO"'

    def __str__(self):
        return self.nome

# ---------- Unidade de Saude ----------
class UnidadeSaude(models.Model):
    id_unidade = models.AutoField(primary_key=True, db_column='id_unidade')
    id_regiao = models.ForeignKey(Regiao, on_delete=models.CASCADE, db_column='id_regiao', related_name='unidades')
    nome_unidade = models.CharField(max_length=255, db_column='nome_unidade')
    morada_unidade = models.CharField(max_length=255, db_column='morada_unidade')
    tipo_unidade = models.CharField(max_length=255, db_column='tipo_unidade')

    class Meta:
        db_table = '"UNIDADE_DE_SAUDE"'

    def __str__(self):
        return self.nome_unidade

# ---------- Especialidades ----------
class Especialidade(models.Model):
    id_especialidade = models.AutoField(primary_key=True, db_column='id_especialidade')
    nome_especialidade = models.CharField(max_length=255, db_column='nome_especialidade')
    descricao = models.CharField(max_length=255, blank=True, null=True, db_column='descricao')

    class Meta:
        db_table = '"ESPECIALIDADES"'

    def __str__(self):
        return self.nome_especialidade

# ---------- Medicos ----------
class Medico(models.Model):
    id_medico = models.AutoField(primary_key=True, db_column='id_medico')
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='id_utilizador', related_name='medicos')
    numero_ordem = models.CharField(max_length=50, db_column='numero_ordem')
    id_especialidade = models.ForeignKey(Especialidade, on_delete=models.SET_NULL, db_column='id_especialidade', blank=True, null=True, related_name='medicos')

    class Meta:
        db_table = '"MEDICOS"'

    def __str__(self):
        return f"Medico {self.id_medico} - user {self.id_utilizador.email}"

# ---------- Enfermeiro ----------
class Enfermeiro(models.Model):
    id_enfermeiro = models.AutoField(primary_key=True, db_column='id_enfermeiro')
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='id_utilizador', related_name='enfermeiros')
    n_ordem_enf = models.CharField(max_length=50, db_column='n_ordem_enf')

    class Meta:
        db_table = '"ENFERMEIRO"'

    def __str__(self):
        return f"Enf. {self.id_enfermeiro} - user {self.id_utilizador.email}"

# ---------- Pacientes ----------
class Paciente(models.Model):
    id_paciente = models.AutoField(primary_key=True, db_column='id_paciente')
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='id_utilizador', related_name='pacientes')
    data_nasc = models.DateField(db_column='data_nasc')
    genero = models.CharField(max_length=50, db_column='genero')
    morada = models.CharField(max_length=255, blank=True, null=True, db_column='morada')
    alergias = models.CharField(max_length=255, blank=True, null=True, db_column='alergias')
    observacoes = models.CharField(max_length=255, blank=True, null=True, db_column='observacoes')

    class Meta:
        db_table = '"PACIENTES"'

    def __str__(self):
        return f"Paciente {self.id_paciente} - user {self.id_utilizador.email}"

# ---------- Disponibilidade ----------
class Disponibilidade(models.Model):
    id_disponibilidade = models.AutoField(primary_key=True, db_column='id_disponibilidade')
    id_medico = models.ForeignKey(Medico, on_delete=models.CASCADE, db_column='id_medico', related_name='disponibilidades')
    id_unidade = models.ForeignKey(UnidadeSaude, on_delete=models.CASCADE, db_column='id_unidade', related_name='disponibilidades')
    data = models.DateField(db_column='data')
    hora_inicio = models.TimeField(db_column='hora_inicio')
    hora_fim = models.TimeField(db_column='hora_fim')
    duracao_slot = models.IntegerField(db_column='duracao_slot')
    status_slot = models.CharField(max_length=20, db_column='status_slot')

    class Meta:
        db_table = '"DISPONIBILIDADE"'

    def __str__(self):
        return f"{self.id_medico} @ {self.id_unidade} - {self.data}"

# ---------- Consultas ----------
class Consulta(models.Model):
    id_consulta = models.AutoField(primary_key=True, db_column='id_consulta')
    id_paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, db_column='id_paciente', related_name='consultas')
    id_medico = models.ForeignKey(Medico, on_delete=models.CASCADE, db_column='id_medico', blank=True, null=True, related_name='consultas')
    id_disponibilidade = models.ForeignKey(Disponibilidade, on_delete=models.CASCADE, db_column='id_disponibilidade', blank=True, null=True, related_name='consultas')
    data_consulta = models.DateField(db_column='data_consulta')
    hora_consulta = models.TimeField(db_column='hora_consulta')
    estado = models.CharField(max_length=50, db_column='estado')
    motivo = models.CharField(max_length=255, blank=True, null=True, db_column='motivo')
    medico_aceitou = models.BooleanField(default=False, db_column='medico_aceitou')
    paciente_aceitou = models.BooleanField(default=False, db_column='paciente_aceitou')
    
    # RF-22: Clinical notes and observations
    notas_clinicas = models.TextField(blank=True, null=True, db_column='notas_clinicas', help_text='Resumo clínico da consulta')
    observacoes = models.TextField(blank=True, null=True, db_column='observacoes', help_text='Observações adicionais')
    
    # RF-21: Check-in workflow
    paciente_presente = models.BooleanField(default=False, db_column='paciente_presente', help_text='Check-in realizado')
    hora_checkin = models.DateTimeField(blank=True, null=True, db_column='hora_checkin')
    hora_inicio_real = models.DateTimeField(blank=True, null=True, db_column='hora_inicio_real', help_text='Hora real de início')
    hora_fim_real = models.DateTimeField(blank=True, null=True, db_column='hora_fim_real', help_text='Hora real de término')
    
    # RF-33: Audit trail
    criado_por = models.ForeignKey('Utilizador', on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='consultas_criadas', db_column='criado_por')
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True, db_column='criado_em')
    modificado_por = models.ForeignKey('Utilizador', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='consultas_modificadas', db_column='modificado_por')
    modificado_em = models.DateTimeField(auto_now=True, null=True, blank=True, db_column='modificado_em')

    class Meta:
        db_table = '"CONSULTAS"'

    def __str__(self):
        return f"Consulta {self.id_consulta} - {self.data_consulta} {self.hora_consulta}"

# ---------- Faturas ----------
class Fatura(models.Model):
    id_fatura = models.AutoField(primary_key=True, db_column='id_fatura')
    id_consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, db_column='id_consulta', related_name='faturas')
    valor = models.DecimalField(max_digits=10, decimal_places=2, db_column='valor')
    metodo_pagamento = models.CharField(max_length=50, db_column='metodo_pagamento')
    estado = models.CharField(max_length=50, db_column='estado')
    data_pagamento = models.DateField(blank=True, null=True, db_column='data_pagamento')

    class Meta:
        db_table = '"FATURAS"'

    def __str__(self):
        return f"Fatura {self.id_fatura} - {self.valor}"

# ---------- Receitas ----------
class Receita(models.Model):
    id_receita = models.AutoField(primary_key=True, db_column='id_receita')
    id_consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, db_column='id_consulta', related_name='receitas')
    medicamento = models.CharField(max_length=255, db_column='medicamento')
    dosagem = models.CharField(max_length=255, db_column='dosagem')
    instrucoes = models.CharField(max_length=255, blank=True, null=True, db_column='instrucoes')
    data_prescricao = models.DateField(db_column='data_prescricao')

    class Meta:
        db_table = '"RECEITAS"'

    def __str__(self):
        return f"Receita {self.id_receita} - {self.medicamento}"
