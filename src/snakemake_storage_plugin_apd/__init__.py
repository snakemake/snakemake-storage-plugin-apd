from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, List

from apd import get_analysis_data, auth, authw

from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_provider import (  # noqa: F401
    StorageProviderBase,
    StorageQueryValidationResult,
    ExampleQuery,
    Operation,
    QueryType,
)
from snakemake_interface_storage_plugins.storage_object import (
    StorageObjectRead,
    StorageObjectWrite,
)
from snakemake_interface_storage_plugins.io import IOCacheStorageInterface


@dataclass
class StorageProviderSettings(StorageProviderSettingsBase):
    working_group: Optional[str] = field(
        default=None,
        metadata={
            "help": "Working group of the analysis e.g. bnoc",
            "env_var": True,
            "required": False,
        },
    )
    analysis: Optional[str] = field(
        default=None,
        metadata={
            "help": "Name of the analysis e.g. bds2kstkstb",
            "env_var": True,
            "required": False,
        },
    )
    readonly: Optional[bool] = field(
        default=True,
        metadata={
            "help": "Whether access is read-only (True by default). Set to False to"
            "allow write access",
            "env_var": False,
            "requried": False,
        },
    )


class StorageProvider(StorageProviderBase):
    def __post_init__(self):
        self.wg = self.settings.working_group
        self.analysis = self.settings.analysis
        self.readonly = self.settings.readonly
        if self.wg is not None and self.analysis is not None:
            self.datasets = get_analysis_data(self.wg, self.analysis)
        self.base_provider = "xrootd"

    def get_files(self, query: dict) -> List[str]:
        auth_func = auth if self.readonly else authw
        return [auth_func(f) for f in self.datasets(**query)]

    @classmethod
    def example_queries(cls) -> List[ExampleQuery]:
        """Return an example queries with description for this storage provider (at
        least one)."""
        return [
            ExampleQuery(
                query={
                    "polarity": ["magup"],
                    "eventtype": "13104007",
                    "datatype": "11",
                },
                description="An example apd query",
                type=QueryType.ANY,
            ),
        ]

    # ?
    def rate_limiter_key(self, query: str, operation: Operation) -> Any:
        """Return a key for identifying a rate limiter given a query and an operation.

        This is used to identify a rate limiter for the query.
        E.g. for a storage provider like http that would be the host name.
        For s3 it might be just the endpoint URL.
        """
        return "xrootd"

    def default_max_requests_per_second(self) -> float:
        """Return the default maximum number of requests per second for this storage
        provider."""
        return 1.0

    def use_rate_limiter(self) -> bool:
        """Return False if no rate limiting is needed for this provider."""
        return True

    @classmethod
    def is_valid_query(cls, query: dict) -> StorageQueryValidationResult:
        """Return whether the given query is valid for this storage provider."""
        # Not used in this case, uses the underlying self.base_provider="xrootd" method
        if not isinstance(query, dict):
            return StorageQueryValidationResult(
                valid=False, reason="apd query must be a dict", query=query
            )
        return StorageQueryValidationResult(
            valid=False,
            reason="apd query is validated on instantiation and for individual files the xrootd plugin is used instead",
            query=query,
        )

    def postprocess_query(self, query: str) -> str:
        """Postprocess the query by adding any global settings to the url."""
        return query


# This is unused -- instead the xrootd plugin storage_object is always used
class StorageObject(StorageObjectRead, StorageObjectWrite):
    # For compatibility with future changes, you should not overwrite the __init__
    # method. Instead, use __post_init__ to set additional attributes and initialize
    # futher stuff.

    async def inventory(self, cache: IOCacheStorageInterface):
        """From this file, try to find as much existence and modification date
        information as possible. Only retrieve that information that comes for free
        given the current object.
        """
        # This is optional and can be left as is

        # If this is implemented in a storage object, results have to be stored in
        # the given IOCache object, using self.cache_key() as key.
        # Optionally, this can take a custom local suffix, needed e.g. when you want
        # to cache more items than the current query: self.cache_key(local_suffix=...)
        raise NotImplementedError()

    def get_inventory_parent(self) -> Optional[str]:
        """Return the parent directory of this object."""
        # this is optional and can be left as is
        raise NotImplementedError()

    def local_suffix(self) -> str:
        """Return a unique suffix for the local path, determined from self.query."""
        raise NotImplementedError()

    # Check but should be nothing?
    def cleanup(self):
        """Perform local cleanup of any remainders of the storage object."""
        # self.local_path() should not be removed, as this is taken care of by
        # Snakemake.
        raise NotImplementedError()

    def exists(self) -> bool:
        raise NotImplementedError()

    def mtime(self) -> float:
        # return the modification time
        raise NotImplementedError()

    def size(self) -> int:
        # return the size in bytes
        raise NotImplementedError()

    def retrieve_object(self):
        raise NotImplementedError()

    # The following to methods are only required if the class inherits from
    # StorageObjectReadWrite.

    def store_object(self):
        raise NotImplementedError()

    def remove(self):
        # Remove the object from the storage.
        raise NotImplementedError()

    # The following to methods are only required if the class inherits from
    # StorageObjectGlob.

    # TODO
    def list_candidate_matches(self) -> Iterable[str]:
        """Return a list of candidate matches in the storage for the query."""
        # This is used by glob_wildcards() to find matches for wildcards in the query.
        # The method has to return concretized queries without any remaining wildcards.
        # Use snakemake_executor_plugins.io.get_constant_prefix(self.query) to get the
        # prefix of the query before the first wildcard.
        # TODO add support for listing files here
        raise NotImplementedError()
