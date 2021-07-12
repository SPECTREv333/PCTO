import csv
import argparse
import json
import os
import re
import sys
import treelib
from treelib import Tree
import logging

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


# regex di pulizia dati------------------v
def organize(product_list, clean_regex="=*\"|=", stop_at='N.D.'):
    categorized_products = []
    current_product = {}
    for product in product_list[1:]:
        current_product = {}
        for data, column in zip(product, product_list[0]):
            if stop_at in data:
                logger.debug("Found " + stop_at + " string, skipping " + column + " column")
                continue
            current_product[column] = re.sub(clean_regex, '', data)
            logger.debug("Adding " + str(current_product))
        categorized_products.append(current_product)
    return categorized_products


# lettura file csv
def read_file(input_file_path):
    extracted = []
    with open(input_file_path, mode='r', encoding='utf-8-sig') as f:
        csv_reader = csv.reader(f, dialect=dialect_sniffer(input_file_path))
        try:
            for row in csv_reader:
                logger.debug("Read line: " + str(row))
                extracted.append(row)
        except csv.Error as e:
            sys.exit('file {}, line {}: {}'.format(input_file_path, csv_reader.line_num, e))
    return extracted


def dialect_sniffer(file_path):
    with open(file_path) as file:
        dialect = csv.Sniffer().sniff(file.read(1024))
    return dialect


def tree_builder(gerarchia_estratta, nome_colonna_categoria='Nome Categoria/Nodo Italiana',
                 nome_colonna_codice_categoria='Codice Categoria/Nodo',
                 nome_colonna_codice_categoria_padre='Codice Categoria/Nodo Padre'):
    logger.debug("Started tree_builder()")
    tree = Tree()
    tree.create_node(identifier='root')
    logger.debug("Created root node")
    for categoria in gerarchia_estratta:
        try:
            # crea nodo
            tree.create_node(tag=categoria[nome_colonna_categoria],
                             identifier=categoria[nome_colonna_codice_categoria],
                             parent=categoria[nome_colonna_codice_categoria_padre], data=categoria)
        except treelib.exceptions.NodeIDAbsentError:
            # se il nodo padre non esiste crea e appendi
            logger.debug("Father not found, creating one")
            tree.create_node(tag=categoria[nome_colonna_categoria],
                             identifier=categoria[nome_colonna_codice_categoria_padre], parent='root')
            tree.create_node(tag=categoria[nome_colonna_categoria],
                             identifier=categoria[nome_colonna_codice_categoria],
                             parent=categoria[nome_colonna_codice_categoria_padre], data=categoria)
        except treelib.exceptions.DuplicatedNodeIdError:
            # sposta nodi padre già crati
            logger.debug("Merging duplicated node")
            tree.move_node(categoria[nome_colonna_codice_categoria], categoria[nome_colonna_codice_categoria_padre])
        except:
            sys.exit("File has unexpected format, check column names")

    # rimuove le foglie e le inserisce in una lista
    leaves_data = []
    for leaf in tree.leaves():
        leaves_data.append(leaf.data)
        tree.remove_node(leaf.identifier)
    return tree, leaves_data


def dictionary_slicer(dictionary, start, end):
    sliced_dictionary = {}
    for key in list(dictionary.keys())[start:end]:
        sliced_dictionary[key] = dictionary[key]
    return sliced_dictionary


def dictionary_cleaner(dictionary, discriminator=""):
    cleaned_dictionary = {}
    for key in dictionary:
        if dictionary[key] != discriminator:
            cleaned_dictionary[key] = dictionary[key]
    return cleaned_dictionary


def separa_varianti(anagrafica, colonna_obsoleto='Obsoleto', stringa_descrizione='Descrizione caratteristica', stringa_codice = 'Codice Prodotto', stringa_valore = 'Valore caratteristica'):
    varianti = []
    varianti_obsolete = []
    caratteristiche_varianti = []
    index_caratteristiche = 0
    for item in list(anagrafica[0].keys()):
        if stringa_descrizione in item:
            index_caratteristiche = list(anagrafica[0].keys()).index(item)
            break

    for variante in anagrafica:
        if 'Si' in variante[colonna_obsoleto]:
            varianti_obsolete.append(dictionary_slicer(variante, 0, 2))
        else:
            varianti.append(dictionary_slicer(variante, 0, index_caratteristiche))
            caratteristiche = dictionary_slicer(variante, index_caratteristiche, len(variante))
            caratteristiche_correnti = {}
            for key in caratteristiche:
                if stringa_descrizione in key:
                    caratteristiche_correnti[stringa_codice] = variante[stringa_codice]
                    caratteristiche_correnti['Posizione'] = key.replace(stringa_descrizione, '').strip()
                    caratteristiche_correnti['Descrizione'] = caratteristiche[key]
                elif stringa_valore in key:
                    caratteristiche_correnti['Valore'] = caratteristiche[key]
                    caratteristiche_varianti.append(caratteristiche_correnti)
                    caratteristiche_correnti = {}
    return varianti, varianti_obsolete, caratteristiche_varianti


def csv_write(list_of_elements, filename, dialect):
    csv_file = open(filename, 'w')
    try:
        keys = list(sorted(list_of_elements, key=len, reverse=True)[0].keys())
    except:
        return
    csv_writer = csv.DictWriter(csv_file, keys, dialect=dialect)
    csv_writer.writeheader()
    csv_writer.writerows(list_of_elements)
    csv_file.close()


def main():
    parser = argparse.ArgumentParser(description='Genera importazione')
    parser.add_argument('-g', '--gerarchia', required=True,
                        help='file gerarchia')
    parser.add_argument('-a', '--anagrafica',
                        required=True, help='file anagrafica')
    parser.add_argument('-o', '--output', required=True,
                        help='-o directory_di_output')
    args = parser.parse_args()

    #assert not os.path.isdir(args.output[0]), "Esiste già la directory di output"
    assert args.gerarchia.endswith(
        '.csv'), "Il file gerarchia deve essere di tipo csv"
    assert args.anagrafica.endswith(
        '.csv'), "Il file anagrafica deve essere di tipo csv"

    # estrae e ripulisce i dati
    gerarchia_estratta = organize(read_file(args.gerarchia))
    anagrafica_estratta = organize(read_file(args.anagrafica))
    # separa le varianti di prodotti tra obsolete e non
    varianti, obsolete, caratteristiche = separa_varianti(anagrafica_estratta)

    # crea directory di output
    os.mkdir(args.output)
    os.chdir(args.output)

    # costruisce albero e foglie da geraarchia
    tree, leaves = tree_builder(gerarchia_estratta)
    # salva la rappresentazione grafica dell'albero delle categorie
    tree.save2file("albero_categorie.txt", idhidden=False)
    logger.info("tree size: " + str(tree.size()))

    # salvataggio dati estratti in formato json
    categorie = []
    for node in tree.all_nodes()[1:]:
        if node.data is not None:
            categorie.append(dictionary_cleaner(node.data))

    csv_write(categorie, "categorie.csv", dialect_sniffer(args.anagrafica))
    csv_write(varianti, "varianti.csv", dialect_sniffer(args.anagrafica))
    csv_write(obsolete, "varianti obsolete.csv", dialect_sniffer(args.anagrafica))
    csv_write(caratteristiche, "caratteristiche.csv", dialect_sniffer(args.anagrafica))
    csv_write(leaves, "prodotti.csv", dialect_sniffer(args.anagrafica))

    with open("categorie.json", 'w', encoding='utf-8-sig') as f:
        json.dump(categorie, f)

    with open("varianti.json", 'w', encoding='utf-8-sig') as f:
        json.dump(varianti, f)

    with open("varianti obsolete.json", 'w', encoding='utf-8-sig') as f:
        json.dump(obsolete, f)

    with open("prodotti.json", 'w', encoding='utf-8-sig') as f:
        json.dump(leaves, f)

    with open("caratteristiche.json", 'w', encoding='utf-8-sig') as f:
        json.dump(caratteristiche, f)


if __name__ == "__main__":
    main()
