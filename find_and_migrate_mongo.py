#!/usr/bin/env python
"""
Find MongoDB collection with data and migrate to the correct collection name
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_consultas.settings')
django.setup()

from pymongo import MongoClient
from django.conf import settings

def find_and_migrate():
    # Connect to MongoDB
    mongo_uri = getattr(settings, 'MONGO_DB_URI', 'mongodb://localhost:27017/')
    target_db_name = getattr(settings, 'MONGO_DB_NAME', 'gestao_consultas_notas_clinicas')
    target_collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'notas_clinicas')
    
    client = MongoClient(mongo_uri)
    
    print(f"Target database: {target_db_name}")
    print(f"Target collection: {target_collection_name}")
    print("\nSearching for collection with data...")
    
    # Check all databases
    for db_name in client.list_database_names():
        if db_name in ['admin', 'config', 'local']:
            continue
            
        db = client[db_name]
        print(f"\n📂 Database: {db_name}")
        
        for coll_name in db.list_collection_names():
            collection = db[coll_name]
            count = collection.count_documents({})
            
            if count > 0:
                print(f"  ✓ Collection '{coll_name}' has {count} documents")
                
                # Show a sample document
                sample = collection.find_one({'consulta_id': 6})
                if sample:
                    print(f"    Found consulta_id=6 in this collection!")
                    print(f"    Sample: notas_clinicas={sample.get('notas_clinicas', 'N/A')}")
                    
                    # Ask to migrate
                    if db_name != target_db_name or coll_name != target_collection_name:
                        print(f"\n  🔄 This data needs to be migrated!")
                        print(f"     From: {db_name}.{coll_name}")
                        print(f"     To: {target_db_name}.{target_collection_name}")
                        
                        response = input("\n  Migrate data? (yes/no): ").strip().lower()
                        if response == 'yes':
                            # Migrate
                            target_db = client[target_db_name]
                            target_coll = target_db[target_collection_name]
                            
                            # Copy all documents
                            docs = list(collection.find())
                            if docs:
                                # Clear target collection first
                                target_coll.delete_many({})
                                print(f"  Cleared target collection")
                                
                                # Insert documents
                                target_coll.insert_many(docs)
                                print(f"  ✓ Migrated {len(docs)} documents")
                                
                                # Verify
                                verify = target_coll.find_one({'consulta_id': 6})
                                if verify:
                                    print(f"  ✓ Verified: consulta_id=6 found in target collection")
                                else:
                                    print(f"  ✗ Warning: Could not verify migration")
                            else:
                                print(f"  No documents to migrate")
            else:
                print(f"  Empty: {coll_name}")
    
    client.close()
    print("\n✓ Done!")

if __name__ == '__main__':
    find_and_migrate()
