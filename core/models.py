# core/models.py - VERSÃO CORRIGIDA
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class UtilizadorManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 5)
        extra_fields.setdefault('ativo', 1)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Utilizador(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        (1, 'Paciente'),
        (2, 'Médico'),
        (3, 'Administrativo'),
        (4, 'Enfermeiro'),
        (5, 'Superuser'),
    ]
    
    id_utilizador = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50, default='N/A')
    email = models.EmailField(max_length=255, unique=True)
    telefone = models.CharField(max_length=15, default='000000000')
    n_utente = models.CharField(max_length=15, default='000000000')
    senha = models.CharField(max_length=255)
    role = models.IntegerField(choices=ROLE_CHOICES, default=1)
    data_registo = models.DateTimeField(default=timezone.now)
    ativo = models.SmallIntegerField(default=1)
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name="utilizador_set",
        related_query_name="utilizador",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name="utilizador_set",
        related_query_name="utilizador",
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nomeregiao', 'telefone', 'n_utente']
    
    objects = UtilizadorManager()
    
    class Meta:
        db_table = '"UTILIZADOR"'
    
    def __str__(self):
        return f"{self.nomeregiao} ({self.email})"
    
    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, 'Desconhecido')

# Modelos básicos (mantenha os que já tem)
class Regiao(models.Model):
    id_regiao = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50)
    tiporegiao = models.CharField(max_length=50)
    
    class Meta:
        db_table = '"REGIAO"'

class UnidadeSaude(models.Model):
    id_unidade = models.AutoField(primary_key=True)
    id_regiao = models.ForeignKey(Regiao, on_delete=models.CASCADE, db_column='ID_REGIAO')
    nome_unidade = models.CharField(max_length=255)
    morada_unidade = models.CharField(max_length=255)
    tipo_unidade = models.CharField(max_length=255)
    
    class Meta:
        db_table = '"UNIDADE_DE_SAUDE"'

class Especialidades(models.Model):
    id_especialidades = models.AutoField(primary_key=True)
    nome_especialidade = models.CharField(max_length=1024)
    descricao = models.CharField(max_length=1024)
    
    class Meta:
        db_table = '"ESPECIALIDADES"'

class Horarios(models.Model):
    id_horario = models.AutoField(primary_key=True)
    hora_inicio = models.CharField(max_length=255)
    hora_fim = models.CharField(max_length=255)
    tipo = models.CharField(max_length=255)
    dias_semana = models.CharField(max_length=255)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    duracao = models.CharField(max_length=255)
    
    class Meta:
        db_table = '"HORARIOS"'

# Modelos com estrutura COMPATÍVEL com a BD
class Medicos(models.Model):
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='ID_UTILIZADOR')
    id_medico = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    telefone = models.CharField(max_length=15)
    n_utente = models.CharField(max_length=15)
    senha = models.CharField(max_length=255)
    role = models.IntegerField()
    data_registo = models.DateTimeField()
    ativo = models.SmallIntegerField()
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)
    numero_ordem = models.CharField(max_length=1024)
    
    class Meta:
        db_table = '"MEDICOS"'
        unique_together = (('id_utilizador', 'id_medico'),)

class Pacientes(models.Model):
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='ID_UTILIZADOR')
    id_paciente = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    telefone = models.CharField(max_length=15)
    n_utente = models.CharField(max_length=15)
    senha = models.CharField(max_length=255)
    role = models.IntegerField()
    data_registo = models.DateTimeField()
    ativo = models.SmallIntegerField()
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)
    data_nasc = models.DateField()
    genero = models.CharField(max_length=255)
    morada = models.CharField(max_length=255, blank=True, null=True)
    alergias = models.CharField(max_length=255, blank=True, null=True)
    observacoes = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = '"PACIENTES"'
        unique_together = (('id_utilizador', 'id_paciente'),)

# Adicione também estes modelos que faltam:
class Enfermeiro(models.Model):
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='ID_UTILIZADOR')
    id_enfermeiro = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    telefone = models.CharField(max_length=15)
    n_utente = models.CharField(max_length=15)
    senha = models.CharField(max_length=255)
    role = models.IntegerField()
    data_registo = models.DateTimeField()
    ativo = models.SmallIntegerField()
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)
    n_ordem_enf = models.CharField(max_length=255)
    
    class Meta:
        db_table = '"ENFERMEIRO"'
        unique_together = (('id_utilizador', 'id_enfermeiro'),)

class Administrativo(models.Model):
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='ID_UTILIZADOR')
    id_admin = models.AutoField(primary_key=True)
    nomeregiao = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    telefone = models.CharField(max_length=15)
    n_utente = models.CharField(max_length=15)
    senha = models.CharField(max_length=255)
    role = models.IntegerField()
    data_registo = models.DateTimeField()
    ativo = models.SmallIntegerField()
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = '"ADMINISTRATIVO"'
        unique_together = (('id_utilizador', 'id_admin'),)

# Mantenha os outros modelos (Consultas, Faturas, Receitas) como estão
class Consultas(models.Model):
    ESTADO_CHOICES = [
        ('agendada', 'Agendada'),
        ('confirmada', 'Confirmada'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]
    
    id_consultas = models.AutoField(primary_key=True, db_column='ID_CONSULTAS')
    id_fatura = models.IntegerField(blank=True, null=True)
    id_horario = models.ForeignKey(Horarios, on_delete=models.CASCADE, db_column='ID_HORARIO')
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    estado = models.CharField(max_length=255, choices=ESTADO_CHOICES)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = '"CONSULTAS"'

class Faturas(models.Model):
    id_fatura = models.AutoField(primary_key=True)
    id_consultas = models.ForeignKey(Consultas, on_delete=models.CASCADE, db_column='ID_CONSULTAS')
    valor = models.CharField(max_length=255)
    metodo_pagamento = models.CharField(max_length=255)
    estado = models.CharField(max_length=255)
    data_pagamento = models.CharField(max_length=255)
    
    class Meta:
        db_table = '"FATURAS"'

class Receitas(models.Model):
    id_receita = models.AutoField(primary_key=True, db_column='ID_RECEITA')
    id_consultas = models.ForeignKey(Consultas, on_delete=models.CASCADE, db_column='ID_CONSULTAS')
    id_fatura = models.ForeignKey(Faturas, on_delete=models.CASCADE, db_column='ID_FATURA')
    medicamento = models.CharField(max_length=255)
    dosagem = models.CharField(max_length=255)
    instrucoes = models.CharField(max_length=255)
    data_prescricao = models.DateField()
    
    class Meta:
        db_table = '"RECEITAS"'
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'