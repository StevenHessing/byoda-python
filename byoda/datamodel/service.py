'''
Class for modeling a service on a social network

:maintainer : Steven Hessing <stevenhessing@live.com>
:copyright  : Copyright 2021
:license    : GPLv3
'''

from __future__ import annotations

import json
import logging
from typing import TypeVar, Callable
from copy import copy

from byoda.datatypes import CsrSource

from byoda.util.secrets import Secret
from byoda.util.secrets import NetworkServicesCaSecret
from byoda.util.secrets import ServiceCaSecret
from byoda.util.secrets import MembersCaSecret
from byoda.util.secrets import AppsCaSecret
from byoda.util.secrets import ServiceSecret
from byoda.util.secrets import ServiceDataSecret

_LOGGER = logging.getLogger(__name__)

Account = TypeVar('Account', bound='Account')
Network = TypeVar('Network', bound='Network')


class Service:
    '''
    Models a service on a BYODA network.
    This class is used both by the SDK for hosting a service
    and by pods
    '''

    def __init__(self, service: str = None, service_id: int = None,
                 network: Network = None):
        '''
        Constructor, can be used by the service but also by the
        network, an app or an account or member to model the service.
        Because of this, only minimal initiation of the instance is
        done and depending on the user case, additional methods must
        be called to load all the needed info for the service.
        '''

        self.service = str(service)
        self.service_id = int(service_id)

        # The data contract for the service. TODO: versioned schemas
        self.schema = None

        self.private_key_password = network.private_key_password

        # The CA signed by the Services CA of the network
        self.service_ca = None

        # CA signs secrets of new members of the service
        self.members_ca = None

        # CA signs secrets of apps that run with a delegation of
        # the data contract of the service
        self.apps_ca = None

        # The secret used as server cert for incoming TLS connections
        # and as client cert in outbound TLS connections
        self.tls_secret = None

        # The secret used to sign documents, ie. the data contract for
        # the service
        self.data_secret = None

        # The network that the service is a part of. As storage is already
        # set up for the Network object, we can copy it here for the Service
        self.network = network
        self.paths = copy(network.paths)
        self.paths.service_id = self.service_id

        self.storage_driver = network.paths.storage_driver

    @classmethod
    def get_service(cls, network: Network, filename: str = None) -> Service:
        '''
        Factory for Service class, loads the service metadata from a local
        file. TODO: load the service metadata from the network directory
        server
        '''

        service = Service(network=network)

        service.load(filename=filename)

        return service

    def load_contract(self, filename: str = None):
        '''
        '''

        # TODO: implement validation of the service definition using
        # JSON-Schema

        if filename is None:
            raise NotImplementedError(
                'Downloading service definitions from the directory server '
                'of a network is not yet implemented'
            )

        with open(filename) as file_desc:
            data = json.load(file_desc)

        self.service_id = self.schema['service_id']
        self.service = self.schema['service']
        self.schema = data['schema']

        # TODO: check signature of service data contract
        if self.schema.get('contract_signature'):
            raise NotImplementedError(
                'Data contract signature verification is not yet implemented'
            )
        self.contract_signature = None

        _LOGGER.debug(
            f'Read service {self.service} without signature verification'
        )

    def create_secrets(self, network_services_ca: NetworkServicesCaSecret,
                       password: str = None) -> None:
        '''
        Creates all the secrets of a service

        :raises PermissionError
        '''

        if (self.service_ca or self.members_ca or self.apps_ca or
                self.tls_secret or self.data_secret):
            raise RuntimeError('One or more service secrets already exist')

        if password:
            self.private_key_password = password

        if not self.paths.service_directory_exists(self.service_id):
            self.paths.create_service_directory(self.service_id)

        if not self.paths.secrets_directory_exists():
            self.paths.create_secrets_directory()

        self.create_service_ca(network_services_ca)

        self.create_apps_ca()
        self.create_members_ca()
        self.create_service_secret()
        self.create_data_secret()

    def create_service_ca(self,
                          network_services_ca: NetworkServicesCaSecret = None,
                          ) -> None:
        '''
        Create the service CA

        :raises: ValueError if the service ca already exists
        '''

        self.service_ca = self._create_secret(
            ServiceCaSecret, network_services_ca
        )

    def create_members_ca(self) -> None:
        '''
        Creates the member CA, signed by the Service CA

        :raises: ValueError if no Service CA is available to sign
        the CSR of the member CA
        '''

        self.members_ca = self._create_secret(
            MembersCaSecret, self.service_ca
        )

    def create_apps_ca(self) -> None:
        '''
        Create the CA that signs application secrets
        '''

        self.apps_ca = self._create_secret(AppsCaSecret, self.service_ca)

    def create_service_secret(self) -> None:
        '''
        Creates the service data secret, signed by the Service CA

        :raises: ValueError if no Service CA is available to sign
        the CSR of the service secret
        '''

        self.service_secret = self._create_secret(
            ServiceSecret, self.service_ca
        )

    def create_data_secret(self) -> None:
        '''
        Creates the service data secret, signed by the Service CA

        :raises: ValueError if no Service CA is available to sign
        the CSR of the service secret
        '''

        self.data_secret = self._create_secret(
            ServiceDataSecret, self.service_ca
        )

    def _create_secret(self, secret_cls: Callable, issuing_ca: Secret
                       ) -> Secret:
        '''
        Abstraction for creating secrets for the Service class to avoid
        repetition of code for creating the various member secrets of the
        Service class

        :param secret_cls: callable for one of the classes derived from
        byoda.util.secrets.Secret
        :raises: ValueError, NotImplementedError
        '''

        if not self.service or self.service_id is None:
            raise ValueError(
                'Name and service_id of the service have not been defined'
            )

        if not issuing_ca:
            # TODO
            if type(secret_cls) != ServiceCaSecret:
                raise ValueError(
                    f'No issuing_ca was provided for creating a '
                    f'{type(secret_cls)}'
                )
            else:
                raise NotImplementedError(
                    'Getting a signed certificate from a network directory'
                    'server is not yet implemented'
                )

        secret = secret_cls(
            self.service, self.service_id, network=self.network
        )

        if secret.cert_file_exists():
            raise ValueError(
                f'{type(secret)} cert for {self.service} ({self.service_id}) '
                'already exists'
            )

        if secret.private_key_file_exists():
            raise ValueError(
                f'{type(secret)} key for {self.service} ({self.service_id}) '
                'already exists'
            )

        csr = secret.create_csr()
        issuing_ca.review_csr(csr, source=CsrSource.LOCAL)
        certchain = issuing_ca.sign_csr(csr)
        secret.add_signed_cert(certchain)
        secret.save(password=self.private_key_password)

        return secret

    def load_secrets(self, with_private_key: bool = True, password: str = None
                     ) -> None:
        '''
        Loads all the secrets of a service
        '''
        if self.service_ca:
            self.service_ca = ServiceCaSecret(
                self.service, self.service_id, self.network
            )
            self.service_ca.load(
                with_private_key=with_private_key, password=password
            )

        if not self.apps_ca:
            self.apps_ca = AppsCaSecret(
                self.service, self.service_id, self.network
            )
            self.apps_ca.load(
                with_private_key=with_private_key, password=password
            )

        if not self.members_ca:
            self.members_ca = MembersCaSecret(
                self.service, self.service_id, self.network
            )
            self.members_ca.load(
                with_private_key=with_private_key, password=password
            )

        if not self.tls_secret:
            self.tls_secret = ServiceSecret(
                self.service, self.service_id, self.network
            )
            self.tls_secret.load(
                with_private_key=with_private_key, password=password
            )

        if not self.data_secret:
            self.data_secret = ServiceDataSecret(
                self.service, self.service_id, self.network
            )
            self.data_secret.load(
                with_private_key=with_private_key, password=password
            )
