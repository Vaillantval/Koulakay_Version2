# patch_thinkific.py

import json
import requests as _requests
import thinkific.client as _thinkific_client
from thinkific.client import Client
from thinkific.utils import mergeURL, BASE_URL, ADMIN_API_URL, WEBHOOKS_API_URL
from .instructor import Instructor
from .collection import Collection
from thinkific import Thinkific


class BearerClient(Client):
    """
    Thinkific's new JWT API tokens require 'Authorization: Bearer'
    instead of the legacy 'X-Auth-API-Key' header.
    """
    def __init__(self, api_key, subdomain, headers={}):
        super().__init__(api_key, subdomain, headers)
        # Override the private headers with Bearer auth
        self.__api_key = api_key
        self.__subdomain = subdomain

    def request(self, method=None, url=None, data=None, params=None, api='Admin'):
        headers = {
            'Authorization': f'Bearer {self.__api_key}',
            'X-Auth-Subdomain': self.__subdomain,
            'Content-Type': 'application/json',
        }
        if data:
            data = json.dumps(data)

        if api == 'Admin':
            full_url = mergeURL(BASE_URL + ADMIN_API_URL + url, params)
        elif api == 'Webhooks':
            full_url = mergeURL(BASE_URL + WEBHOOKS_API_URL + url, params)
        else:
            return 'API provided is not available'

        result = _requests.request(method=method, url=full_url, data=data, headers=headers)

        try:
            body = json.loads(result.text)
        except Exception:
            body = {}
        if result.status_code >= 400:
            raise Exception(result.status_code)
        return body


# Patch the library's Client globally so Thinkific.__init__ uses BearerClient
_thinkific_client.Client = BearerClient


class ThinkificExtend(Thinkific):
    def __init__(self, api_key, subdomain):
        super().__init__(api_key, subdomain)
        client = BearerClient(api_key, subdomain)
        self.__instructors = Instructor(client)
        self.__collections = Collection(client)

    @property
    def instructors(self):
        return self.__instructors

    @property
    def collections(self):
        return self.__collections
