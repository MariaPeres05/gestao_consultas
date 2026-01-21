# core/mongo_client.py
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    Singleton MongoDB client for managing notas clínicas and medical records.
    """
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            try:
                mongo_uri = getattr(settings, 'MONGO_DB_URI', 'mongodb://localhost:27017/')
                mongo_db_name = getattr(settings, 'MONGO_DB_NAME', 'gestao_consultas_notas_clinicas')
                
                self._client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
                # Test connection
                self._client.admin.command('ping')
                self._db = self._client[mongo_db_name]
                
                # Create indexes for better performance
                self._create_indexes()
                
                logger.info(f"MongoDB connected successfully to {mongo_db_name}")
            except ConnectionFailure as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                self._client = None
                self._db = None
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                self._client = None
                self._db = None
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'notas_clinicas')
            notas_clinicas = self._db[collection_name]
            notas_clinicas.create_index([('consulta_id', ASCENDING)], unique=False)
            notas_clinicas.create_index([('medico_id', ASCENDING)])
            notas_clinicas.create_index([('paciente_id', ASCENDING)])
            notas_clinicas.create_index([('created_at', DESCENDING)])
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @property
    def is_connected(self):
        """Check if MongoDB connection is active"""
        return self._client is not None and self._db is not None
    
    def get_collection(self, collection_name):
        """Get a MongoDB collection"""
        if not self.is_connected:
            raise ConnectionError("MongoDB is not connected")
        return self._db[collection_name]


class NotasClinicasService:
    """
    Service for managing notas clínicas in MongoDB
    """
    
    def __init__(self):
        self.mongo = MongoDBClient()
        if self.mongo.is_connected:
            collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'notas_clinicas')
            self.collection = self.mongo.get_collection(collection_name)
        else:
            self.collection = None
    
    def create_note(self, consulta_id, medico_id, paciente_id, notes_data):
        """
        Create a new nota clínica
        
        Args:
            consulta_id: ID of the consultation
            medico_id: ID of the doctor
            paciente_id: ID of the patient
            notes_data: Dictionary containing notas clínicas data
            
        Returns:
            The inserted document ID or None if failed
        """
        if self.collection is None:
            logger.error("Cannot create note: MongoDB not connected")
            return None
        
        document = {
            'consulta_id': consulta_id,
            'medico_id': medico_id,
            'paciente_id': paciente_id,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'notas_clinicas': notes_data.get('notas_clinicas', ''),
            'observacoes': notes_data.get('observacoes', ''),
            'diagnostico': notes_data.get('diagnostico', ''),
            'tratamento': notes_data.get('tratamento', ''),
            'exame_fisico': notes_data.get('exame_fisico', {}),
            'sintomas': notes_data.get('sintomas', []),
            'prescricoes': notes_data.get('prescricoes', []),
            'exames_solicitados': notes_data.get('exames_solicitados', []),
            'seguimento': notes_data.get('seguimento', ''),
        }
        
        try:
            result = self.collection.insert_one(document)
            logger.info(f"Nota clínica created for consulta {consulta_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create nota clínica: {e}")
            return None
    
    def get_note_by_consulta(self, consulta_id):
        """Get nota clínica for a specific consultation"""
        if self.collection is None:
            logger.warning("MongoDB collection not available")
            return None
        
        try:
            note = self.collection.find_one({'consulta_id': consulta_id})
            return note
        except Exception as e:
            logger.error(f"Failed to retrieve nota clínica: {e}")
            return None
    
    def get_notes_by_patient(self, paciente_id, limit=50):
        """Get all notas clínicas for a patient"""
        if self.collection is None:
            return []
        
        try:
            notes = self.collection.find(
                {'paciente_id': paciente_id}
            ).sort('created_at', DESCENDING).limit(limit)
            return list(notes)
        except Exception as e:
            logger.error(f"Failed to retrieve patient notes: {e}")
            return []
    
    def get_notes_by_medico(self, medico_id, limit=50):
        """Get all notas clínicas created by a doctor"""
        if self.collection is None:
            return []
        
        try:
            notes = self.collection.find(
                {'medico_id': medico_id}
            ).sort('created_at', DESCENDING).limit(limit)
            return list(notes)
        except Exception as e:
            logger.error(f"Failed to retrieve doctor notes: {e}")
            return []
    
    def update_note(self, consulta_id, notes_data):
        """Update an existing nota clínica"""
        if self.collection is None:
            return False
        
        update_data = {
            'updated_at': datetime.now(),
        }
        
        # Update only provided fields
        for key in ['notas_clinicas', 'observacoes', 'diagnostico', 'tratamento', 
                    'exame_fisico', 'sintomas', 'prescricoes', 'exames_solicitados', 'seguimento']:
            if key in notes_data:
                update_data[key] = notes_data[key]
        
        try:
            result = self.collection.update_one(
                {'consulta_id': consulta_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update nota clínica: {e}")
            return False
    
    def delete_note(self, consulta_id):
        """Delete a nota clínica"""
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_one({'consulta_id': consulta_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete nota clínica: {e}")
            return False
    
    def search_notes(self, query_text, limit=50):
        """Search notas clínicas by text"""
        if self.collection is None:
            return []
        
        try:
            # Simple text search in notas_clinicas and observacoes
            notes = self.collection.find({
                '$or': [
                    {'notas_clinicas': {'$regex': query_text, '$options': 'i'}},
                    {'observacoes': {'$regex': query_text, '$options': 'i'}},
                    {'diagnostico': {'$regex': query_text, '$options': 'i'}}
                ]
            }).sort('created_at', DESCENDING).limit(limit)
            return list(notes)
        except Exception as e:
            logger.error(f"Failed to search notes: {e}")
            return []
