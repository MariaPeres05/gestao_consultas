#!/usr/bin/env python
"""Script de teste para verificar pacientes na base de dados"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_consultas.settings')
django.setup()

from core.models import Paciente, Utilizador
from django.db import connection

print("=" * 60)
print("🔍 TESTE DE PACIENTES NA BASE DE DADOS")
print("=" * 60)

# Teste 1: Contar pacientes via Django ORM
pacientes_orm = Paciente.objects.count()
print(f"\n1. Total de pacientes (ORM): {pacientes_orm}")

# Teste 2: Contar utilizadores com role 'paciente'
utilizadores_pacientes = Utilizador.objects.filter(role='paciente').count()
print(f"2. Total de utilizadores com role 'paciente': {utilizadores_pacientes}")

# Teste 3: Contar utilizadores pacientes ativos
utilizadores_pacientes_ativos = Utilizador.objects.filter(role='paciente', ativo=True).count()
print(f"3. Total de utilizadores pacientes ATIVOS: {utilizadores_pacientes_ativos}")

# Teste 4: Executar função PostgreSQL
print("\n4. Resultado da função PostgreSQL 'obter_pacientes_ativos()':")
with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM obter_pacientes_ativos()")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    print(f"   Colunas: {columns}")
    print(f"   Total de resultados: {len(rows)}")
    if rows:
        print(f"   Primeiros 3 resultados:")
        for row in rows[:3]:
            print(f"     {dict(zip(columns, row))}")

# Teste 5: Verificar pacientes com utilizadores
print("\n5. Detalhes dos pacientes com utilizadores:")
pacientes = Paciente.objects.select_related('id_utilizador').all()[:5]
for pac in pacientes:
    print(f"   - Paciente #{pac.id_paciente}: {pac.id_utilizador.nome} (Ativo: {pac.id_utilizador.ativo})")

# Teste 6: Query SQL direta
print("\n6. Query SQL direta para verificar dados:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT p.id_paciente, u.nome, u.email, u.ativo, p.data_nasc
        FROM "PACIENTES" p
        JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
        WHERE u.ativo = TRUE
        ORDER BY u.nome
        LIMIT 5
    """)
    rows = cursor.fetchall()
    print(f"   Total de pacientes ativos encontrados: {cursor.rowcount}")
    for row in rows:
        print(f"     {row}")

print("\n" + "=" * 60)
