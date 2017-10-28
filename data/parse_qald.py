import csv
import json
import logging
import sys
from subprocess import check_output
import os
from tqdm import tqdm
import argparse


QUERY_PREFIXES = """
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX wd: <http://www.wikidata.org/entity/>
    """

QPARSE = os.environ.get("QPARSE", "qparse")


def prettyify_query(query):
    return check_output([QPARSE, QUERY_PREFIXES + query]).decode('utf-8')


def pick_first(input, key, id):
    values = input[key]
    assert isinstance(values, list)
    assert values, ("No value for key {} in {}"
                    .format(repr(key), id))
    if len(values) > 1:
        logging.warning("Multiple values for key {} in {}"
                        .format(repr(key), id))
    return values[0]


def transform_question(input):
    id = str(input['id'])
    return {
        'id': id,
        'answer_type': input['answertype'],
        'question': pick_first(input, 'question', id)['string'],
        'query': prettyify_query(input['query']['sparql']),
        'answer': pick_first(input, 'answers', id),
    }


def transform_root(input):
    return [
        transform_question(question)
        for question in tqdm(input['questions'])
    ]


def parse(path, format, id_prefix):
    with open(path) as f:
        input = json.load(f)
        questions = transform_root(input)

        if id_prefix:
            for question in questions:
                question['id'] = id_prefix + question['id']

        if format == 'json':
            json.dump(questions, sys.stdout, indent=4)
        elif format == 'csv':
            fieldnames = ['id', 'answer_type', 'question', 'query', 'answer']
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            for question in questions:
                writer.writerow(question)
        else:
            raise ValueError('Unknown output format: {}'.format(format))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="path of the QALD JSON file")
    parser.add_argument("-f", "--format", type=str,
                        choices=['json', 'csv'],
                        default='csv',
                        help="output format")
    parser.add_argument("--id-prefix", type=str, help="prefix for IDs")
    args = parser.parse_args()

    dir = os.path.dirname(__file__)
    path = os.path.join(dir, args.path)

    parse(path, args.format, args.id_prefix)
