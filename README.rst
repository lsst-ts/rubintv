########
rubin-tv
########

A web app that shows streaming views of butler datasets.

The datasets are gathered from three locations:
Summit
SLAC
Tucson

Data is gathered and stored centrally in the cloud, with each location in it's own
storage container or bucket (Google Cloud Service/S3)

The app continually polls the buckets local to it for the current observation
date and scrapes for the entire history daily at change of day.


rubin-tv is developed with the `Safir <https://safir.lsst.io>`__ framework.
`Get started with development with the tutorial <https://safir.lsst.io/set-up-from-template.html>`__.
