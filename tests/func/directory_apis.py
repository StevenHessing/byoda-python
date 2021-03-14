#!/usr/bin/env python3

'''
Test the Directory APIs

As these test cases are directly run against the web APIs, they mock
the headers that would normally be set by the reverse proxy

'''

import sys

from uuid import UUID, uuid4
import unittest
import requests

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from byoda.util.logger import Logger

from byoda.util.paths import Paths
from byoda.util.secrets import AccountSecret

NETWORK = 'byoda.net'
BASE_URL = 'http://localhost:5000/api'


class TestDirectoryApis(unittest.TestCase):
    def test_network_account_get(self):
        API = BASE_URL + '/v1/network/account/'
        uuid = uuid4()
        # GET, no auth
        response = requests.get(API)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(data)
        self.assertEqual(data['accounts'], 1)
        self.assertEqual(data['remote_addr'], '127.0.0.1')
        UUID(data['uuid'])

        # GET, with auth
        headers = {
            'X-Client-SSL-Verify': 'SUCCESS',
            'X-Client-SSL-Subject': f'CN={uuid}.accounts.{NETWORK}',
            'X-Client-SSL-Issuing-CA': f'CN=accounts-ca.{NETWORK}'
        }
        response = requests.get(API, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['accounts'], 1)
        self.assertEqual(data['remote_addr'], '127.0.0.1')
        UUID(data['uuid'])

        # GET, with auth
        headers = {
            'X-Client-SSL-Verify': 'SUCCESS',
            'X-Client-SSL-Subject': f'CN={uuid}.accounts.{NETWORK}',
            'X-Client-SSL-Issuing-CA': f'CN=accounts-ca.{NETWORK}'
        }
        response = requests.get(API, headers=headers)
        data = response.json()
        self.assertEqual(data['accounts'], 1)
        self.assertEqual(data['remote_addr'], '127.0.0.1')
        UUID(data['uuid'])

    def test_network_account_post(self):
        API = BASE_URL + '/v1/network/account/'

        paths = Paths(
            root_directory='/tmp/byoda_account_post',
            account_alias='account_post',
            network_name='byoda.net'
        )
        secret = AccountSecret(paths=paths)
        csr = secret.create_csr(uuid4())
        csr = csr.public_bytes(serialization.Encoding.PEM)
        response = requests.post(API, json={'csr': csr})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cert_splitter = '-----END CERTIFICATE-----\n'
        certs = data['certificate'].split(cert_splitter)
        certs = [cert + cert_splitter for cert in certs]
        issuing_ca_cert = x509.load_pem_x509_certificate(certs[0].encode())  # noqa
        account_cert = x509.load_pem_x509_certificate(certs[1].encode())     # noqa


if __name__ == '__main__':
    _LOGGER = Logger.getLogger(sys.argv[0], debug=True, json_out=False)

    unittest.main()
