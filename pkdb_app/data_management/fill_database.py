"""
Script to load data into database.

Needs location of directory with data.
Uses bonobo framework, a lightweight extract-transform-load (ETL) framework,
for data transformation and preparation.

The upload expects a certain folder structure:
- folder name is STUDYNAME, e.g., Albert1974
- folder contains pdf as STUDYNAME.pdf, e.g., Albert1974.pdf
- folder contains reference information as `reference.json`
- folder contains study information as `study.json`
- folder contains additional files associated with study, i.e.,
    - tables, named STUDYNAME_Tab[0-9]*.png, e.g., Albert1974_Tab1.png
    - figures, named STUDYNAME_Fig[0-9]*.png, e.g., Albert1974_Fig2.png
    - excel file, named STUDYNAME.xlsx, e.g., Albert1974.xlsx
    - data files, named STUDYNAME_Tab[0-9]*.csv or STUDYNAME_Fig[0-9]*.csv

Details about the JSON schema are given elsewhere (JSON schema and REST API).
"""
import os
import sys
import json
import requests
import bonobo
from jsonschema import validate
import logging

# FIXME: remove bonobo

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.schemas import reference_schema
from pkdb_app.data_management.create_reference import run as create_reference
from collections import namedtuple


# FIXME: implement proper logging

# -----------------------------
# master path
# -----------------------------
# DATA_PATH = os.path.join(BASEPATH, "data", "Master", "Studies")
DATA_PATH = os.path.abspath(os.path.join(BASEPATH, "..", "pkdb_data", "caffeine"))
print("-" * 80)
print("DATA_PATH:", DATA_PATH)
print("-" * 80)
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError

# -----------------------------
# setup database
# -----------------------------
API_URL = "http://0.0.0.0:8000/api/v1"
PASSWORD = "test"
USERS = [
    {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski", "email": "Janekg89@hotmail.de",
     "password": PASSWORD},
    {"username": "mkoenig", "first_name": "Matthias", "last_name": "König", "email": "konigmatt@googlemail.com",
     "password": PASSWORD}
]


def setup_database():
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    from pkdb_app.categoricals import SUBSTANCES_DATA
    for substance in SUBSTANCES_DATA:
        requests.post(f'{API_URL}/substances/', json={"name": substance})

    for user in USERS:
        requests.post(f'{API_URL}/users/', json=user)


# -------------------------------
# Paths of JSON files
# -------------------------------
def _get_paths(filename):
    """ Finds paths of filename recursively in MASTER_PATH. """
    for root, dirs, files in os.walk(DATA_PATH, topdown=False):
        if filename in files:
            yield os.path.join(root, filename)


def get_reference_paths():
    """ Finds paths of reference JSON files and corresponding PDFs.

    :return: dict
    """
    for path in _get_paths("reference.json"):
        study_name = os.path.basename(os.path.dirname(path))
        pdf_path = os.path.join(os.path.dirname(path), f"{study_name}.pdf")
        yield {"reference_path": path, "pdf": pdf_path}


def get_study_paths():
    """ Finds paths of study JSON files. """
    return _get_paths("study.json")


# -------------------------------
# Read JSON files
# -------------------------------
def _read_json(path):
    """ Reads json.

    :param path: returns json, or None if parsing failed.
    :return:
    """
    with open(path) as f:
        try:
            json_data = json.loads(f.read())
        except json.decoder.JSONDecodeError as err:
            print(err)
            return
    return json_data


def read_reference_json(d):
    """ Reads JSON for reference. """
    path = d["reference_path"]
    d2 = d.copy()
    d2["json"] = _read_json(path)
    return d2


def read_study_json(path):
    return {"json": _read_json(path),
            "study_path": path}


# -------------------------------
# Helpers
# -------------------------------

def recursive_iter(obj, keys=()):
    """ Creates dictionary with key:object from nested JSON data structure. """
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, keys + (k,))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, keys + (idx,))
    else:
        yield keys, obj


def set_keys(d, value, *keys):
    """ Changes keys in nested dictionary. """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def pop_comment(d, *keys):
    """ Pops comment in nested dictionary. """
    for key in keys[:-1]:

        if key == "comments":
            d.pop("comments")
            return

        d = d[key]


# -------------------------------
# Upload JSON in database
# -------------------------------
def upload_files(file_path):
    """ Uploads all files in directory of given file.

    :param file_path:
    :return: dict with all keys for files
    """
    data_dict = {}
    head, sid = os.path.split(file_path)
    study_dir = os.path.join(head, sid)
    for root, dirs, files in os.walk(study_dir, topdown=False):
        files = set(files) - set(['reference.json', 'study.json', f'{sid}.pdf'])
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                response = requests.post(f'{API_URL}/datafiles/', files={"file": f})
            data_dict[file] = response.json()["id"]
    return data_dict


def upload_reference_json(json_reference):
    """ Uploads reference JSON. """
    success = True
    validate(json_reference["json"], reference_schema)

    # post
    response = requests.post(f'{API_URL}/references/', json=json_reference["json"])
    if not response.status_code == 201:
        print(json_reference["json"]["name"], response.text)
        success = False

    # patch
    with open(json_reference["pdf"], 'rb') as f:
        response = requests.patch(f'{API_URL}/references/{json_reference["json"]["sid"]}/', files={"pdf": f})

    if not response.status_code == 200:
        print(json_reference["json"]["name"], response.text)
        success = False

    return success


def upload_study_json(json_study):
    """ Uploads study JSON. """
    success = True
    study_dir = os.path.dirname(json_study["study_path"])
    file_dict = upload_files(study_dir)
    comments = []
    for keys, item in recursive_iter(json_study):
        if item in file_dict.keys():
            set_keys(json_study, file_dict[item], *keys)
        if "comments" in keys:
            comments.append(keys)

    for comment in comments:
        pop_comment(json_study, *comment)

    study_partial = {}
    study_partial["sid"] = json_study["json"]["sid"]
    study_partial["name"] = json_study["json"]["name"]
    study_partial["pkdb_version"] = json_study["json"]["pkdb_version"]
    study_partial["design"] = json_study["json"]["design"]
    study_partial["substances"] = json_study["json"]["substances"]
    study_partial["reference"] = json_study["json"]["reference"]
    study_partial["curators"] = json_study["json"]["curators"]
    study_partial["creator"] = json_study["json"]["creator"]
    study_partial["files"] = list(file_dict.values())

    # post
    response = requests.post(f'{API_URL}/studies/', json=study_partial)
    if not response.status_code == 201:
        print(json_study["json"]["name"], response.text)
        success = False

    study_partial2 = {}
    study_partial2["groupset"] = json_study["json"]["groupset"]
    study_partial2["interventionset"] = json_study["json"]["interventionset"]
    study_partial2["individualset"] = json_study["json"].get("individualset", None)

    # patch
    response = requests.patch(f'{API_URL}/studies/{json_study["json"]["sid"]}/', json=study_partial2)
    if not response.status_code == 200:
        print(json_study["json"]["name"], response.text)
        success = False

    # patch
    if "outputset" in json_study["json"].keys():
        response = requests.patch(f'{API_URL}/studies/{json_study["json"]["sid"]}/',
                                  json={"outputset": json_study["json"].get("outputset")})
        if not response.status_code == 200:
            print(json_study["json"]["name"], response.text)
            success = False

    return success


def upload_study_from_dir(study_dir):
    """ Upload a complete study directory.

    Includes
    - study.json
    - reference.json
    - files

    :param study_dir:
    :return:
    """

    success = True
    study_path = os.path.join(study_dir, "study.json")
    _, study_name = os.path.split(study_dir)

    reference_path = os.path.join(study_dir, "reference.json")
    reference_pdf = os.path.join(study_dir, f"{study_name}.pdf")

    if not os.path.exists(reference_path):
        study = read_study_json(study_path)
        Reference = namedtuple("Reference", ["reference", "name", "pmid"])
        ref = Reference(reference=study_dir, name=study_name, pmid=study["json"]["reference"])
        create_reference(ref)

    if os.path.isfile(reference_path):
        reference_dict = {"json": reference_path, "pdf": reference_pdf}
        if read_reference_json(reference_dict):
            ok_ref = upload_reference_json(read_reference_json(reference_dict))
            if not ok_ref:
                success = ok_ref
        else:
            success = False

    if os.path.isfile(study_path):
        if read_study_json(study_path):
            ok_study = upload_study_json(read_study_json(study_path))
            if not ok_study:
                success = ok_study
        else:
            success = False

    if success:
        print("--- upload successful ---")


# -------------------------------
# Bonobo
# -------------------------------
def get_graph_references(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_reference_paths,
        read_reference_json,
        upload_reference_json,
    )
    return graph


def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_paths,
        read_study_json,
        upload_study_json,
    )
    return graph


def get_services(**options):
    return {}


# -------------------------------------------------------------------------------
if __name__ == '__main__':

    # core database setup
    setup_database()


    # run the bonobo chain
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_references(**options), services=get_services(**options))
        bonobo.run(get_graph_study(**options), services=get_services(**options))

    print("--- done ---")