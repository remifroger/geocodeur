# Géocodeur

## Version

Python 2.7.x

## Exécuter en ligne de commande

### Pré-requis

Assurez-vous de bien avoir QGIS, PostgreSQL, une clé API Esri et la librairie ArcPy. Une instance locale de PostgreSQL est nécessaire.

Puis remplissez les variables d'environnement du fichier `.env.sample` (en cas d'erreur, renommez-le en `.env`).

### Aide

```shell
python main.py --help
```

```
main.py [-h] -f FILE -id ID -w WORKSPACE -a ADRESSE -cp CODE_POSTAL
               -com COM -p PAYS [-m MAX_ESRI] -g GEOCODEUR [GEOCODEUR ...] -o
               OUTPUT_NAME
```

### Description

```
-f --file
Chemin du CSV à géocoder
Exemple : -f "C:\data\rpls\adresses_a_geocoder.csv"
```

```
-id --id
Clé primaire du fichier d'adresses à géocoder (longueur inférieure à 10 caractères)
Exemple : -id objectid
```

```
-a --adresse
Colonne de l'adresse à géocoder (longueur inférieure à 10 caractères)
Exemple : -a col_adr
```

```
-cp --code_postal
Colonne du code postal à géocoder (longueur inférieure à 10 caractères)
Exemple : -cp col_cp
```

```
-com --com
Colonne du libellé de la commune à géocoder (longueur inférieure à 10 caractères)
Exemple : -com col_com
```

```
-p --pays
Colonne du libellé du pays à géocoder (longueur inférieure à 10 caractères)
Exemple : -p col_pays
```

```
-m --max_esri
Nombre de lignes max. à géocoder par le service payant World Esri (100 lignes par défaut) - voir avec Alain Beauregard en cas de doute
Exemple : -m 2000
```

```
-g --geocodeur
Nom du service de géocodage (interne ou esri ou ban ; les trois peuvent être appelés dans l'ordre de géocodage voulu, ex. le plus courant : -g interne esri ban)
Exemple : -g interne esri ban
```

```
-w --workspace
Dossier de travail où seront stocker les résultats
Exemple : -w "C:\data\rpls"
```

```
-o --output_name
Nom du fichier de sortie des adresses géocodées (qui sera créé dans l'espace de travail défini (paramètre -w))
Exemple : -o proj_adr_geocodees.csv
```

### Exemple de commande

```shell
python "C:\path\main.py" -f "C:\data\rpls\adresses_a_geocoder.csv" -w "C:\data\rpls" -id n_sq_rplsa -a adresse -cp c_postal -com l_com -p pays -m 20 -g interne ban -o test3.csv
```

## Exécuter dans un script

Il est possible d'appeler la classe Geocoding() directement dans votre propre script Python.

### Exemple d'intégration

```python
import sys
sys.path.append('C:\\Users\\froger\\OneDrive - APUR\\python_apps\\geocoding')
import geocoding

config = {
    "PGHOST": "localhost",
    "PGPORT": "5436",
    "PGDBNAME": "work",
    "PGUSER": "postgres",
    "PGPWD": "postgres",
    "PGSCHEMA": "rpls_2021",
    "QGISBINPATH": "C:\\Program Files\\QGIS 3.10\\bin",
    "PGBINPATH": "C:\\Program Files\\PostgreSQL\\14\\bin",
    "GEOCODINGSERVICES": ["interne", "esri", "ban"],
    "LOCATOR": "P:\\SIG\\06_RESSOURCES\\Geocodage\\PERSONNALISATION_BDREF\\Adresses\\ADRESSE_COMPOSITE",
    "ESRI_MAX_ROWS": "3000",
    "ESRIAPIKEY": "secret",
    "WORKSPACE": "C:\\data\\rpls",
    "INPUT_A_GEOCODER": "C:\\data\\rpls\\adresses_a_geocoder.csv",
    "GEOCODAGE_OUTPUT": "test2.csv",
    "GEOCODAGE_ERROR": "adresses_err.csv"
    "ID": "n_sq_rplsa",
    "ADRESSE": "adresse",
    "CODE_POSTAL": "c_postal",
    "COMMUNE": "l_com",
    "PAYS": "pays",
}

ExecGeoc = geocoding.Geocoding(config)
ExecGeoc.clean_workspace()
ExecGeoc.chain_geocoding()
```
