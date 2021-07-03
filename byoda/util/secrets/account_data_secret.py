'''
Cert manipulation for data of an account

:maintainer : Steven Hessing <stevenhessing@live.com>
:copyright  : Copyright 2021
:license    : GPLv3
'''

import logging
from uuid import UUID

from cryptography.x509 import CertificateSigningRequest

from byoda.util import Paths

from byoda.datatypes import IdType
from . import Secret

_LOGGER = logging.getLogger(__name__)


class AccountDataSecret(Secret):
    def __init__(self, paths: Paths):
        '''
        Class for the account-data secret. This secret is used to encrypt
        account data.
        :param paths: instance of Paths class defining the directory structure
        and file names of a BYODA network
        :returns: ValueError if both 'paths' and 'network' parameters are
        specified
        :raises: (none)
        '''

        self.account_id = None
        super().__init__(
            cert_file=paths.get(Paths.ACCOUNT_DATA_CERT_FILE),
            key_file=paths.get(Paths.ACCOUNT_DATA_KEY_FILE),
            storage_driver=paths.storage_driver
        )
        self.account = paths.account
        self.network = paths.network
        self.ca = False
        self.issuing_ca = None
        self.id_type = IdType.ACCOUNT_DATA

        self.accepted_csrs = ()

    def create_csr(self, account_id: UUID = None) -> CertificateSigningRequest:
        '''
        Creates an RSA private key and X.509 CSR

        :param service_id: identifier for the service
        :returns: csr
        :raises: ValueError if the Secret instance already has
                                a private key or cert
        '''

        if not account_id:
            account_id = self.account_id

        common_name = (
            f'{account_id}.{self.id_type.value}.{self.network}'
        )

        return super().create_csr(common_name, key_size=4096, ca=self.ca)
