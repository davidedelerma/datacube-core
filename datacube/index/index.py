from __future__ import absolute_import

import logging

from datacube.drivers.postgres import PostgresDb
from datacube.index._datasets import DatasetResource
from datacube.index.metadata_types import MetadataTypeResource, default_metadata_type_docs
from datacube.index.products import ProductResource
from datacube.index.users import UserResource

_LOG = logging.getLogger(__name__)


class Index(object):
    """
    Access to the datacube index.

    Thread safe. But not multiprocess safe once a connection is made (db connections cannot be shared between processes)
    You can close idle connections before forking by calling close(), provided you know no other connections are active.
    Or else use a separate instance of this class in each process.

    :ivar datacube.index._datasets.DatasetResource datasets: store and retrieve :class:`datacube.model.Dataset`
    :ivar datacube.index._datasets.DatasetTypeResource products: store and retrieve :class:`datacube.model.DatasetType`\
    (should really be called Product)
    :ivar datacube.index._datasets.MetadataTypeResource metadata_types: store and retrieve \
    :class:`datacube.model.MetadataType`
    :ivar UserResource users: user management

    :type users: datacube.index.users.UserResource
    :type datasets: datacube.index._datasets.DatasetResource
    :type products: datacube.index._datasets.DatasetTypeResource
    :type metadata_types: datacube.index._datasets.MetadataTypeResource
    """

    def __init__(self, db):
        # type: (PostgresDb) -> None
        self._db = db

        self.users = UserResource(db)
        self.metadata_types = MetadataTypeResource(db)
        self.products = ProductResource(db, self.metadata_types)
        self.datasets = DatasetResource(db, self.products)

    @property
    def url(self):
        # type: () -> URL
        return self._db.url

    @classmethod
    def from_config(cls, config, application_name=None, validate_connection=True):
        db = PostgresDb.from_config(config, application_name=application_name,
                                    validate_connection=validate_connection)
        return cls(db)

    def init_db(self, with_default_types=True, with_permissions=True):
        is_new = self._db.init(with_permissions=with_permissions)

        if is_new and with_default_types:
            _LOG.info('Adding default metadata types.')
            for doc in default_metadata_type_docs():
                self.metadata_types.add(self.metadata_types.from_doc(doc), allow_table_lock=True)

        return is_new

    def close(self):
        """
        Close any idle connections database connections.

        This is good practice if you are keeping the Index instance in scope
        but wont be using it for a while.

        (Connections are normally closed automatically when this object is deleted: ie. no references exist)
        """
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def __repr__(self):
        return "Index<db={!r}>".format(self._db)


class DefaultIndexDriver(object):
    @staticmethod
    def connect_to_index(config, application_name=None, validate_connection=True):
        return Index.from_config(config, application_name, validate_connection)


def index_driver_init():
    return DefaultIndexDriver()
