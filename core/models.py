# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# ---------- Custom user manager (simples) ----------
class UtilizadorManager(BaseUserManager):
    def create_user(self, email, nome, senha=None, **extra_fields):
        if not email:
            raise ValueError("O utilizador deve ter email")

        user = self.model(
            email=self.normalize_email(email),
            nome=nome,
            **extra_fields
        )
        # Garantir que data_registo está preenchida
        if not getattr(user, 'data_registo', None):
            user.data_registo = timezone.now()

        user.set_password(senha)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, senha=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        return self.create_user(email, nome, senha, **extra_fields)


class Utilizador(AbstractBaseUser, PermissionsMixin):
    id_utilizador = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    n_utente = models.CharField(max_length=20, null=True, blank=True)
    senha = models.CharField(max_length=255)
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


    # override set_password to use bcrypt-compatible crypt()
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.senha = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.senha)

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


class Horario(models.Model):
    """
    RF-09: Modelo para horários recorrentes dos médicos.
    Define padrões semanais que geram disponibilidades automaticamente.
    """
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    id_horario = models.AutoField(primary_key=True)
    medico = models.ForeignKey(
        Medico, 
        on_delete=models.CASCADE,
        related_name='horarios',
        db_column='ID_MEDICO'
    )
    unidade = models.ForeignKey(
        UnidadeSaude,
        on_delete=models.CASCADE,
        related_name='horarios',
        db_column='ID_UNIDADE'
    )
    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA,
        help_text="Dia da semana (0=Segunda, 6=Domingo)"
    )
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    duracao_slot = models.IntegerField(
        default=30,
        help_text="Duração de cada slot em minutos"
    )
    data_inicio = models.DateField(
        help_text="Data a partir da qual este horário é válido"
    )
    data_fim = models.DateField(
        null=True,
        blank=True,
        help_text="Data até a qual este horário é válido (deixe vazio para sem limite)"
    )
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = '"HORARIOS"'
        ordering = ['dia_semana', 'hora_inicio']
        unique_together = ['medico', 'unidade', 'dia_semana', 'hora_inicio']
    
    def __str__(self):
        dia = dict(self.DIAS_SEMANA)[self.dia_semana]
        return f"{self.medico.utilizador.nome} - {dia} {self.hora_inicio}-{self.hora_fim}"
    
    def gerar_disponibilidades(self, data_inicio=None, data_fim=None):
        """
        Gera disponibilidades baseadas neste horário recorrente.
        """
        from datetime import datetime, timedelta
        
        if not self.ativo:
            return 0
        
        # Define o período para gerar disponibilidades
        inicio = data_inicio or self.data_inicio
        fim = data_fim or (self.data_fim if self.data_fim else inicio + timedelta(days=90))
        
        # Encontra o primeiro dia da semana correto
        dias_ate_primeiro = (self.dia_semana - inicio.weekday()) % 7
        data_atual = inicio + timedelta(days=dias_ate_primeiro)
        
        disponibilidades_criadas = 0
        
        while data_atual <= fim:
            # Verifica se há indisponibilidade nesta data
            if not Indisponibilidade.objects.filter(
                medico=self.medico,
                data_inicio__lte=data_atual,
                data_fim__gte=data_atual
            ).exists():
                # Gera slots para este dia
                hora_atual = datetime.combine(data_atual, self.hora_inicio)
                hora_fim = datetime.combine(data_atual, self.hora_fim)
                
                while hora_atual < hora_fim:
                    # Verifica se já existe disponibilidade para este horário
                    if not Disponibilidade.objects.filter(
                        medico=self.medico,
                        unidade=self.unidade,
                        data=data_atual,
                        hora_inicio=hora_atual.time()
                    ).exists():
                        Disponibilidade.objects.create(
                            medico=self.medico,
                            unidade=self.unidade,
                            data=data_atual,
                            hora_inicio=hora_atual.time(),
                            hora_fim=(hora_atual + timedelta(minutes=self.duracao_slot)).time(),
                            disponivel=True
                        )
                        disponibilidades_criadas += 1
                    
                    hora_atual += timedelta(minutes=self.duracao_slot)
            
            # Avança para a próxima semana
            data_atual += timedelta(days=7)
        
        return disponibilidades_criadas


class Indisponibilidade(models.Model):
    """
    RF-10: Modelo para registrar períodos de indisponibilidade dos médicos.
    Separado do modelo Disponibilidade para melhor gestão.
    """
    TIPO_CHOICES = [
        ('ferias', 'Férias'),
        ('ausencia', 'Ausência'),
        ('formacao', 'Formação'),
        ('doenca', 'Doença'),
        ('outro', 'Outro'),
    ]
    
    id_indisponibilidade = models.AutoField(primary_key=True)
    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name='indisponibilidades',
        db_column='ID_MEDICO'
    )
    data_inicio = models.DateField()
    data_fim = models.DateField()
    hora_inicio = models.TimeField(
        null=True,
        blank=True,
        help_text="Deixe vazio para dia completo"
    )
    hora_fim = models.TimeField(
        null=True,
        blank=True,
        help_text="Deixe vazio para dia completo"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='outro'
    )
    motivo = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = '"INDISPONIBILIDADES"'
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"{self.medico.utilizador.nome} - {self.data_inicio} a {self.data_fim}"
    
    def clean(self):
        """Validação personalizada"""
        from django.core.exceptions import ValidationError
        
        if self.data_fim < self.data_inicio:
            raise ValidationError("Data de fim deve ser posterior à data de início")
        
        if self.hora_inicio and self.hora_fim:
            if self.hora_fim <= self.hora_inicio:
                raise ValidationError("Hora de fim deve ser posterior à hora de início")
        
        # Ambas as horas devem ser preenchidas ou ambas vazias
        if (self.hora_inicio and not self.hora_fim) or (not self.hora_inicio and self.hora_fim):
            raise ValidationError("Preencha ambas as horas ou deixe ambas vazias para dia completo")
    
    def cancelar_disponibilidades(self):
        """
        Cancela ou marca como indisponíveis as disponibilidades no período.
        """
        filtros = {
            'medico': self.medico,
            'data__gte': self.data_inicio,
            'data__lte': self.data_fim,
            'disponivel': True
        }
        
        if self.hora_inicio and self.hora_fim:
            # Indisponibilidade parcial (apenas certas horas)
            filtros['hora_inicio__gte'] = self.hora_inicio
            filtros['hora_inicio__lt'] = self.hora_fim
        
        disponibilidades = Disponibilidade.objects.filter(**filtros)
        count = disponibilidades.update(disponivel=False)
        
        return count


class ListaEspera(models.Model):
    """
    RF-13: Modelo para lista de espera de consultas.
    Permite que pacientes se inscrevam quando não há disponibilidade.
    """
    STATUS_CHOICES = [
        ('aguardando', 'Aguardando'),
        ('notificado', 'Notificado'),
        ('atendido', 'Atendido'),
        ('cancelado', 'Cancelado'),
    ]
    
    PRIORIDADE_CHOICES = [
        (1, 'Baixa'),
        (2, 'Normal'),
        (3, 'Alta'),
        (4, 'Urgente'),
    ]
    
    id_lista_espera = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='listas_espera',
        db_column='ID_PACIENTE'
    )
    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.CASCADE,
        related_name='listas_espera',
        db_column='ID_ESPECIALIDADE'
    )
    unidade = models.ForeignKey(
        UnidadeSaude,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listas_espera',
        db_column='ID_UNIDADE',
        help_text="Unidade preferencial (opcional)"
    )
    data_inscricao = models.DateTimeField(auto_now_add=True)
    prioridade = models.IntegerField(
        choices=PRIORIDADE_CHOICES,
        default=2
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='aguardando'
    )
    observacoes = models.TextField(blank=True)
    data_notificacao = models.DateTimeField(null=True, blank=True)
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lista_espera',
        db_column='ID_CONSULTA',
        help_text="Consulta agendada após notificação"
    )
    
    class Meta:
        db_table = '"LISTAS_ESPERA"'
        ordering = ['-prioridade', 'data_inscricao']
    
    def __str__(self):
        return f"{self.paciente.utilizador.nome} - {self.especialidade.designacao} ({self.get_status_display()})"
    
    def notificar_paciente(self, disponibilidade=None):
        """
        Notifica o paciente sobre disponibilidade.
        """
        from django.utils import timezone
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        if self.status != 'aguardando':
            return False
        
        self.status = 'notificado'
        self.data_notificacao = timezone.now()
        self.save()
        
        # Enviar email de notificação
        context = {
            'paciente': self.paciente,
            'especialidade': self.especialidade,
            'disponibilidade': disponibilidade,
        }
        
        try:
            mensagem = render_to_string('emails/notificacao_lista_espera.html', context)
            send_mail(
                subject=f'Vaga disponível - {self.especialidade.designacao}',
                message='',
                html_message=mensagem,
                from_email='noreply@gestao-consultas.pt',
                recipient_list=[self.paciente.utilizador.email],
                fail_silently=False,
            )
            return True
        except Exception:
            return False
