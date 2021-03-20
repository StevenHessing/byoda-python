'''
Cert manipulation for service secrets: Service CA, Service Members CA and
Service secret

:maintainer : Steven Hessing <stevenhessing@live.com>
:copyright  : Copyright 2021
:license    : GPLv3
'''

import logging

from cryptography.x509 import CertificateSigningRequest

from byoda.util import Paths

from byoda.datatypes import IdType, EntityId

from . import Secret, CsrSource

_LOGGER = logging.getLogger(__name__)


class ServiceSecret(Secret):
    def __init__(self, service: str, paths: Paths):
        '''
        Class for the service secret

        :param str service_alias: short name for the service
        :param Paths paths: instance of Paths class defining the directory,
        structure and file names of a BYODA network
        :returns: (none)
        :raises: (none)
        '''

        self.network = paths.network
        self.service = service
        self.service_id = None

        super().__init__(
            cert_file=paths.get(
                Paths.SERVICE_CERT_FILE, service_alias=service
            ),
            key_file=paths.get(
                Paths.SERVICE_KEY_FILE, service_alias=service
            )
        )
        self.ca = False
        self.id_type = IdType.SERVICE

    def create_csr(self, service_id: int) -> CertificateSigningRequest:
        '''
        Creates an RSA private key and X.509 CSR

        :param service_id: identifier for the service
        :returns: csr
        :raises: ValueError if the Secret instance already has a private key
        or cert
        '''

        common_name = f'{service_id}.{self.id_type.value}.{self.network}'

        return super().create_csr(common_name, ca=self.ca)

    def review_commonname(self, commonname: str) -> EntityId:
        '''
        Checks if the structure of common name matches with a common name of
        an AccountSecret and returns the entity identifier parsed from
        the commonname

        :param commonname: the commonname to check
        :returns: service entity
        :raises: ValueError if the commonname is not valid for this class
        '''

        # Checks on commonname type and the network postfix
        commonname_prefix = super().review_commonname(commonname)

        bits = commonname_prefix.split('.')
        if len(bits) != 2:
            raise ValueError(f'Invalid number of domain levels: {commonname}')

        service_id, subdomain = bits[0:1]
        id_type = IdType(subdomain)
        if id_type != IdType.SERVICE:
            raise ValueError(f'commonname {commonname} is not for a service')

        try:
            service_id = int(service_id)
        except ValueError:
            raise ValueError(f'{service_id} is not a valid service_id')

        self.service_id = service_id

        return EntityId(IdType.SERVICE, None, self.service_id)

    def review_csr(self, csr, source=CsrSource.WEBAPI):
        raise NotImplementedError