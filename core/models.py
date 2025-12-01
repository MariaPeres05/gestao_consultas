from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UtilizadorManager(BaseUserManager):
    def create_user(self, email, nome, senha=None, **extra_fields):
        if not email:
            raise ValueError("O utilizador deve ter email")

        user = self.model(email=self.normalize_email(email), nome=nome, **extra_fields)
        if not getattr(user, 'data_registo', None):
            user.data_registo = timezone.now()
        user.set_password(senha)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, senha=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, nome, senha, **extra_fields)


class Utilizador(AbstractBaseUser, PermissionsMixin):
    id_utilizador = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    n_utente = models.CharField(max_length=20, null=True, blank=True)
    senha = models.CharField(max_length=255)
    role = models.CharField(max_length=20)
    data_registo = models.DateTimeField()
    ativo = models.BooleanField(default=True)
    foto_perfil = models.TextField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = UtilizadorManager()

    @property
    def is_staff(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return self.ativo

    def __str__(self):
        return self.nome

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.senha = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.senha)


# Minimal additional models to satisfy imports used elsewhere
class Especialidade(models.Model):
    id_especialidade = models.AutoField(primary_key=True)
    nome_especialidade = models.CharField(max_length=255)

    class Meta:
        db_table = '"ESPECIALIDADES"'

    def __str__(self):
        return self.nome_especialidade


class UnidadeSaude(models.Model):
    id_unidade = models.AutoField(primary_key=True)
    nome_unidade = models.CharField(max_length=255)

    class Meta:
        db_table = '"UNIDADE_DE_SAUDE"'

    def __str__(self):
        return self.nome_unidade


class Medico(models.Model):
    id_medico = models.AutoField(primary_key=True, db_column='id_medico')
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='id_utilizador', related_name='medicos')
    numero_ordem = models.CharField(max_length=50, db_column='numero_ordem')
    id_especialidade = models.ForeignKey(Especialidade, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_especialidade', related_name='medicos')

    class Meta:
        db_table = '"MEDICOS"'

    def __str__(self):
        return f"Medico {self.id_medico} - {self.id_utilizador.email}"


class Paciente(models.Model):
    id_paciente = models.AutoField(primary_key=True, db_column='id_paciente')
    id_utilizador = models.ForeignKey(Utilizador, on_delete=models.CASCADE, db_column='id_utilizador', related_name='pacientes')
    data_nasc = models.DateField(null=True, db_column='data_nasc')

    class Meta:
        db_table = '"PACIENTES"'

    def __str__(self):
        return f"Paciente {self.id_paciente} - {self.id_utilizador.email}"


class Disponibilidade(models.Model):
    id_disponibilidade = models.AutoField(primary_key=True, db_column='id_disponibilidade')
    id_medico = models.ForeignKey(Medico, on_delete=models.CASCADE, db_column='id_medico', related_name='disponibilidades')
    id_unidade = models.ForeignKey(UnidadeSaude, on_delete=models.CASCADE, db_column='id_unidade', related_name='disponibilidades')
    data = models.DateField(db_column='data')
    hora_inicio = models.TimeField(db_column='hora_inicio')
    hora_fim = models.TimeField(db_column='hora_fim')
    duracao_slot = models.IntegerField(default=30, db_column='duracao_slot')
    status_slot = models.CharField(max_length=20, default='open', db_column='status_slot')

    class Meta:
        db_table = '"DISPONIBILIDADE"'

    def __str__(self):
        return f"{self.id_medico} @ {self.id_unidade} - {self.data}"


class Consulta(models.Model):
    id_consulta = models.AutoField(primary_key=True, db_column='id_consulta')
    id_paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, db_column='id_paciente', related_name='consultas')
    id_medico = models.ForeignKey(Medico, on_delete=models.CASCADE, db_column='id_medico', related_name='consultas')
    id_disponibilidade = models.ForeignKey(Disponibilidade, on_delete=models.CASCADE, db_column='id_disponibilidade', related_name='consultas')
    data_consulta = models.DateField(null=True, db_column='data_consulta')
    hora_consulta = models.TimeField(null=True, db_column='hora_consulta')
    estado = models.CharField(max_length=50, default='marcada', db_column='estado')

    class Meta:
        db_table = '"CONSULTAS"'

    def __str__(self):
        return f"Consulta {self.id_consulta} - {self.data_consulta} {self.hora_consulta}"


class Fatura(models.Model):
    id_fatura = models.AutoField(primary_key=True, db_column='id_fatura')
    id_consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, db_column='id_consulta', related_name='faturas')
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='valor')
    metodo_pagamento = models.CharField(max_length=50, null=True, blank=True, db_column='metodo_pagamento')
    estado = models.CharField(max_length=50, default='pendente', db_column='estado')
    data_pagamento = models.DateField(null=True, blank=True, db_column='data_pagamento')

    class Meta:
        db_table = '"FATURAS"'

    def __str__(self):
        return f"Fatura {self.id_fatura} - {self.valor}"
