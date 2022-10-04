#!/usr/bin/python
# -*- coding: utf-8 -*-
# Python 2.7.X

# Aide : python main.py --help

import argparse, os
from dotenv import load_dotenv
import geocoding
load_dotenv()

parser = argparse.ArgumentParser(description='A test program.')
parser.add_argument("-f", "--file", required=True, help="Chemin du fichier contenant les adresses à géocoder")
parser.add_argument("-id", "--id", required=True, help="Clé primaire du fichier")
parser.add_argument("-a", "--adresse", required=True, help="Colonne de l'adresse")
parser.add_argument("-cp", "--code_postal", required=True, help="Colonne du code postal")
parser.add_argument("-com", "--com", required=True, help="Colonne de la commune")
parser.add_argument("-p", "--pays", required=True, help="Colonne du pays")
parser.add_argument("-m", "--max_esri", required=False, default=100, help="Nombre de lignes max. à géocoder par le service payant World Esri (100 lignes par défaut)")
parser.add_argument("-g", "--geocodeur", required=True, nargs='+', help="Nom du service de géocodage (interne ou esri ou ban | les trois peuvent être appelés dans l'ordre de géocodage voulu, ex. : -g interne esri ban)")
parser.add_argument("-w", "--workspace", required=True, help="Dossier de travail où seront stocker les résultats")
parser.add_argument("-o", "--output_name", required=True, help="Nom du fichier de sortie des adresses géocodées")
args = parser.parse_args()

config = {
    "PGHOST": os.getenv('PGHOST'),
    "PGPORT": os.getenv('PGPORT'),
    "PGDBNAME": os.getenv('PGDBNAME'),
    "PGUSER": os.getenv('PGUSER'),
    "PGPWD": os.getenv('PGPWD'),
    "PGSCHEMA": os.getenv('PGSCHEMA'),
    "QGISBINPATH": os.getenv('QGISBINPATH'),
    "PGBINPATH": os.getenv('PGBINPATH'),
    "GEOCODINGSERVICES": args.geocodeur,
    "LOCATOR": os.getenv('INTERNELOCATOR'),
    "ESRI_MAX_ROWS": args.max_esri,
    "ESRIAPIKEY": os.getenv('ESRIAPIKEY'),
    "WORKSPACE": args.workspace,
    "INPUT_A_GEOCODER": args.file,
    "GEOCODAGE_OUTPUT": args.output_name,
    "GEOCODAGE_ERROR": 'adresses_err.csv',
    "ID": args.id,
    "ADRESSE": args.adresse,
    "CODE_POSTAL": args.code_postal,
    "COMMUNE": args.com,
    "PAYS": args.pays
}

ExecGeoc = geocoding.Geocoding(config)
ExecGeoc.chain_geocoding()

