# export_sqlite.py
import sqlite3
import pyodbc
from datetime import datetime

print(" Connexion à SQLite...")

# 1. Connexion à SQLite (db.sqlite3)
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

print("Connexion SQLite réussie")

# 2. Connexion à SQL Server
server = r'LAPTOP-SS7MFL50\MSSQLSERVER01'
database = 'extraction'

drivers_to_try = [
    'ODBC Driver 17 for SQL Server',
    'ODBC Driver 13 for SQL Server',
    'SQL Server Native Client 11.0',
    'SQL Server'
]

sql_server_conn = None

for driver in drivers_to_try:
    try:
        print(f"🔌 Essai du driver: {driver}...")
        sql_server_conn = pyodbc.connect(
            f'DRIVER={{{driver}}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            'Trusted_Connection=yes;'
        )
        print(f"Connecté avec: {driver}")
        break
    except pyodbc.Error as e:
        print(f" {driver}: {e}")
        continue

if sql_server_conn is None:
    print("\n Aucun driver ODBC trouvé.")
    exit()

sql_cursor = sql_server_conn.cursor()

# ============================================================
# TABLE 1: extraction_catalogueupload
# ============================================================
print("\n" + "="*50)
print(" IMPORTATION DES CATALOGUES")
print("="*50)

# Supprimer l'ancienne table
try:
    sql_cursor.execute("DROP TABLE IF EXISTS extraction_catalogueupload")
    sql_server_conn.commit()
    print("Ancienne table catalogue supprimée")
except:
    pass

# Créer la table
print(" Création de la table extraction_catalogueupload...")
sql_cursor.execute("""
    CREATE TABLE extraction_catalogueupload (
        id INT PRIMARY KEY,
        enseigne NVARCHAR(100),
        enseigne_autre NVARCHAR(100),
        date_debut DATE,
        date_fin DATE,
        date_upload DATETIME2,
        image NVARCHAR(500)
    )
""")
sql_server_conn.commit()
print(" Table catalogue créée")

# Récupérer les données
print("\n Récupération des catalogues depuis SQLite...")
sqlite_cursor.execute("SELECT * FROM extraction_catalogueupload")
rows = sqlite_cursor.fetchall()
print(f"   {len(rows)} catalogues trouvés")

if len(rows) > 0:
    print(" Importation des catalogues...")
    count = 0
    for row in rows:
        try:
            # Convertir les dates
            date_debut = row['date_debut']
            date_fin = row['date_fin']
            date_upload = row['date_upload']
            
            if date_debut and isinstance(date_debut, str):
                date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            if date_fin and isinstance(date_fin, str):
                date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            if date_upload and isinstance(date_upload, str):
                date_upload = datetime.strptime(date_upload, '%Y-%m-%d %H:%M:%S.%f')
            elif date_upload and isinstance(date_upload, (int, float)):
                date_upload = datetime.fromtimestamp(date_upload)
            
            sql_cursor.execute("""
                INSERT INTO extraction_catalogueupload 
                (id, enseigne, enseigne_autre, date_debut, date_fin, date_upload, image)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['id'],
                row['enseigne'],
                row['enseigne_autre'],
                date_debut,
                date_fin,
                date_upload,
                row['image']
            ))
            count += 1
        except Exception as e:
            print(f" Erreur catalogue {row['id']}: {e}")
    
    sql_server_conn.commit()
    print(f" {count} catalogues importés avec succès")
else:
    print(" Aucun catalogue à importer")

# ============================================================
# TABLE 2: extraction_product
# ============================================================
print("\n" + "="*50)
print(" IMPORTATION DES PRODUITS")
print("="*50)

# Supprimer l'ancienne table
try:
    sql_cursor.execute("DROP TABLE IF EXISTS extraction_product")
    sql_server_conn.commit()
    print(" Ancienne table produit supprimée")
except:
    pass

# Créer la table
print(" Création de la table extraction_product...")
sql_cursor.execute("""
    CREATE TABLE extraction_product (
        id INT PRIMARY KEY,
        nom_fr NVARCHAR(500),
        nom_ar NVARCHAR(500),
        marque NVARCHAR(200),
        prix DECIMAL(10,3),
        prix_avant DECIMAL(10,3),
        remise NVARCHAR(50),
        description NVARCHAR(MAX),
        created_at DATETIME2,
        catalogue_id INT
    )
""")
sql_server_conn.commit()
print(" Table produit créée")

# Récupérer les données
print("\n Récupération des produits depuis SQLite...")
sqlite_cursor.execute("SELECT * FROM extraction_product")
rows = sqlite_cursor.fetchall()
print(f"   {len(rows)} produits trouvés")

if len(rows) == 0:
    print(" Aucun produit à importer")
else:
    print(" Importation des produits...")
    count_success = 0
    count_error = 0

    for row in rows:
        try:
            created_at = row['created_at']
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                    elif isinstance(created_at, (int, float)):
                        created_at = datetime.fromtimestamp(created_at)
                except:
                    try:
                        created_at = datetime.strptime(str(created_at), '%Y-%m-%d %H:%M:%S')
                    except:
                        created_at = None
            else:
                created_at = None
            
            sql_cursor.execute("""
                INSERT INTO extraction_product 
                (id, nom_fr, nom_ar, marque, prix, prix_avant, remise, description, created_at, catalogue_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['id'],
                row['nom_fr'],
                row['nom_ar'],
                row['marque'],
                row['prix'],
                row['prix_avant'],
                row['remise'],
                row['description'],
                created_at,
                row['catalogue_id']
            ))
            count_success += 1
            if count_success % 10 == 0:
                print(f"   {count_success} produits importés...")
        except Exception as e:
            count_error += 1
            print(f" Erreur produit {row['id']}: {e}")

    sql_server_conn.commit()
    print(f" {count_success} produits importés avec succès")
    if count_error > 0:
        print(f" {count_error} erreurs rencontrées")

# ============================================================
# RÉSUMÉ FINAL
# ============================================================
print("\n" + "="*50)
print(" RÉSUMÉ DES DONNÉES IMPORTÉES")
print("="*50)

sql_cursor.execute("SELECT COUNT(*) FROM extraction_catalogueupload")
total_catalogues = sql_cursor.fetchone()[0]
print(f"    Catalogues: {total_catalogues}")

sql_cursor.execute("SELECT COUNT(*) FROM extraction_product")
total_produits = sql_cursor.fetchone()[0]
print(f"    Produits: {total_produits}")

# 8. Fermer les connexions
sqlite_conn.close()
sql_server_conn.close()

print("\n Import terminé !")