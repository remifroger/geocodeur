##!/usr/bin/python
## -*- coding: utf-8 -*-
## Python 2.7.X

import os, sys, arcpy, subprocess, json, csv, requests, shutil
import pandas as pd

def csv_to_esri_json(csvFilePath, limit_rows, id_adr, address, cpostal, com, country):
    """
    Transforme un CSV en JSON adapté pour le service de géocodage World d'Esri

    Paramètres
    ----------
    csvFilePath: str
        Chemin du fichier CSV
    limit_rows: int
        Nombre de lignes max. à retourner
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
        limit = limit_rows
        for index, row in enumerate(rows):
            if index == limit:
                break
            else:
                id_row = row[id_adr]
                address_format = row[address] + "" + row[cpostal] + "" + row[com] + ", " + row[country]
                json_dict = {
                    'attributes': {
                        'objectid': int(id_row),
                        'address': address_format
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
            print("Le nom des colonnes adresse, code_postal, commune et pays ne doit pas dépasser 10 caractères.")
            exit()
        else:
            self.config = config

    def clean_workspace(self):
        print('Suppression des fichiers d\'export s\'ils existent déjà')
        try:
            # Pour les shp, on boucle sur l'ensemble du dossier pour détecter les fichiers commençant par le nom du shp sans l'extension, afin de bien supprimer l'ensemble des fichiers shp
            if os.path.exists(os.path.join(self.config["WORKSPACE"], 'interne')):
                shutil.rmtree(os.path.join(self.config["WORKSPACE"], 'interne'))
            if os.path.exists(os.path.join(self.config["WORKSPACE"], 'esri')):
                shutil.rmtree(os.path.join(self.config["WORKSPACE"], 'esri'))
            if os.path.exists(os.path.join(self.config["WORKSPACE"], 'ban')):
                shutil.rmtree(os.path.join(self.config["WORKSPACE"], 'ban'))
            if os.path.exists(os.path.join(self.config["WORKSPACE"], 'geocodage_resultats')):
                shutil.rmtree(os.path.join(self.config["WORKSPACE"], 'geocodage_resultats'))
            print('Espace de travail prêt')
        except OSError as error:
            print(error)
            pass

    def geocoding_interne(self, pathIn, pathOut):
        os.mkdir(pathOut)
        input_adresse_interne = pathIn
        LOCATOR_INTERNE = self.config["LOCATOR"]
        output_adresse_interne = "{0}/{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])

        try:
            print('Lancement du géocodage interne')
            arcpy.GeocodeAddresses_geocoding(input_adresse_interne, LOCATOR_INTERNE, "adresse {0} VISIBLE NONE;cpostal {1} VISIBLE NONE".format(self.config["ADRESSE"], self.config["CODE_POSTAL"]), output_adresse_interne, "STATIC", "", "")
        except Exception:
            e = sys.exc_info()[1]
            print(e.args[0])

        try:
            print('Enregistrement des adresses géocodées par le locator interne dans une table PostgreSQL')
            os.chdir(self.config["QGISBINPATH"])
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', 'PG:host={0} port={1} dbname={2} user={3} password={4}'.format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split(".")[0]), '-overwrite', '-dialect', 'sqlite', '-sql', "SELECT {0}, 'Interne' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, ST_X(geometry) as x, ST_Y(geometry) as y FROM {5} where status <> 'U'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-lco', 'OVERWRITE=yes', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)

        try:
            print('Sélection des adresses non géocodées précédemment et export en CSV pour poursuivre le géocodage des erreurs')
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}\{1}.shp".format(pathOut, str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-sql', "SELECT {0}, {1}, {2}, {3}, {4} FROM {5} WHERE status = 'U'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)
    
    def geocoding_esri(self, pathIn, pathOut):
        os.mkdir(pathOut)
        rows_limit = 10
        input_adresse_esri = pathIn
        input_adresse_esri_to_json = csv_to_esri_json(input_adresse_esri, rows_limit, self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"])
        # Usage du service ArcGIS World Geocoding Service seulement si le CSV en entrée contient moins que X lignes
        try:
            print('Lancement du géocodage Esri (World service) des adresses non géocodées précédemment')
            headers = { 'Content-Type': 'application/x-www-form-urlencoded','charset': 'utf-8' }
            data = 'f=json&addresses={0}&langCode=fr&token={1}&outSR=102110'.format(input_adresse_esri_to_json, self.config["ESRIAPIKEY"])
            response = requests.post('https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/geocodeAddresses', headers=headers, data=data)
            outEsriGeoc = response.json()
            print('Géocodage terminé')
            rows = []
            for data in [outEsriGeoc]:
                data_rows = data['locations']
                for row in data_rows:
                    rows.append({self.config["ID"]: row['attributes']['ResultID'], 'loc_name': row['attributes']['Loc_name'], 'status': row['attributes']['Status'], 'score': row['attributes']['Score'], 'match_type': row['attributes']['Addr_type'], 'match_addr': row['attributes']['Match_addr'], self.config["ADRESSE"]: row['attributes']['Place_addr'], self.config["CODE_POSTAL"]: row['attributes']['Postal'], self.config["COMMUNE"]: row['attributes']['City'], self.config["PAYS"]: row['attributes']['CntryName'], 'x': row['attributes']['X'], 'y': row['attributes']['Y']})
            data = pd.DataFrame(rows)
            data.to_csv("{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), sep=';', index=False, encoding='utf-8')
        except requests.exceptions.HTTPError as e:
            print(str(e))
        try:
            print('Enregistrement des adresses géocodées par Esri dans une table PostgreSQL (insertion dans la même table que précédemment)')
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT {0}, 'Esri' as geoc_name, loc_name, status, score, match_type, match_addr, {1}, {2}, {3}, {4}, x, y FROM {5} where status <> 'U'".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-dialect', 'sqlite', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)

        try:
            print('Sélection des adresses non géocodées par Esri précédemment et export en CSV')
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}/{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}/{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT * FROM {0} WHERE status = 'U'".format(str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)
    
    def geocoding_ban(self, pathIn, pathOut):
        os.mkdir(pathOut)
        try:
            print('Lancement du géocodage BAN') # Documentation : https://adresse.data.gouv.fr/api-doc/adresse
            subprocess.check_output(['curl', '-X', 'POST', '-F', 'data=@{0}'.format(pathIn), 'https://api-adresse.data.gouv.fr/search/csv/', '-F', 'columns={0}'.format(self.config["ADRESSE"]), '-F', 'postcode={0}'.format(self.config["CODE_POSTAL"]), '-F', 'columns={0}'.format(self.config["COMMUNE"]), '-F', 'columns={0}'.format(self.config["PAYS"]), '-o', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"])])
        except subprocess.CalledProcessError as e:
            print(e.output)

        try:
            print('Enregistrement des adresses géocodées par la BAN dans une table PostgreSQL (insertion dans la même table que précédemment)')
            subprocess.check_call(['ogr2ogr', '-f', 'PostgreSQL', "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-sql', "SELECT {0}, 'BAN' as geoc_name, 'BAN' as loc_name, '' as status, result_score as score, result_type as match_type, result_label as match_addr, {1}, {2}, {3}, {4}, longitude as x, latitude as y FROM {5} where round(result_score, 1) >= 0.6".format(self.config["ID"], self.config["ADRESSE"], self.config["CODE_POSTAL"], self.config["COMMUNE"], self.config["PAYS"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0]), '-dialect', 'sqlite', '-nln', '{0}.{1}'.format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)

        try:
            print('Sélection des adresses non géocodées par BAN précédemment et export en CSV')
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(pathOut, self.config["GEOCODAGE_ERROR"]), "{0}\{1}".format(pathOut, self.config["GEOCODAGE_OUTPUT"]), '-dialect', 'sqlite', '-sql', "SELECT * FROM {0} WHERE round(result_score, 1) < 0.6".format(str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            print('Exporté')
        except subprocess.CalledProcessError as e:
            print(e.output)
    
    def geom_proj(self):
        os.chdir(self.config["PGBINPATH"])
        try:
            print('Transformation des coordonnées issues du géocodage Esri et BAN dans le format L93')
            SQLUPDATECOORD = "UPDATE " + str(self.config["PGSCHEMA"]) + "." + str(self.config["GEOCODAGE_OUTPUT"]).split(".")[0] + " SET x=st_x(st_transform(ST_setsrid(cast(st_makepoint(x,y) as geometry), 4326), 2154)), y=st_y(st_transform(ST_setsrid(cast(st_makepoint(x,y) as geometry), 4326), 2154)) WHERE geoc_name in('BAN', 'Esri')"
            subprocess.check_call(['psql', '-U', self.config["PGUSER"], '-h', self.config["PGHOST"], '-p', self.config["PGPORT"], '-d', self.config["PGDBNAME"], '-c', '{0}'.format(SQLUPDATECOORD)])
            print('Transformation terminée')
        except subprocess.CalledProcessError as e:
            print(e.output) 

    def export_results(self):
        final_folder = os.path.join(self.config["WORKSPACE"], "geocodage_resultats")
        os.mkdir(final_folder)
        os.chdir(self.config["QGISBINPATH"])
        try:
            print('Export des résultats dans le dossier final /geocodage_resultats')
            # Copie en CSV de la table PostgreSQL contenant les adresses géocodées insérées au fil de l'eau
            subprocess.check_call(['ogr2ogr', '-f', 'CSV', "{0}\{1}".format(final_folder, "adresses_geocodees.csv"), "PG:host={0} port={1} dbname={2} user={3} password={4}".format(self.config["PGHOST"], self.config["PGPORT"], self.config["PGDBNAME"], self.config["PGUSER"], self.config["PGPWD"]), '-sql', "SELECT * FROM {0}.{1}".format(self.config["PGSCHEMA"], str(self.config["GEOCODAGE_OUTPUT"]).split('.')[0])])
            # Copie du CSV contenant les adresses non géocodées s'il en reste
            pathErrors = os.path.join(self.config["WORKSPACE"], self.config["GEOCODINGSERVICES"][-1], self.config["GEOCODAGE_ERROR"])
            pathResults = os.path.join(self.config["WORKSPACE"], "geocodage_resultats", "geocodage_erreurs_restantes.csv")
            if os.path.exists(pathErrors):
                shutil.copyfile(pathErrors, pathResults)
            print('Copie terminée')
        except subprocess.CalledProcessError as e:
            print(e.output) 

    def chain_geocoding(self):
        self.clean_workspace()
        GEOCODING_SERVICES = self.config["GEOCODINGSERVICES"]
        for index, service in enumerate(GEOCODING_SERVICES):
            if index == 0:
                pathIn = self.config["INPUT_A_GEOCODER"]
            else:
                pathIn = os.path.join(self.config["WORKSPACE"], GEOCODING_SERVICES[index - 1], self.config["GEOCODAGE_ERROR"])
            pathOut = os.path.join(self.config["WORKSPACE"], service)
            if service == 'interne':
                self.geocoding_interne(pathIn, pathOut)
            elif service == 'esri':
                count_rows_csv = subprocess.check_output("csvstat {0} --count".format(pathIn), shell=True)
                if int(count_rows_csv) < self.config["ESRI_MAX_ROWS"]:
                    self.geocoding_esri(pathIn, pathOut)
                elif int(count_rows_csv) == 0:
                    print('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                    break
                else:
                    print('Seuil Esri dépassé')
                    break
            elif service == 'ban':
                count_rows_csv = subprocess.check_output("csvstat {0} --count".format(pathIn), shell=True)
                if int(count_rows_csv) == 0:
                    print('Toutes les lignes ont été géocodées par le service précédent : {0}'.format(GEOCODING_SERVICES[index - 1]))
                    break
                else:
                    self.geocoding_ban(pathIn, pathOut)
        self.geom_proj()
        self.export_results()