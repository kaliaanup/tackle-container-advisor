# *****************************************************************
# Copyright IBM Corporation 2021
# Licensed under the Eclipse Public License 2.0, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# *****************************************************************

import json
import re
import configparser
import logging
import sqlite3
import os
from sqlite3 import Error
from sqlite3.dbapi2 import Cursor, complete_statement
from pathlib import Path



config_obj = configparser.ConfigParser()
config_obj.read("./config.ini")

os.chdir('..')

def cleanStrValue(value):
    """
    Clean input strings   

    :param value: input string
    :returns: value
    
    """
    if value:
        value = str(value).strip()
        value = value.replace(u'\u00a0', ' ')
        value = re.sub(r'[^\x00-\x7F]+', ' ', ' ' + str(value) + ' ').strip()
    else:
        value = ''
    return value




def type_mapper(db_connection):

    """Maps each entity to the corresponding type

    :param conn:  A connection to mysql
    :type conn:  <class 'sqlite3.Connection'>

    :returns: {'1': 'Lang', '2': 'Lib', '3': 'App Server', '4': 'Runtime', '5': 'App', '6': 'OS'}
    :rtype: dict

    
    """

    type_cursor = db_connection.cursor()
    type_cursor.execute("SELECT * FROM entity_types")
    type_map = {}
    

    for type_tuple in type_cursor.fetchall():
        type_id , tech_type = type_tuple
        type_map[str(type_id)] = tech_type

    return type_map



def entity_mapper(db_connection):
    
    """
    Method to load entity names from "entities" table from mysql db 

    :param db_connection: A connection to mysql
    :type db_connection:  <class 'sqlite3.Connection'>

    :returns: A dictionary of entity_names
    :rtype: dict 

    """
    parent_class = {}

    parent_cursor = db_connection.cursor()
    parent_cursor.execute("SELECT * FROM entities")

    for entity_row in parent_cursor.fetchall():
        class_id , entity = entity_row[0] , entity_row[1]
        parent_class[str(class_id)] = entity 
    return parent_class


def save_json(json_file , file_name):
    """
    Save json file to the ontologies folder
    
    """

    path =  fr'aca_kg_utils/{config_obj["kg"]["ontologies"]}'  
    dst_pth = fr'aca_backend_api/{config_obj["kg"]["ontologies"]}'

    if not os.path.isdir(path):
        os.mkdir(path)
       
    if not os.path.isdir(dst_pth) :
        os.mkdir(dst_pth)  

    with open(path + config_obj["kg"][file_name] , encoding="utf-8", mode="w") as comp_file:
        comp_file.write(json.dumps(json_file, indent=2))





def create_class_type_mapper(db_connection):
    
    """
    Method to extract Entities from sql db and create  mapping each entity to the  corresponding type ("APP, APP SERVER , RUNTIME , LANG , LIB, OS)

    :param db_connection: A connection to mysql
    :type db_connection:  <class 'sqlite3.Connection'>


    :returns: Saves entity_mentions  in config_obj["kg"]["class_type_mapper_raw"]
    :retype: None
    """

    entity_mentions = {}
    entity_mentions["kg_version"] = config_obj["db"]["version"]
    entity_mentions["mappings"] = {}

    types_ = type_mapper(db_connection)
    entity_names = entity_mapper(db_connection) 
    
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM  entity_mentions")   
    mentions = cursor.fetchall()
    
    

    for mention in mentions:
        class_type = types_[str(mention[2])]
        index = str(mention[3])
        entity = entity_names[index]
        entity_mentions["mappings"][entity] = class_type
    
    save_json(entity_mentions, "class_type_mapper")
    

    



def create_inverted_compatibility_kg(db_connection):
    """
    Create inverted compatibility kwonledge graph
    
    """
    inverted_compatibilty_kg = {}
    inverted_cursor = db_connection.cursor()
    inverted_cursor.execute("SELECT * FROM entity_relations")


    entity_ids = entity_mapper(db_connection)
    type_ids = type_mapper(db_connection)

    inverted_compatibilty_kg["KG Version"] =  config_obj["db"]["version"]

    for inverted_ids in inverted_cursor.fetchall():
        
        inverted_lst = []
        parent_type_id , parent_id , child_type_id , child_id = inverted_ids[1:5]

        inverted_lst.append({"Parent Type":type_ids[str(parent_type_id)],"Parent Class":entity_ids[str(parent_id)],      
        "Child Type":type_ids[str(child_type_id)] })

        child_class = entity_ids[str(child_id)]

        inverted_compatibilty_kg[child_class] = inverted_lst
    

    save_json(inverted_compatibilty_kg,"inverted_compatibilityKG")






def create_compatibilty_kg(db_connection):
    """
    
    
    """

    CompatibilityKG= {}
    compatibility_list = []

    CompatibilityKG["KG Version"] =  config_obj["db"]["version"]

    
    type_ids = type_mapper(db_connection)
    entity_ids = entity_mapper(db_connection)
  

    relation_cursor = db_connection.cursor()
    relation_cursor.execute("SELECT * FROM entity_relations")


    
    for ids in relation_cursor.fetchall():
        parent_type_id , parent_id , child_type_id , child_id = ids[1:5]

        compatibility_list.append({"Parent Type":type_ids[str(parent_type_id)],"Parent Class":entity_ids[str(parent_id)],
        "Child Type":type_ids[str(child_type_id)] ,"Child Class":entity_ids[str(child_id)]})


    CompatibilityKG["Compatibility List"] =  compatibility_list

    save_json(CompatibilityKG,"compatibilityKG")



def create_base_os_kg(db_connection):
    """
    
    
    """

    base_cursor = db_connection.cursor()
    base_cursor.execute("SELECT * FROM  docker_baseos_images")

    mapped_os = entity_mapper(db_connection)

    base_os = {}
    base_os["KG Version"] =  config_obj["db"]["version"]
    base_os["Container Images"] = {}

    for  docker_baseos_image in base_cursor.fetchall():
        baseos_image, os_id , docker_url   = docker_baseos_image[1] , docker_baseos_image[2],  docker_baseos_image[3]
        Note , Status                      = docker_baseos_image[4] , docker_baseos_image[6]
        base_os["Container Images"][baseos_image] ={}
        base_os["Container Images"][baseos_image]["OS"] = [{"Class":mapped_os[str(os_id)] , "Variants":"", "Version":"","Type":"OS","Subtype":""}]

        base_os["Container Images"][baseos_image]["Lang"] , base_os["Container Images"][baseos_image]["Lib"] =[] , []
        base_os["Container Images"][baseos_image]["App"] ,  base_os["Container Images"][baseos_image]["App Server"] = [] ,[] 

        base_os["Container Images"][baseos_image]["Plugin"] , base_os["Container Images"][baseos_image]["Runlib"],  base_os["Container Images"][baseos_image]["Runtime"] =[] ,[] ,[]
        base_os["Container Images"][baseos_image]["Docker_URL"] = docker_url
        base_os["Container Images"][baseos_image]["Notes"] , base_os["Container Images"][baseos_image]["CertOfImageAndPublisher"]  = Note , Status 
        

    save_json(base_os, "baseOSKG")
       

def create_openshift_base_os_kg(db_connection):
    """
    
    
    """

    base_cursor = db_connection.cursor()
    base_cursor.execute("SELECT * FROM  openshift_baseos_images")

    mapped_os = entity_mapper(db_connection)

    base_os = {}
    base_os["KG Version"] =  config_obj["db"]["version"]
    base_os["Container Images"] = {}

    for  docker_baseos_image in base_cursor.fetchall():
        baseos_image, os_id , docker_url   = docker_baseos_image[1] , docker_baseos_image[2],  docker_baseos_image[3]
        Note , Status                      = docker_baseos_image[4] , docker_baseos_image[6]
        base_os["Container Images"][baseos_image] ={}
        base_os["Container Images"][baseos_image]["OS"] = [{"Class":mapped_os[str(os_id)] , "Variants":"", "Version":"","Type":"OS","Subtype":""}]

        base_os["Container Images"][baseos_image]["Lang"] , base_os["Container Images"][baseos_image]["Lib"] =[] , []
        base_os["Container Images"][baseos_image]["App"] ,  base_os["Container Images"][baseos_image]["App Server"] = [] ,[] 

        base_os["Container Images"][baseos_image]["Plugin"] , base_os["Container Images"][baseos_image]["Runlib"],  base_os["Container Images"][baseos_image]["Runtime"] =[] ,[] ,[]
        base_os["Container Images"][baseos_image]["Docker_URL"] = docker_url
        base_os["Container Images"][baseos_image]["Notes"] , base_os["Container Images"][baseos_image]["CertOfImageAndPublisher"]  = Note , Status 
        
      
        
    save_json(base_os, "openshiftbaseOSKG")

    

def create_inverted_openshift_base_os_kg(db_connection):
    """
    
    """

    base_cursor = db_connection.cursor()
    base_cursor.execute("SELECT * FROM  openshift_baseos_images")

    mapped_os = entity_mapper(db_connection)

    inverted_openshift_kg = {}
    inverted_openshift_kg["KG Version"] =  config_obj["db"]["version"]

    for base_image in base_cursor.fetchall():
        os , os_id = base_image[1],  base_image[2]
        inverted_openshift_kg[mapped_os[str(os_id)]] = [os]

    save_json(inverted_openshift_kg , "inverted_openshiftbaseOSKG")



def create_inverted_base_os_kg(db_connection):
    """
    
    """

    base_cursor = db_connection.cursor()
    base_cursor.execute("SELECT * FROM  docker_baseos_images")

    mapped_os = entity_mapper(db_connection)

    inverted_os_kg = {}
    inverted_os_kg["KG Version"] =  config_obj["db"]["version"]

    for base_image in base_cursor.fetchall():
        os , os_id = base_image[1],  base_image[2]
        inverted_os_kg[mapped_os[str(os_id)]] = [os]

    save_json(inverted_os_kg, "inverted_baseOSKG")

  
def get_os_variants(db_connection):
    """
    
    """

    cur = db_connection.cursor()
    cur.execute("SELECT * FROM  entities")
    all_os = []
    os_variants = {}
    types_map = type_mapper(db_connection)

    for entity in cur.fetchall():
        
        entity_name , entity_type_id = entity[1:3]
        type_ = types_map[str(entity_type_id)]
        if type_ == "OS" :
            all_os.append(entity_name)
        

        if entity_name.split("|")[-1] == "*" and type_ =="OS":
            os_variants[entity_name] = []
    
    OS = [os for os in all_os if os not in list(os_variants.keys())]

    os_variants["|*"] = OS

    for  os_variant in list(os_variants.keys())[1:]:

        var_lst = []     
        for variant in OS:
            if os_variant.split("|")[0] in variant :
                var_lst.append(variant)
        os_variants[os_variant] = var_lst

    return os_variants


def create_compatibility_os_kg(db_connection):
    """
    
    
    """

    cursor1 = db_connection.cursor()
    cursor2 = db_connection.cursor()
    entities = entity_mapper(db_connection)
    type_ids = type_mapper(db_connection)

    cursor1.execute("SELECT * FROM  entity_relations")
    cursor2.execute("SELECT * FROM  entity_relations")
    compatibilty_os_kg = {}
    compatibilty_os_kg["KG Version"] =  config_obj["db"]["version"]
    
    os_variant = get_os_variants(db_connection)

    for relation in cursor1.fetchall():
        parent_type_id , _, _, child_id = relation[1:5]

        parent_type = type_ids[str(parent_type_id)]

        if parent_type == "OS":

            child = entities[str(child_id)]
            compatibilty_os_kg[child] = []


    for entity_relation in cursor2.fetchall():
        
        
        type_id , parent_id , child_type_id , child_id =  entity_relation[1:5]

        type_ = type_ids[str(type_id)]

        parent_os = entities[str(parent_id)]
        child = entities[str(child_id)]

     
        if  type_ == "OS":
                
            if parent_os in list(os_variant.keys()):
                os_list = os_variant[parent_os]
                for os_ in os_list:
                    compatibilty_os_kg[child].append(os_)

            else:
                compatibilty_os_kg[child].append(parent_os)

    save_json(compatibilty_os_kg,"compatibilityOSKG")
    



def create_docker_image_kg(db_connect):
    """
    
    
    """
    docker_cursor = db_connect.cursor()
    docker_cursor.execute("SELECT *  FROM  docker_images")
    entities = entity_mapper(db_connect)

    docker_image_kg = {} 

    docker_image_kg["KG Version"] =  config_obj["db"]["version"]


    docker_image_kg["Container Images"]  = {}
    for image in docker_cursor.fetchall():
        container_name, os_entity_id, lang_id , lib_id, app_id, app_server_id, plugin_id , runlib_id , runtime_id, Docker_URL, Notes, CertOfImageAndPublisher = image[1:]

        docker_image_kg["Container Images"][container_name] = {}
        docker_image_kg["Container Images"][container_name]["OS"] =  [{"Class": entities[str(os_entity_id)], "Variants": "" ,"Versions": "" , "Type": "OS", "Subtype":""}]
        


        if lang_id == None: docker_image_kg["Container Images"][container_name]["Lang"] = []
        else: docker_image_kg["Container Images"][container_name]["Lang"] =  [{"Class": entities[str(lang_id)], "Variants": "" ,"Versions": "" , "Type": "Lang", "Subtype":""}]

        
        if lib_id == None:docker_image_kg["Container Images"][container_name]["Lib"] = []
        else: docker_image_kg["Container Images"][container_name]["Lib"] =  [{"Class": entities[str(lib_id)], "Variants": "" ,"Versions": "" , "Type": "Lib", "Subtype":""}]

        if app_id == None: docker_image_kg["Container Images"][container_name]["App"] = []
        else: docker_image_kg["Container Images"][container_name]["App"] =  [{"Class":entities[str(app_id)], "Variants": '' ,'Versions': '' , 'Type':"App",'Subtype':''}]


        if app_server_id == None: docker_image_kg["Container Images"][container_name]["App Server"] = []
        else: docker_image_kg["Container Images"][container_name]["App Server"] =  [{"Class":entities[str(app_server_id)], "Variants": '' ,'Versions': '' , 'Type':"App Server",'Subtype':''}]



        if plugin_id == None: docker_image_kg["Container Images"][container_name]["Plugin"] = []
        else: docker_image_kg["Container Images"][container_name]["Plugin"] =  [{"Class":entities[str(plugin_id)], "Variants": '' ,'Versions': '' , 'Type':"Plugin",'Subtype':''}]



               
        if runlib_id == None: docker_image_kg["Container Images"][container_name]["Runlib"] = []
        else: docker_image_kg["Container Images"][container_name]["Runlib"] =  [{"Class":entities[str(runlib_id)], "Variants": '' ,'Versions': '' , 'Type':"Runlib",'Subtype':''}]



        
        if runtime_id == None: docker_image_kg["Container Images"][container_name]["Runtime"] = []
        else: docker_image_kg["Container Images"][container_name]["Runtime"] =  [{"Class":entities[str(runtime_id)], "Variants": '' ,'Versions': '' , 'Type':"Runtime",'Subtype':''}]




        docker_image_kg["Container Images"][container_name]["Docker_URL"] = Docker_URL
        docker_image_kg["Container Images"][container_name]["Note"] = Notes
        docker_image_kg["Container Images"][container_name]["CertOfImageAndPublisher"] = CertOfImageAndPublisher
    
    save_json(docker_image_kg,"dockerimageKG")
    



def create_openshift_image_kg(db_connect):
    """
    
    """
    openshift_cursor = db_connect.cursor()
    openshift_cursor.execute("SELECT *  FROM  openshift_images")
    entities = entity_mapper(db_connect)

    openshift_image_kg = {} 

    openshift_image_kg["KG Version"] =    config_obj["db"]["version"]


    openshift_image_kg["Container Images"] = {}
    for image in openshift_cursor.fetchall():
        container_name, os_entity_id, lang_id , lib_id, app_id, app_server_id, plugin_id , runlib_id , runtime_id, Docker_URL,_= image[1:]

        openshift_image_kg["Container Images"][container_name] = {}
        openshift_image_kg["Container Images"][container_name]["OS"] =  [{"Class": entities[str(os_entity_id)], "Variants": "" ,"Versions": "" , "Type": "OS", "Subtype":""}]
        

        if lang_id == None: openshift_image_kg["Container Images"][container_name]["Lang"] = []
        else: openshift_image_kg["Container Images"][container_name]["Lang"] = [{"Class": entities[str(lang_id)], "Variants": "" ,"Versions": "" , "Type": "Lang", "Subtype":""}]
        
        
        
        if lib_id == None:openshift_image_kg["Container Images"][container_name]["Lib"] = []
        else: openshift_image_kg["Container Images"][container_name]["Lib"] = [{"Class": entities[str(lib_id)], "Variants": "" ,"Versions": "" , "Type": "Lib", "Subtype":""}]
        
        
        if app_id == None: openshift_image_kg["Container Images"][container_name]["App"] = []
        else: openshift_image_kg["Container Images"][container_name]["App"] =  [{"Class":entities[str(app_id)], "Variants": '' ,'Versions': '' , 'Type':"App",'Subtype':''}]
        
        if app_server_id == None: openshift_image_kg["Container Images"][container_name]["App Server"] = []
        else: openshift_image_kg["Container Images"][container_name]["App Server"] = [{"Class":entities[str(app_server_id)], "Variants": '' ,'Versions': '' , 'Type':"App Server",'Subtype':''}]
        

        if plugin_id == None: openshift_image_kg["Container Images"][container_name]["Plugin"] = []
        else: openshift_image_kg["Container Images"][container_name]["Plugin"] = [{"Class":entities[str(plugin_id)], "Variants": '' ,'Versions': '' , 'Type':"Plugin",'Subtype':''}]
        
        
        
        if runlib_id == None: openshift_image_kg["Container Images"][container_name]["Runlib"] = []
        else: openshift_image_kg["Container Images"][container_name]["Runlib"] = [{"Class":entities[str(runlib_id)], "Variants": '' ,'Versions': '' , 'Type':"Runlib",'Subtype':''}]
        
       
        
        if runtime_id == None: openshift_image_kg["Container Images"][container_name]["Runtime"] = []
        else: openshift_image_kg["Container Images"][container_name]["Runtime"] = [{"Class":entities[str(runtime_id)], "Variants": '' ,'Versions': '' , 'Type':"Runtime",'Subtype':''}]
        
        
        openshift_image_kg["Container Images"][container_name]["Docker_URL"] = Docker_URL
        
        openshift_image_kg["Container Images"][container_name]["CertOfImageAndPublisher"] = ''
    
    save_json(openshift_image_kg, "openshiftimageKG")


def create_inverted_docker_image_kg(database_connect):
    """
    
    
    """

    inverted_cur = database_connect.cursor()
    inverted_cur.execute("SELECT * FROM docker_images")
    entities = entity_mapper(database_connect)
    inverted_docker_images_kg = {}
    inverted_docker_images_kg['Version'] = config_obj["db"]["version"]
    cur = database_connect.cursor()
    cur.execute("SELECT * FROM docker_images")

    for img in cur.fetchall():
        _ , os_id, lan_id , libr_id, appl_id, appl_server_id, plug_id , runlibr_id , runtim_id,_, _,_ = img[1:]

        if os_id == None: pass
        else: inverted_docker_images_kg[entities[str(os_id)]] = []
        if lan_id == None: pass
        else:inverted_docker_images_kg[entities[str(lan_id)]] = []

        if libr_id == None: pass
        else: inverted_docker_images_kg[entities[str(libr_id)]] = []
        if appl_id == None: pass
        else:inverted_docker_images_kg[entities[str(appl_id)]] = []

        if appl_server_id == None: pass
        else:inverted_docker_images_kg[entities[str(appl_server_id)]] = []

        if plug_id == None: pass
        else: inverted_docker_images_kg[entities[str(plug_id)]] = []

        if runlibr_id == None: pass
        else: inverted_docker_images_kg[entities[str(runlibr_id)]] = []
        if runtim_id == None: pass
        else:inverted_docker_images_kg[entities[str(runtim_id)]] = []


    

    for image in inverted_cur.fetchall():
        _,container_name, os_entity_id, lang_id , lib_id, app_id, app_server_id, plugin_id , runlib_id , runtime_id,_, _,_ = image[:]

       
        if os_entity_id == None: pass
        else: inverted_docker_images_kg[entities[str(os_entity_id)]].append(container_name)

        if lang_id == None: pass
        else: inverted_docker_images_kg[entities[str(lang_id)]].append(container_name)
        
        if lib_id == None: pass
        else: inverted_docker_images_kg[entities[str(lib_id)]].append(container_name)

        if app_id == None: pass
        else: inverted_docker_images_kg[entities[str(app_id)]].append(container_name)


        if app_server_id == None: pass
        else: inverted_docker_images_kg[entities[str(app_server_id)]].append(container_name)


        
        if plugin_id == None: pass
        else: inverted_docker_images_kg[entities[str(plugin_id)]].append(container_name)

        
        if runlib_id == None: pass
        else: inverted_docker_images_kg[entities[str(runlib_id)]].append(container_name)

        
        if runtime_id == None: pass
        else: inverted_docker_images_kg[entities[str(runtime_id)]].append(container_name)

    save_json(inverted_docker_images_kg, "inverted_dockerimageKG")
    



def create_inverted_openshifht_image_kg(db_connection):
    """
    
    
    """

    inverted_cur = db_connection.cursor()
    inverted_cur.execute("SELECT * FROM openshift_images")  #
    entities = entity_mapper(db_connection)
    inverted_openshift_images_kg = {}
    inverted_openshift_images_kg['Version'] =  config_obj["db"]["version"]

    cur = db_connection.cursor()
    cur.execute("SELECT * FROM openshift_images")

    for img in cur.fetchall():
        _ , os_id, lan_id , libr_id, appl_id, appl_server_id, plug_id , runlibr_id , runtim_id,_, _ = img[1:]


        if os_id == None: pass
        else: inverted_openshift_images_kg[entities[str(os_id)]] = []
        if lan_id == None: pass
        else: inverted_openshift_images_kg[entities[str(lan_id)]] = []

        if libr_id == None: pass
        else: inverted_openshift_images_kg[entities[str(libr_id)]] = []
        if appl_id == None: pass
        else: inverted_openshift_images_kg[entities[str(appl_id)]] = []

        if appl_server_id == None: pass
        else: inverted_openshift_images_kg[entities[str(appl_server_id)]] = []

        if plug_id == None: pass
        else:  inverted_openshift_images_kg[entities[str(plug_id)]] = []

        if runlibr_id == None: pass
        else: inverted_openshift_images_kg[entities[str(runlibr_id)]] = []
        if runtim_id == None: pass
        else: inverted_openshift_images_kg[entities[str(runtim_id)]] = []
    
    for image in inverted_cur.fetchall():
        _,container_name, os_entity_id, lang_id , lib_id, app_id, app_server_id, plugin_id , runlib_id , runtime_id,_, _ = image[:]

       
        if os_entity_id == None: pass
        else: inverted_openshift_images_kg[entities[str(os_entity_id)]].append(container_name)

        if lang_id == None: pass
        else: inverted_openshift_images_kg[entities[str(lang_id)]].append(container_name)
        
        if lib_id == None: pass
        else: inverted_openshift_images_kg[entities[str(lib_id)]].append(container_name)

        if app_id == None: pass
        else: inverted_openshift_images_kg[entities[str(app_id)]].append(container_name)


        if app_server_id == None: pass
        else: inverted_openshift_images_kg[entities[str(app_server_id)]].append(container_name)


        
        if plugin_id == None: pass
        else: inverted_openshift_images_kg[entities[str(plugin_id)]].append(container_name)

        
        if runlib_id == None: pass
        else: inverted_openshift_images_kg[entities[str(runlib_id)]].append(container_name)
            
        if runtime_id == None: pass
        else: inverted_openshift_images_kg[entities[str(runtime_id)]].append(container_name)
    
    save_json(inverted_openshift_images_kg, "inverted_openshiftimageKG")
  

def create_cot_kg(db_connection):

    """
    
    
    """

    
    cur = db_connection.cursor()
    cur.execute("SELECT * FROM  entities")  
    entities = entity_mapper(db_connection)
    cot_kg = {}
    cot_kg['Version'] =  config_obj["db"]["version"]

    cots = []
    for entity in cur.fetchall():

        entity_name  = entity[1]

        cots.append(entity_name)
    
    cot_kg["COTS"] = cots

    save_json(cot_kg , "cot_kg")





    



def create_db_connection(db_file):
    """
    Create Mysql db connection

    :param db_file: path to mysql file
    :type db_file:  .db file

    :returns: Connection to mysql db

    :rtype:  <class 'sqlite3.Connection'>

    """

    connection = None

    try:
        connection = sqlite3.connect(db_file)
    except Error as e:
        logging.error(f'{e}: Issue connecting to db. Please check whether the .db file exists.')  
        print(e)
    return connection



if __name__== '__main__':


    logging.basicConfig(filename='logging.log',level=logging.ERROR, filemode='w')
    

    db_path = config_obj["db"]["db_path"]
    if not os.path.isfile(db_path):
        logging.error(f'{db_path} is not a file. Run "sh setup" from /tackle-advise-containerizeation folder to generate db files')
        print(f'{db_path} is not a file. Run "sh setup.sh" from /tackle-advise-containerizeation folder to generate db files')
        exit()

    try:
        db_path = config_obj["db"]["db_path"]


    except KeyError as k:
        logging.error(f'{k}  is not a key in your config.ini file.')
        print(f'{k} is not a key in your config.ini file.')
        exit()


    if not os.path.isfile(db_path):
        logging.error(f'{db_path} is not a valid file. Check your config.ini file for valid file under "db_path" key  ')
        print("{} is not a valid file. Check your config.ini file for valid file under 'db_path' key ".format(db_path))
        

    else:

        connection = create_db_connection(db_path)  
        create_inverted_compatibility_kg(connection)
        create_class_type_mapper(connection)
        create_openshift_image_kg(connection)
        create_docker_image_kg(connection)
        create_inverted_docker_image_kg(connection)
        create_compatibility_os_kg(connection)
        create_compatibilty_kg(connection)
        create_inverted_openshift_base_os_kg(connection)
        create_inverted_openshifht_image_kg(connection)
        create_base_os_kg(connection)
        create_inverted_base_os_kg(connection)
        create_openshift_base_os_kg(connection)
        create_cot_kg(connection)
    
    



    


    


