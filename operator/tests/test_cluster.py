"""K8sOperatorCluster.apply() contract: create-if-absent.

An already-existing child makes the create 409; apply must treat that as
success. This is what reattaches the unowned persistent-workspace PVC
(ADR-0010) on relaunch instead of failing the reconcile.
"""

import pytest
from kubernetes.client.rest import ApiException

from cluster import K8sOperatorCluster


async def test_create_or_ignore_swallows_conflict():
    def already_exists(**kwargs):
        raise ApiException(status=409)

    await K8sOperatorCluster._create_or_ignore(
        already_exists, "PVC", "ws-rstudio-abcdef123456"
    )


async def test_create_or_ignore_propagates_other_errors():
    def forbidden(**kwargs):
        raise ApiException(status=403)

    with pytest.raises(ApiException):
        await K8sOperatorCluster._create_or_ignore(
            forbidden, "PVC", "ws-rstudio-abcdef123456"
        )
