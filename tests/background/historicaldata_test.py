from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..conftest import mock_s3_service
from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.fixture(scope="function")
def rubin_data_mocker(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        mocker = RubinDataMocker(m.locations, s3_required=True)
        yield mocker


@pytest.fixture
def historical(rubin_data_mocker: RubinDataMocker) -> HistoricalPoller:
    return HistoricalPoller(m.locations)


@pytest.fixture(scope="function")
def c_poller_no_mock_data(rubin_data_mocker: RubinDataMocker) -> Any:
    with mock_s3_service():
        yield HistoricalPoller(m.locations)


# TODO : Write tests for the HistoricalData class.
# see DM-44273
