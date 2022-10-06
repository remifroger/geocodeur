# Géocodeur

Géocodeur prenant en entrée un CSV et utilisant trois services successifs au choix : un "locator" Esri, le ArcGIS World Geocoding et la BAN, pour aboutir à un CSV comprenant les X, Y ainsi qu'un fichier contenant les erreurs. Le géocodage est exécutable en ligne de commande ou dans un script Python.

[Exécuter en ligne de commande](#exécuter-en-ligne-de-commande)

[Exécuter dans un script Python](#exécuter-dans-un-script)

## Version

Python 2.7.x

Conseil : étant donné la dépendance à la librairie ArcPy, il est conseillé d'utiliser la version Python 2.7 associée à ArcGIS, en général à ce chemin : C:\Python27\ArcGISX.X

## Exécuter en ligne de commande

### Pré-requis et dépendances

Assurez-vous de bien avoir QGIS, PostgreSQL, une clé API Esri et la librairie ArcPy. Une instance locale de PostgreSQL est nécessaire.

* ogr2ogr (QGIS),
* psql (PostgreSQL),
* API Esri,
* Python (ArcPy, Pandas, Subprocess, CSV, Requests, Shutil, Dotenv)

Puis remplissez les variables d'environnement du fichier `.env.sample` (en cas d'erreur, renommez-le en `.env`).

### Usage

```shell
python main.py -f "C:\path\to\adresses_a_geocoder.csv" -w "C:\path\to\workspace" -id col_id -a col_adresse -cp col_code_postal -com col_commune -p col_pays -m max_rows_esri -g interne esri ban -o output_file.csv
```

**Les paramètres -id (colonne identifiant adresse), -a (colonne adresse), -cp (colonne code postal), -com (colonne commune), -p (colonne pays) n'acceptent que des noms de colonne sans caractères spéciaux (ni espace, ni majuscule), et dont la longueur est inférieure à 10, pour des contraintes liées au format de sortie SHP.**

Retourne dans l'espace de travail défini (paramètre -w) un dossier `geocodage/geocodage_resultats` contenant le fichier de sortie CSV (paramètre -o) et un fichier contenant les erreurs, s'il y en a (adresses_err.csv).

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

### Exemple d'usage

```shell
python "C:\path\main.py" -f "C:\data\rpls\adresses_a_geocoder.csv" -w "C:\data\rpls" -id n_sq_rplsa -a adresse -cp c_postal -com l_com -p pays -m 20 -g interne ban -o test3.csv
```

## Exécuter dans un script

Il est possible d'appeler la classe Geocoding() directement dans votre propre script Python.

### La class Geocoding(*config*)

```
Geocoding(*config*)

Classe représentant une instance de géocodage d'un fichier

Attributs

config: dict
    Object de configuration
config.PGHOST: str
    Hôte PostgreSQL
config.PGPORT: str
    Port PostgreSQL
config.PGDBNAME: str
    BDD PostgreSQL
config.PGUSER: str
    Nom d'utilisateur PostgreSQL
config.PGPWD: str
    Mot de passe PostgreSQL
config.QGISBINPATH: str
    Chemin vers le dossier des binaires QGIS (/bin)
config.PGBINPATH: str
    Chemin vers le dossier des binaires PostgreSQL (/bin)
config.GEOCODINGSERVICES: array
    Liste des services de géocodage à utiliser, dans l'ordre
config.LOCATOR: str
    Chemin vers le locator associé au géocodage interne (P:/SIG/06_RESSOURCES/Geocodage/PERSONNALISATION_BDREF/Adresses/ADRESSE_COMPOSITE)
config.ESRI_MAX_ROWS: str
    Nombre de lignes max. à consommer par le service payant World Esri
config.ESRIAPIKEY: str
    Clé API Esri
config.WORKSPACE: str
    Chemin vers l'espace de travail où les fichiers seront créés
config.INPUT_A_GEOCODER: str
    Chemin du CSV à géocoder
config.GEOCODAGE_OUTPUT: str
    Nom du fichier CSV de sortie
config.GEOCODAGE_ERROR: str
    Nom du fichier CSV des erreurs de géocodage
config.ID: str
    Colonne de l'identifiant unique des adresses à géocoder
config.ADRESSE: str
    Colonne de l'adresse
config.CODE_POSTAL: str
    Colonne du code postal
config.COMMUNE: str
    Colonne de la commune
config.PAYS: str
    Colonne du pays
pathIn: str
    Chemin d'entrée du géocodage
pathOut: str
    Chemin de sortie du géocodage
```

### Méthodes accessibles

```
Geocoding.clean_workspace()

Nettoyage de l'espace de travail
```

```
Geocoding.geocoding_interne(*pathIn*, *pathOut*)

Géocodage avec le service interne

Attributs

pathIn: str
    Fichier d'entrée
pathOut: str
    Dossier de sortie
```

```
Geocoding.geocoding_esri(*pathIn*, *pathOut*)

Géocodage avec le service Esri

Attributs

pathIn: str
    Fichier d'entrée
pathOut: str
    Dossier de sortie
```

```
Geocoding.geocoding_ban(*pathIn*, *pathOut*)

Géocodage avec le service BAN

Attributs

pathIn: str
    Fichier d'entrée
pathOut: str
    Dossier de sortie
```

```
Geocoding.geom_proj()

Reprojection des adresses en Lambert-93
```

```
Geocoding.export_results()

Exporte les résultats des géocodeurs dans un dossier final
```

```
Geocoding.chain_geocoding()

Enchaîne l'ensemble des tâches
```

### Exemple d'usage

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
ExecGeoc.chain_geocoding()
## Cela retourne un dossier au niveau du "WORKSPACE" (dans l'exemple : C:\\data\\rpls) comprenant les résultats CSV du géocodage
```
