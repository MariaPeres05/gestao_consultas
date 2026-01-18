# core/admin.py
from django.contrib import admin
from .models import (
    Utilizador, Regiao, UnidadeSaude, Especialidade, 
    Medico, Enfermeiro, Paciente, Consulta, Fatura, 
    Receita, Disponibilidade
)

@admin.register(Utilizador)
class UtilizadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "role", "ativo", "data_registo")
    search_fields = ("nome", "email")
    list_filter = ("role", "ativo")
    ordering = ("-data_registo",)

@admin.register(Regiao)
class RegiaoAdmin(admin.ModelAdmin):
    list_display = ("id_regiao", "nome", "tipo_regiao")
    search_fields = ("nome",)
    list_filter = ("tipo_regiao",)

@admin.register(UnidadeSaude)
class UnidadeSaudeAdmin(admin.ModelAdmin):
    list_display = ("id_unidade", "nome_unidade", "tipo_unidade", "id_regiao")
    search_fields = ("nome_unidade", "morada_unidade")
    list_filter = ("tipo_unidade", "id_regiao")

@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ("id_especialidade", "nome_especialidade", "descricao")
    search_fields = ("nome_especialidade",)

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ("id_medico", "get_nome", "numero_ordem", "id_especialidade")
    search_fields = ("id_utilizador__nome", "numero_ordem")
    list_filter = ("id_especialidade",)
    
    def get_nome(self, obj):
        return obj.id_utilizador.nome
    get_nome.short_description = "Nome"

@admin.register(Enfermeiro)
class EnfermeiroAdmin(admin.ModelAdmin):
    list_display = ("id_enfermeiro", "get_nome", "n_ordem_enf")
    search_fields = ("id_utilizador__nome", "n_ordem_enf")
    
    def get_nome(self, obj):
        return obj.id_utilizador.nome
    get_nome.short_description = "Nome"

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("id_paciente", "get_nome", "data_nasc", "genero")
    search_fields = ("id_utilizador__nome", "id_utilizador__email")
    list_filter = ("genero",)
    
    def get_nome(self, obj):
        return obj.id_utilizador.nome
    get_nome.short_description = "Nome"

@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ("id_disponibilidade", "get_medico", "id_unidade", "data", "hora_inicio", "hora_fim", "status_slot")
    search_fields = ("id_medico__id_utilizador__nome",)
    list_filter = ("data", "status_slot", "id_unidade")
    date_hierarchy = "data"
    
    def get_medico(self, obj):
        return obj.id_medico.id_utilizador.nome
    get_medico.short_description = "Médico"

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("id_consulta", "get_paciente", "get_medico", "data_consulta", "hora_consulta", "estado")
    search_fields = ("id_paciente__id_utilizador__nome", "id_medico__id_utilizador__nome")
    list_filter = ("estado", "data_consulta")
    date_hierarchy = "data_consulta"
    
    def get_paciente(self, obj):
        return obj.id_paciente.id_utilizador.nome
    get_paciente.short_description = "Paciente"
    
    def get_medico(self, obj):
        return obj.id_medico.id_utilizador.nome
    get_medico.short_description = "Médico"

@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ("id_fatura", "get_consulta_id", "valor", "metodo_pagamento", "estado", "data_pagamento")
    search_fields = ("id_consulta__id_paciente__id_utilizador__nome",)
    list_filter = ("estado", "metodo_pagamento", "data_pagamento")
    
    def get_consulta_id(self, obj):
        return f"Consulta #{obj.id_consulta.id_consulta}"
    get_consulta_id.short_description = "Consulta"

@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ("id_receita", "get_consulta", "medicamento", "dosagem", "data_prescricao")
    search_fields = ("medicamento", "id_consulta__id_paciente__id_utilizador__nome")
    list_filter = ("data_prescricao",)
    date_hierarchy = "data_prescricao"
    
    def get_consulta(self, obj):
        return f"Consulta #{obj.id_consulta.id_consulta}"
    get_consulta.short_description = "Consulta"

