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

from byoda.datatypes import IdType, CsrSource
from . import Secret, CSR

_LOGGER = logging.getLogger(__name__)


class MemberDataSecret(Secret):
    def __init__(self, member_id: UUID, paths: Paths):
        '''
        Class for the member-data secret. This secret is used to encrypt
        data of an account for a service.
        :param paths: instance of Paths class defining the directory structure
        and file names of a BYODA network
        :returns: ValueError if both 'paths' and 'network' parameters are
        specified
        :raises: (none)
        '''

        self.member_id = member_id

        super().__init__(
            cert_file=paths.get(Paths.MEMBER_DATA_CERT_FILE),
            key_file=paths.get(Paths.MEMBER_DATA_KEY_FILE),
            storage_driver=paths.storage_driver, member_id=member_id
        )
        self.account_alias = paths.account
        self.network = paths.network
        self.ca = False
        self.issuing_ca = None
        self.id_type = IdType.MEMBER_DATA

        self.csrs_accepted_for = ()

    def create(self, expire: int = 109500):
        '''
        Creates an RSA private key and X.509 cert

        :param int expire: days after which the cert should expire
        :returns: (none)
        :raises: ValueError if the Secret instance already
                            has a private key or cert

        '''

        common_name = (
            f'{self.member_id}.{IdType.MEMBER_DATA.value}'
            f'.{self.network}'
        )
        super().create(common_name, expire=expire, key_size=4096, ca=self.ca)

    def create_csr(self, member_id: int = None) -> CertificateSigningRequest:
        '''
        Creates an RSA private key and X.509 CSR

        :param service_id: identifier for the service
        :returns: csr
        :raises: ValueError if the Secret instance already has
                                a private key or cert
        '''

        if not member_id:
            member_id = self.member_id

        common_name = (
            f'{self.member_id}.{IdType.MEMBER_DATA.value}'
            f'.{self.network}'
        )

        return super().create_csr(common_name, key_size=4096, ca=True)

    def review_commonname(self, commonname: str) -> str:
        '''
        Checks if the structure of common name matches with a common name an
        account_data

        :param commonname: the commonname to check
        :returns: the common name with the network domain stripped off
        :raises: ValueError if the commonname is not valid for this class
        '''

        # Checks on commonname type and the network postfix
        commonname_prefix = super().review_commonname(commonname)

        if commonname_prefix not in self.csrs_accepted_for:
            raise ValueError('An Account Data secret does not sign CSRs')

        return commonname_prefix

    def review_csr(self, csr: CSR, source: CsrSource = CsrSource.WEBAPI
                   ) -> str:
        raise NotImplementedError
