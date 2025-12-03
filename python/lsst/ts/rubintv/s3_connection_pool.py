"""S3 Connection Pool for efficient reuse of S3Client instances.

This module provides a connection pool to manage S3Client instances and prevent
memory leaks from creating multiple boto3 clients with the same configuration.
"""

import gc
import threading

from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger()

__all__ = ["S3ConnectionPool", "get_shared_s3_client", "force_garbage_collection"]


class S3ConnectionPool:
    """A thread-safe connection pool for S3Client instances.

    This pool maintains a cache of S3Client instances based on their
    configuration parameters (profile_name, bucket_name, endpoint_url).
    Reusing clients prevents memory accumulation from boto3 library
    initialization overhead.
    """

    def __init__(self) -> None:
        self._clients: dict[tuple[str, str, str], S3Client] = {}
        self._lock = threading.Lock()
        self._access_count = 0
        self._gc_threshold = 100  # Trigger GC every 100 accesses

    def get_client(
        self, profile_name: str, bucket_name: str, endpoint_url: str | None = None
    ) -> S3Client:
        """Get or create an S3Client with the specified configuration.

        Parameters
        ----------
        profile_name : `str`
            AWS profile name for authentication
        bucket_name : `str`
            S3 bucket name
        endpoint_url : `str` | `None`
            S3 endpoint URL, None for default

        Returns
        -------
        S3Client
            Cached or newly created S3Client instance
        """
        # Normalize endpoint_url for consistent key generation
        endpoint_key = endpoint_url or ""
        cache_key = (profile_name, bucket_name, endpoint_key)

        with self._lock:
            # Increment access counter and trigger GC if needed
            self._access_count += 1
            if self._access_count >= self._gc_threshold:
                gc.collect()
                self._access_count = 0
                logger.debug("Triggered garbage collection in S3ConnectionPool")

            if cache_key not in self._clients:
                logger.info(
                    f"Creating new S3Client for profile={profile_name}, "
                    f"bucket={bucket_name}, endpoint={endpoint_url}"
                )
                self._clients[cache_key] = S3Client(
                    profile_name=profile_name,
                    bucket_name=bucket_name,
                    endpoint_url=endpoint_url,
                )
                # Force GC after creating new client to clean up
                # initialization overhead
                gc.collect()
            else:
                logger.debug(
                    f"Reusing cached S3Client for profile={profile_name}, "
                    f"bucket={bucket_name}, endpoint={endpoint_url}"
                )

        return self._clients[cache_key]

    def clear_cache(self) -> None:
        """Clear all cached S3Client instances.

        This method can be used for testing or to force recreation
        of all clients.
        """
        with self._lock:
            logger.info(f"Clearing S3Client cache ({len(self._clients)} clients)")
            self._clients.clear()
            self._access_count = 0
            # Force garbage collection after clearing cache
            gc.collect()

    def get_pool_stats(self) -> dict[str, int]:
        """Get statistics about the connection pool.

        Returns
        -------
        `dict` [`str`, `int`]
            dictionary with 'cached_clients' count and access statistics
        """
        with self._lock:
            return {
                "cached_clients": len(self._clients),
                "access_count": self._access_count,
                "gc_threshold": self._gc_threshold,
            }

    def force_gc_and_reset(self) -> None:
        """Force garbage collection and reset access counter.

        This is useful for testing or when you want to ensure
        memory is cleaned up immediately.
        """
        with self._lock:
            gc.collect()
            self._access_count = 0
        logger.info("Forced garbage collection and reset access counter")


# Global connection pool instance
_global_pool = S3ConnectionPool()


def get_shared_s3_client(
    profile_name: str, bucket_name: str, endpoint_url: str | None = None
) -> S3Client:
    """Get a shared S3Client instance from the global connection pool.

    This is the recommended way to obtain S3Client instances to prevent
    memory leaks from boto3 client creation overhead.

    Parameters
    ----------
    profile_name : `str`
        AWS profile name for authentication
    bucket_name : `str`
        S3 bucket name
    endpoint_url : `str` | None
        S3 endpoint URL, None for default

    Returns
    -------
    S3Client
        Cached or newly created S3Client instance
    """
    return _global_pool.get_client(profile_name, bucket_name, endpoint_url)


def clear_s3_client_cache() -> None:
    """Clear the global S3Client cache.

    Useful for testing or forcing recreation of all cached clients.
    """
    _global_pool.clear_cache()


def get_s3_pool_stats() -> dict[str, int]:
    """Get statistics about the global S3 connection pool.

    Returns
    -------
    `dict` [`str`, `int`]
        dictionary with connection pool statistics
    """
    return _global_pool.get_pool_stats()


def force_garbage_collection() -> None:
    """Force garbage collection and reset access counter.

    This is useful for testing or when you want to ensure
    memory is cleaned up immediately.
    """
    _global_pool.force_gc_and_reset()
