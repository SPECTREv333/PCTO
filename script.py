# coding: utf8
import csv
import argparse
import json
import re
from anytree import Node, RenderTree
# import pandas as pd



# regex per ripulire dati numerici
def data_cleaner(data):
    return re.sub("=*\"", '', data)

def organize(product_list):
    categorized_products = []
    current_product = {}
    for product in product_list[1:]:
        current_product = {}
        for data, column in zip(product, product_list[0]):
            if 'N.D.' not in data:
                current_product[column] = data_cleaner(data)
        categorized_products.append(current_product)
    return categorized_products


def extract(input_file, separator=';'):
    extracted = []
    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        csv_reader = csv.reader(f, delimiter=separator)
        for row in csv_reader:
            extracted.append(row)
    return extracted


def tree_builder(gerarchia_estratta):
    dictionary = {}
    for categoria in gerarchia_estratta:
        pass



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

    assert args.gerarchia.endswith(
        '.csv'), "Il file gerarchia deve essere di tipo csv"
    assert args.anagrafica.endswith(
        '.csv'), "Il file anagrafica deve essere di tipo csv"
    # df = pd.read_csv(args.anagrafica, sep=';', usecols = [i for i in range(len(extract(args.anagrafica)[0]))])

    # estrae e ripulisce i dati
    organized = organize(extract(args.gerarchia))

    # test unit
    with open(args.output, 'w') as f:
        json.dump(organized[30:], f)


# df = pd.DataFrame(organized[:-30])
# print(tabulate(df, headers='keys', tablefmt='psql'))


if __name__ == "__main__":
    main()
