import csv
import argparse
import json
import re
import treelib
from treelib import Tree, Node
import os
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
def extract(input_file, separator=';'):
    extracted = []
    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        csv_reader = csv.reader(f, delimiter=separator)
        for row in csv_reader:
            logger.debug("Read line: " + str(row))
            extracted.append(row)
    return extracted


def tree_builder(gerarchia_estratta):
    logger.debug("Started tree_builder()")
    tree = Tree()
    tree.create_node(identifier='root')
    logger.debug("Created root node")
    for categoria in gerarchia_estratta:
        try:
            # crea nodo
            tree.create_node(tag=categoria['Nome Categoria/Nodo Italiana'],
                             identifier=categoria['Codice Categoria/Nodo'],
                             parent=categoria['Codice Categoria/Nodo Padre'], data=categoria)
        except treelib.exceptions.NodeIDAbsentError:
            # se il nodo padre non esiste crea e appendi
            logger.debug("Father not found, creating one")
            tree.create_node(tag=categoria['Nome Categoria/Nodo Italiana'],
                             identifier=categoria['Codice Categoria/Nodo Padre'], parent='root')
            tree.create_node(tag=categoria['Nome Categoria/Nodo Italiana'],
                             identifier=categoria['Codice Categoria/Nodo'],
                             parent=categoria['Codice Categoria/Nodo Padre'], data=categoria)
        except treelib.exceptions.DuplicatedNodeIdError:
            # sposta nodi padre già crati
            logger.debug("Merging duplicated node")
            tree.move_node(categoria['Codice Categoria/Nodo'], categoria['Codice Categoria/Nodo Padre'])
        except:
            logger.error("File has unexpected format, check column names")
            exit(0)

    # rimuove le foglie e le inserisce in una lista
    leaves_data = []
    for leaf in tree.leaves():
        leaves_data.append(leaf.data)
        tree.remove_node(leaf.identifier)
    return tree, leaves_data


def dictionary_slicer(dictionary, start, end):
    sliced_dictionary={}
    for key, i in zip(dictionary, range(start, end)):
        sliced_dictionary[key] = dictionary[key]
    return sliced_dictionary


def dictionary_cleaner(dictionary, discriminator=""):
    cleaned_dictionary = {}
    for key in dictionary:
        if dictionary[key] != discriminator:
            cleaned_dictionary[key] = dictionary[key]
    return cleaned_dictionary


def main():
    parser = argparse.ArgumentParser(description='Genera importazione')
    parser.add_argument('-g', '--gerarchia', required=True,
                        help='file gerarchia')
    parser.add_argument('-a', '--anagrafica',
                        required=True, help='file anagrafica')
    parser.add_argument('-s', '--separator', required=False,
                        help='simbolo di separazione file csv (default: \';\')')
    parser.add_argument('-o', '--output', required=True,
                        help='directory di output')
    args = parser.parse_args()

    assert not os.path.isdir(args.output), "Esiste già la directory di output"
    assert args.gerarchia.endswith(
        '.csv'), "Il file gerarchia deve essere di tipo csv"
    assert args.anagrafica.endswith(
        '.csv'), "Il file anagrafica deve essere di tipo csv"

    # estrae e ripulisce i dati
    gerarchia_estratta = organize(extract(args.gerarchia))
    anagrafica_estratta = organize(extract(args.anagrafica))

    # crea directory di output
    os.mkdir(args.output)
    os.chdir(args.output)

    # costruisce albero e foglie da geraarchia
    tree, leaves = tree_builder(gerarchia_estratta)
    # salva la rappresentazione grafica dell'albero delle categorie
    tree.save2file("albero_categorie.txt", idhidden=False)
    logger.info("tree size: " + str(tree.size()))

    # separa le varianti di prodotti tra obsolete e non
    varianti = []
    varianti_obsolete = []
    for variante in anagrafica_estratta:
        if variante['Codice Categoria'] == '':
            varianti_obsolete.append(dictionary_slicer(variante, 0, 2))
        else:
            varianti.append(variante)

    # salvataggio dati estratti in formato json
    with open("categorie.json", 'w') as f:
        categorie = []
        for node in tree.all_nodes()[1:]:
            if node.data is not None:
                categorie.append(dictionary_cleaner(node.data))
        json.dump(categorie, f)

    with open("varianti con caratteristiche.json", 'w', encoding='utf-8-sig') as f:
        json.dump(varianti[10:], f)

    with open("varianti obsolete.json", 'w', encoding='utf-8-sig') as f:
        json.dump(varianti_obsolete[10:], f)

    with open("prodotti.json", 'w', encoding='utf-8-sig') as f:
        json.dump(leaves[10:], f)


if __name__ == "__main__":
    main()
