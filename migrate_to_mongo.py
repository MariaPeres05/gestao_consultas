#!/usr/bin/env python
"""
Script to migrate existing consultation notes from PostgreSQL to MongoDB
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_consultas.settings')
django.setup()

from core.models import Consulta
from core.mongo_client import NotasClinicasService

def migrate_consultas_to_mongo():
    """Migrate all consultas with notes from PostgreSQL to MongoDB"""
    notas_service = NotasClinicasService()
    
    # Get all consultas that have notes
    consultas = Consulta.objects.filter(
        notas_clinicas__isnull=False
    ).exclude(notas_clinicas='').select_related('id_medico', 'id_paciente')
    
    print(f"Found {consultas.count()} consultas with notes to migrate")
    
    migrated = 0
    skipped = 0
    
    for consulta in consultas:
        # Check if already exists in MongoDB
        existing = notas_service.get_note_by_consulta(consulta.id_consulta)
        
        if existing:
            print(f"  Skipping consulta {consulta.id_consulta} - already in MongoDB")
            skipped += 1
            continue
        
        # Prepare notes data
        notes_data = {
            'notas_clinicas': consulta.notas_clinicas or '',
            'observacoes': consulta.observacoes or '',
            'diagnostico': '',
            'tratamento': '',
            'sintomas': [],
            'prescricoes': [],
            'exames_solicitados': [],
            'seguimento': '',
            'exame_fisico': {
                'pressao_arterial': '',
                'temperatura': '',
                'frequencia_cardiaca': '',
                'peso': '',
                'altura': '',
            }
        }
        
        # Create in MongoDB
        try:
            note_id = notas_service.create_note(
                consulta_id=consulta.id_consulta,
                medico_id=consulta.id_medico.id_medico,
                paciente_id=consulta.id_paciente.id_paciente,
                notes_data=notes_data
            )
            
            if note_id:
                print(f"  ✓ Migrated consulta {consulta.id_consulta}")
                migrated += 1
            else:
                print(f"  ✗ Failed to migrate consulta {consulta.id_consulta}")
        except Exception as e:
            print(f"  ✗ Error migrating consulta {consulta.id_consulta}: {e}")
    
    print(f"\n✓ Migration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {consultas.count()}")

if __name__ == '__main__':
    migrate_consultas_to_mongo()
