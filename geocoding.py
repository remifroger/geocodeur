##!/usr/bin/python
## -*- coding: utf-8 -*-
## Python 2.7.X

"""
Fonctionnement
--------------
Le but est de géocoder des adresses en utilisant plusieurs services successifs en une seule fois, tout en gardant la possibilité de personnaliser l'approche si besoin.
On crée une classe de géocodage, prenant en paramètre un dictionnaire de configuration (config) et ayant des méthodes pour :
    - nettoyer l'espace de travail,
    - géocoder avec le service interne,
    - géocoder avec le service Esri,
    - géocoder avec la BAN,
    - transformer les coordonnées dans un le même système,
    - exporter les résultats,
    - chaîner l'ensemble des méthodes.
Cette dernière méthode est celle utilisée par défaut dans l'exécuteur (main.py).
"""

import os, sys, arcpy, subprocess, json, csv, requests, shutil, io
import pandas as pd
import re

def split_csv(filehandler, output_path, output_name, row_limit, delimiter=',', keep_headers=True):
    import csv
    output_name_template='{0}_%s.csv'.format(output_name)
    reader = csv.reader(filehandler, delimiter=delimiter)
    current_piece = 1
    current_out_path = os.path.join(
        output_path,
        output_name_template % current_piece
    )
    current_out_writer = csv.writer(open(current_out_path, 'wb'), delimiter=delimiter)
    current_limit = row_limit
    if keep_headers:
        headers = next(reader)
        current_out_writer.writerow(headers)
    for i, row in enumerate(reader):
        if i + 1 > current_limit:
            current_piece += 1
            current_limit = row_limit * current_piece
            current_out_path = os.path.join(
                output_path,
                output_name_template % current_piece
            )
            current_out_writer = csv.writer(open(current_out_path, 'wb'), delimiter=delimiter)
            if keep_headers:
                current_out_writer.writerow(headers)
        current_out_writer.writerow(row)

def csv_to_esri_json(csvFilePath, id_adr, address, cpostal, com, country):
    """
    Transforme un CSV en JSON adapté pour le service de géocodage World d'Esri

    Paramètres
    ----------
    csvFilePath: str
        Chemin du fichier CSV
    id_adr: str
        Colonne le l'identifiant unique de l'adresse
    address: str
        Colonne de l'adresse
    cpostal: str
        Colonne du code postal
    com: str
        Colonne du nom de commune
    country: str
        Colonne du pays
    """
    with open(csvFilePath) as file_obj:
        rows = csv.DictReader(file_obj, delimiter=',')
        array = []
        special_characters = ['!','#','$','%', '&','@','[',']',']','_', '?ï¿½', '/']
        for index, row in enumerate(rows):
            id_row = int(row[id_adr])
            address_format = row[address] + " " + row[cpostal] + " " + row[com] + ", " + row[country]
            cleanAddress = ''.join(i for i in address_format if not i in special_characters)
            json_dict = {
                'attributes': {
                    'objectid': id_row,
                    'address': cleanAddress
                }
            }
            array.append(json_dict)
        esriJsonFormat = { 'records': array }
        return json.dumps(esriJsonFormat)

class Geocoding:
    """
    Classe représentant une instance de géocodage d'un fichier

    Attributs
    ---------
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
    
    Méthodes
    --------
    clean_workspace()
        Nettoie l'espace de travail initial
    geocoding_interne(pathIn, pathOut)
        Géocodeur interne (basé sur config.LOCATOR)
    geocoding_esri(pathIn, pathOut)
        Géocodeur Esri (service payant World basé sur config.ESRIAPIKEY
    geocoding_ban(pathIn, pathOut)
        Géocodeur BAN
    geom_proj()
        Reprojette les points en Lambert-93
    export_results()
        Exporte les résultats des géocodeurs dans un dossier final
    chain_geocoding()
        Enchaîne l'ensemble des tâches
    """

    def __init__(self, config):
        """
        Paramètre
        ---------
        config: dict
            Objet de configuration
        """

        if len(config["ADRESSE"]) > 10 or len(config["CODE_POSTAL"]) > 10 or len(config["COMMUNE"]) > 10 or len(config["PAYS"]) > 10:
            sys.stdout.write("Le nom des colonnes adresse, code_postal, commune et pays ne doit pas dépasser 10 caractères.")
            sys.stdout.flush()
            exit()
        else:
            self.config = config

    def clean_workspace(self):
        sys.stdout.write('Suppression des fichiers d\'export s\'ils existent déjà')
        sys.stdout.flush()
        try:
            if os.path.exists(os.path.join(self.config["WORKSPACE"], 'geocodage')):
                shutil.rmtree(os.path.join(self.config["WORKSPACE"], 'geocodage'))
            workspaceFolder = os.path.join(self.config["WORKSPACE"], 'geocodage')
            os.mkdir(workspaceFolder)
            sys.stdout.write('Espace de travail prêt')
            sys.stdout.flush()
        except OSError as error:
            sys.stdout.write(str(error))
            sys.stdout.flush()
            pass

    def geocoding_interne(self, pathIn, pathOut):
        os.mkdir(pathOut)
        input_adresse_interne = pathIn
        LOCATOR_INTERNE = self.config["LOCATOR"]
        output_adresse_interne = "{0}/{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])

        try:
            sys.stdout.write('Lancement du géocodage interne')
            sys.stdout.flush()
            arcpy.GeocodeAddresses_geocoding(input_adresse_interne, LOCATOR_INTERNE, "adresse {0} VISIBLE NONE;cpostal {1} VISIBLE NONE".format(self.config["ADRESSE"], self.config["CODE_POSTAL"]), output_adresse_interne, "STATIC", "", "")
        except Exception:
            e = sys.exc_info()[1]
            sys.stdout.write(e.args[0])
            sys.stdout.flush()

        try:
            sys.stdout.write('Enregistrement des adresses géocodées par le locator interne dans une table PostgreSQL')
            sys.stdout.flush()
            os.chdir(self.config["QGISBINPATH"])
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', 'PG:host={0} port={1} dbname={2} user={3} password={4}'.format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split(".")[0]), '-overwrite', '-dialect', 'sqlite', '-sql', "SELECT {0}, 'Interne' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, ST_X(geometry) as x, ST_Y(geometry) as y FROM {5} where status <> 'U'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-lco', 'OVERWRITE=yes', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)
            sys.stdout.flush()

        try:
            sys.stdout.write('Sélection des adresses non géocodées précédemment et export en CSV pour poursuivre le géocodage des erreurs')
            sys.stdout.flush()
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}\{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-sql', "SELECT {0}, 'Interne' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, '' as x, '' as y FROM {5} where status = 'U'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)
            sys.stdout.flush()
    
    def geocoding_esri(self, pathIn, pathOut):
        os.mkdir(pathOut)
        input_adresse_esri = pathIn
        esri_batch_geocoding = 1800 # Le service Esri ne permet de géocoder que 2000 lignes d'un coup à chaque appel de l'API
        split_csv(open('{0}'.format(input_adresse_esri), 'r'), pathOut, "adresses_a_geoc_esri", esri_batch_geocoding)
        for index, csv in enumerate(os.listdir(pathOut)):
            if csv.startswith("adresses_a_geoc_esri") and csv.endswith(".csv"):
                try:
                    input_adresse_esri_to_json = csv_to_esri_json(os.path.join(pathOut, csv), self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"])
                    try:
                        sys.stdout.write('Lancement du géocodage Esri (World service) des adresses non géocodées précédemment')
                        sys.stdout.flush()
                        headers = { 'Content-Type': 'application/x-www-form-urlencoded','charset': 'utf-8' }
                        data = 'f=json&addresses={0}&token={1}&outSR=102110'.format(input_adresse_esri_to_json, self.config["ESRIAPIKEY"])
                        response = requests.post('https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/geocodeAddresses', headers=headers, data=data)
                        outEsriGeoc = response.json()
                        sys.stdout.write('Géocodage terminé')
                        sys.stdout.flush()
                        rows = []
                        for data in [outEsriGeoc]:
                            data_rows = data['locations']
                            for row in data_rows:
                                rows.append({self.config["ID"]: row['attributes']['ResultID'], 'loc_name': row['attributes']['Loc_name'], 'status': row['attributes']['Status'], 'score': row['attributes']['Score'], 'match_type': row['attributes']['Addr_type'], 'match_addr': row['attributes']['Match_addr'], self.config["ADRESSE"]: row['attributes']['Place_addr'], self.config["CODE_POSTAL"]: row['attributes']['Postal'], self.config["COMMUNE"]: row['attributes']['City'], self.config["PAYS"]: row['attributes']['CntryName'], 'x': row['attributes']['X'], 'y': row['attributes']['Y']})
                        data = pd.DataFrame(rows)
                        if index == 0:
                            data.to_csv("{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), sep=';', index=False, encoding='utf-8')
                        elif index > 0:
                            data.to_csv("{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), sep=';', mode='a', index=False, header=False, encoding='utf-8')
                    except requests.exceptions.HTTPError as e:
                        sys.stdout.write(str(e))
                        sys.stdout.flush()
                except subprocess.CalledProcessError as e:
                    sys.stdout.write(e.output)
                    sys.stdout.flush()
        try:
            sys.stdout.write('Enregistrement des adresses géocodées par Esri dans une table PostgreSQL (insertion dans la même table que précédemment)')
            sys.stdout.flush()
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT {0}, 'Esri' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, x, y FROM {5} where status <> 'U' or addr_type <> 'StreetName' or addr_type <> 'Postal'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-dialect', 'sqlite', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)
            sys.stdout.flush()

        try:
            sys.stdout.write('Sélection des adresses non géocodées par Esri précédemment et export en CSV')
            sys.stdout.flush()
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}/{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}/{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT {0}, 'Esri' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, x, y FROM {5} where status = 'U' or addr_type = 'StreetName' or addr_type = 'Postal'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)
            sys.stdout.flush()
    
    def geocoding_ban(self, pathIn, pathOut):
        os.mkdir(pathOut)
        try:
            sys.stdout.write('Lancement du géocodage BAN') # Documentation : https://adresse.data.gouv.fr/api-doc/adresse
            sys.stdout.flush()
            subprocess.check_output(['curl', '-X', 'POST', '-F', 'data=@{0}'.format(pathIn), 'https://api-adresse.data.gouv.fr/search/csv/', '-F', 'columns={0}'.format(self.config["ADRESSE"]), '-F', 'postcode={0}'.format(self.config["CODE_POSTAL"]), '-F', 'columns={0}'.format(self.config["COMMUNE"]), '-F', 'columns={0}'.format(self.config["PAYS"]), '-o', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"])])
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)

        try:
            sys.stdout.write('Enregistrement des adresses géocodées par la BAN dans une table PostgreSQL (insertion dans la même table que précédemment)')
            sys.stdout.flush()
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT {0}, 'BAN' as geoc_name, 'BAN' as loc_name, '' as status, result_score * 100 as score, result_type as match_type, result_label as match_addr, {1}, {2}, {3}, {4}, longitude as x, latitude as y FROM {5} where round(result_score, 1) >= 0.6".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-dialect', 'sqlite', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)

        try:
            sys.stdout.write('Sélection des adresses non géocodées par BAN précédemment et export en CSV')
            sys.stdout.flush()
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-dialect', 'sqlite', '-sql', "SELECT {0}, 'BAN' as geoc_name, 'BAN' as loc_name, '' as status, result_score * 100 as score, result_type as match_type, result_label as match_addr, {1}, {2}, {3}, {4}, longitude as x, latitude as y FROM {5} where round(result_score, 1) < 0.6".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            sys.stdout.write('Exporté')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output)
    
    def geom_proj(self):
        os.chdir(self.config["PGBINPATH"])
        try:
            sys.stdout.write('Transformation des coordonnées issues du géocodage Esri et BAN dans le format L93')
            sys.stdout.flush()
            SQLUPDATECOORD = "UPDATE " + str(self.config["PGSCHEMA"]) + "." + str(self.config["GEOCODAGE_OUTPUT"]).split(".")[0] + " SET x=st_x(st_transform(ST_setsrid(cast(st_makepoint(x::numeric, y::numeric) as geometry), 4326), 2154)), y=st_y(st_transform(ST_setsrid(cast(st_makepoint(x::numeric, y::numeric) as geometry), 4326), 2154)) WHERE geoc_name in('BAN', 'Esri')"
            subprocess.check_call(['psql', '-U', self.config["PGUSER"], '-h', self.config["PGHOST"], '-p', self.config["PGPORT"], '-d', self.config["PGDBNAME"], '-c', '{0}'.format(SQLUPDATECOORD)])
            sys.stdout.write('Transformation terminée')
            sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output) 

    def export_results(self):
        final_folder = os.path.join(self.config["WORKSPACE"], "geocodage", "geocodage_resultats")
        os.mkdir(final_folder)
        os.chdir(self.config["QGISBINPATH"])
        try:
            sys.stdout.write('Export des résultats dans le dossier final /geocodage_resultats')
            sys.stdout.flush()
            # Copie en CSV de la table PostgreSQL contenant les adresses géocodées insérées au fil de l'eau
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(final_folder, "adresses_geocodees.csv"), "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), '-sql', "SELECT * FROM {0}.{1}".format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            # Copie du CSV contenant les adresses non géocodées s'il en reste
            pathErrors = os.path.join(self.config["WORKSPACE"], "geocodage", self.config["GEOCODINGSERVICES"][-1], self.config["GEOCODAGE_ERROR"])
            pathResults = os.path.join(self.config["WORKSPACE"], "geocodage", "geocodage_resultats", "geocodage_erreurs_restantes.csv")
            if os.path.exists(pathErrors):
                shutil.copyfile(pathErrors, os.path.join(self.config["WORKSPACE"], "geocodage", "geocodage_resultats") + "/geocodage_erreurs_restantes.csv")
            sys.stdout.write('Copie terminée')
            sys.stdout.flush()
            # Calcul ratio du nombre de lignes géocodées
            nbRowsGeocoding = subprocess.check_output("csvstat {0}\{1} --count".format(final_folder, "adresses_geocodees.csv"), shell=True)
            nbRowsErrors = subprocess.check_output("csvstat {0}\{1} --count".format(final_folder, "geocodage_erreurs_restantes.csv"), shell=True)
            if nbRowsGeocoding > 0:
                ratioGeocoding = (float(nbRowsGeocoding) / (float(nbRowsGeocoding) + float(nbRowsErrors))) * 100
                sys.stdout.write("Performance du géocodage : {0} %".format(ratioGeocoding))
                sys.stdout.flush()
        except subprocess.CalledProcessError as e:
            sys.stdout.write(e.output) 

    def chain_geocoding(self):
        self.clean_workspace()
        GEOCODING_SERVICES = self.config["GEOCODINGSERVICES"]
        if len(GEOCODING_SERVICES) > 0:
            for index, service in enumerate(GEOCODING_SERVICES):
                if index == 0:
                    pathIn = self.config["INPUT_A_GEOCODER"]
                else:
                    pathIn = os.path.join(self.config["WORKSPACE"], "geocodage", GEOCODING_SERVICES[index - 1], self.config["GEOCODAGE_ERROR"])
                pathOut = os.path.join(self.config["WORKSPACE"], "geocodage", service)
                if service == 'interne':
                    self.geocoding_interne(pathIn, pathOut)
                elif service == 'esri':
                    if (os.path.exists(pathIn)):
                        count_rows_csv = subprocess.check_output("csvstat {0} --count".format(pathIn), shell=True)
                        if int(count_rows_csv) < int(self.config["ESRI_MAX_ROWS"]):
                            self.geocoding_esri(pathIn, pathOut)
                        elif int(count_rows_csv) == 0:
                            sys.stdout.write('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                            break
                        else:
                            sys.stdout.write('Seuil Esri dépassé')
                            break
                    else: 
                        sys.stdout.write('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                        break
                elif service == 'ban':
                    if (os.path.exists(pathIn)):
                        count_rows_csv = subprocess.check_output("csvstat {0} --count".format(pathIn), shell=True)
                        if int(count_rows_csv) == 0:
                            sys.stdout.write('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                            break
                        else:
                            # Si le géocodeur précédent est 'esri' et que le nombre de lignes a excédé le seuil esri, alors on prend l'entrée du géocodeur précédent esri s'il existe (si longueur de GEOCODING_SERVICES vaut 3)
                            if GEOCODING_SERVICES[index - 1] == 'esri' and int(count_rows_csv) > int(self.config["ESRI_MAX_ROWS"]) and len(GEOCODING_SERVICES) == 3:
                                sys.stdout.write('Seuil Esri dépassé, passage par la BAN')
                                pathIn = os.path.join(self.config["WORKSPACE"], "geocodage", GEOCODING_SERVICES[index - 2], self.config["GEOCODAGE_ERROR"])
                            self.geocoding_ban(pathIn, pathOut)
                    else: 
                        sys.stdout.write('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                        break
            self.geom_proj()
            self.export_results()
            sys.stdout.write("Géocodage terminé")
            sys.stdout.flush()
        else:
            sys.stdout.write("Aucun service de géocodage n'a été utilisé, GEOCODINGSERVICES est vide")
            exit()