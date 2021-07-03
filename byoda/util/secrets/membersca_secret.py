'''
Cert manipulation for service secrets: Service CA, Service Members CA and
Service secret

:maintainer : Steven Hessing <stevenhessing@live.com>
:copyright  : Copyright 2021
:license    : GPLv3
'''

import logging
from uuid import UUID
from typing import TypeVar

from cryptography.x509 import CertificateSigningRequest

from byoda.util import Paths

from byoda.datatypes import IdType, EntityId, CsrSource

from . import Secret

_LOGGER = logging.getLogger(__name__)

Network = TypeVar('Network', bound='Network')


class MembersCaSecret(Secret):
    def __init__(self, service: str, service_id: int,
                 network: Network):
        '''
        Class for the Service Members CA secret. Either paths or network
        parameters must be provided. If paths parameter is not provided,
        the cert_file and private_key_file attributes of the instance must
        be set before the save() or load() members are called

        The first two levels of a commmon name for a member should be:
            {member_id}.members-ca-{service_id}
        :param paths: instance of Paths class defining the directory structure
        and file names of a BYODA network
        :param service: label for the service
        :param paths: object containing all the file paths for the network. If
        this parameter has a value then the 'network' parameter must be None
        :param network: name of the network. If this parameter has a value then
        the 'paths' parameter must be None
        :returns: ValueError if both 'paths' and 'network' parameters are
        specified
        :raises: (none)
        '''

        paths = network.paths
        self.network = network
        self.service_id = service_id
        self.service = service

        super().__init__(
            cert_file=paths.get(
                Paths.SERVICE_MEMBERS_CA_CERT_FILE, service_id=service_id
            ),
            key_file=paths.get(
                Paths.SERVICE_MEMBERS_CA_KEY_FILE, service_id=service_id
            ),
            storage_driver=paths.storage_driver
        )
        self.ca = True
        self.id_type = IdType.MEMBERS_CA

        self.accepted_csrs = (IdType.MEMBER)

    def create_csr(self) -> CertificateSigningRequest:
        '''
        Creates an RSA private key and X.509 CSR

        :param service_id: identifier for the service
        :returns: csr
        :raises: ValueError if the Secret instance already has
                                a private key or cert
        '''

        name = self.id_type.value.rstrip('-')
        common_name = (
            f'{name}.{self.id_type.value}{self.service_id}.'
            f'{self.network.network}'
        )

        return super().create_csr(common_name, key_size=4096, ca=True)

    def review_commonname(self, commonname: str) -> EntityId:
        '''
        Checks if the structure of common name matches with a common name of
        an MemberSecret.

        :param commonname: the commonname to check
        :returns: entity parsed from the commonname
        :raises: ValueError if the commonname is not valid for this class
        '''

        # Checks on commonname type and the network postfix
        entity_id = super().review_commonname(commonname)

        return entity_id

    def review_csr(self, csr: CertificateSigningRequest,
                   source: CsrSource = None) -> EntityId:
        '''
        Review a CSR. CSRs for registering service member are permissable.

        :param csr: CSR to review
        :returns: entity, identifier
        :raises: ValueError if this object is not a CA (because it only has
        access to the cert and not the private_key) or if the CommonName
        in the CSR is not valid for signature by this CA
        '''

        if not self.private_key_file:
            _LOGGER.exception('CSR received while we are not a CA')
            raise ValueError('CSR received while we are not a CA')

        commonname = super().review_csr(csr)

        entity_id = self.review_commonname(commonname)

        return entity_id
