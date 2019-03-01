"""
Initial setup of database.

Creates basic users and information like substances and keywords.
"""
import requests
import logging
import os
from urllib.parse import quote_plus

from pkdb_app.settings import DEFAULT_PASSWORD, API_BASE
from pkdb_app.categoricals import  KEYWORDS_DATA
from pkdb_app.data_management.utils import _read_json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logging.getLogger().setLevel(logging.INFO)

USERS = [
    {
        "username": "janekg",
        "first_name": "Jan",
        "last_name": "Grzegorzewski",
        "email": "Janekg89@hotmail.de",
        "password": DEFAULT_PASSWORD,
    },
    {
        "username": "mkoenig",
        "first_name": "Matthias",
        "last_name": "König",
        "email": "konigmatt@googlemail.com",
        "password": DEFAULT_PASSWORD,
    },
    {
        "username": "kgreen",
        "first_name": "Kathleen",
        "last_name": "Green",
        "email": "test@test.com",
        "password": DEFAULT_PASSWORD,
    },

]


def get_authentication_headers(api_base=API_BASE, username="admin", password=DEFAULT_PASSWORD):
    """ Get authentication header with token for given user.

    Returns admin authentification as default.
    """
    response = requests.post(f"{api_base}/api-token-auth/", json={"username": username, "password": password})
    print(response.content)
    response.raise_for_status()
    token = response.json().get("token")
    return {'Authorization': f'token {token}'}


def requests_with_client(client, requests, *args, **kwargs):
    method = kwargs.pop("method", None)

    if client:
        if kwargs.get("files"):
            kwargs["data"] = kwargs.pop("files",None)
            response = getattr(client, method)(*args, **kwargs)

        else:
            response = getattr(client, method)(*args, **kwargs, format='json')
    else:
        kwargs["json"] = kwargs.pop("data", None)
        response = getattr(requests, method)(*args, **kwargs)

    return response


def setup_database(api_url, auth_headers, client=None):
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    for user in USERS:
        response = requests_with_client(client, requests, f"{api_url}/users/", method="post",
                                        data=user, headers=auth_headers)

        if not response.status_code == 201:
            logging.warning(f"user upload failed: {user} ")
            logging.warning(response.content)

    #substances_json = [{"name":substance.name} for substance in SUBSTANCES_DATA]
    substance_json_dir = os.path.join(BASE_DIR,"substances/substances.json")
    substances_json = _read_json(substance_json_dir)
    for substance in substances_json:

        response = requests_with_client(client, requests, f"{api_url}/substances/", method="post",
                                        data=substance, headers=auth_headers)
        if not response.status_code == 201:
            if response.content == b'{"sid":["substance with this sid already exists."],"url_slug":["substance with this url slug already exists."]}':

                response = requests_with_client(client, requests, f"{api_url}/substances/{substance['url_slug']}/", method="patch",
                                                data=substance, headers=auth_headers)
                if not response.status_code == 200:
                    logging.warning(f"substance: {substance} upload failed")
                    logging.warning(response.content)

            else:
                logging.warning(f"substance: {substance} upload failed")
                logging.warning(response.content)




    #for substance in SUBSTANCES_DATA:
    #
    #    response = requests_with_client(client, requests, f"{api_url}/substances/", method="post",
    #                                    data={"name": substance}, headers=auth_headers)
    #    if not response.status_code == 201:
    #        logging.warning(f"substance upload failed: {substance}")
    #        logging.warning(response.content)

    for keyword in KEYWORDS_DATA:
        response = requests_with_client(client, requests, f"{api_url}/keywords/", method="post",
                                        data={"name": keyword}, headers=auth_headers)
        if not response.status_code == 201:
            logging.warning(f"keyword upload failed: {keyword} ")
            logging.warning(response.content)


if __name__ == "__main__":
    from pkdb_app.settings import API_URL

    authentication_headers = get_authentication_headers(api_base=API_BASE, username="admin", password=DEFAULT_PASSWORD)
    setup_database(api_url=API_URL, auth_headers=authentication_headers)
