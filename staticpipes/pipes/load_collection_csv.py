import csv
import os
import tempfile

import requests

from staticpipes.collection import Collection, CollectionRecord
from staticpipes.current_info import CurrentInfo
from staticpipes.pipe_base import BasePipe


class PipeLoadCollectionCSV(BasePipe):
    """
    Creates a collection and loads data from a CSV in the source directory.

    The first row of the CSV is used as field names.

    The first column of the CSV is used as the id of items in the collection.
    """

    def __init__(self, directory=None, filename=None, url=None, collection_name="data"):
        if filename and url:
            raise Exception("Pass one of filename or URL, not both.")
        if not (filename or url):
            raise Exception("Pass one of filename or URL, not nothing.")
        self._directory = directory
        self._filename = filename
        self._url = url
        self._collection_name = collection_name

    def start_prepare(self, current_info: CurrentInfo) -> None:
        """"""
        collection = Collection()

        if self._filename:
            with self.source_directory.get_contents_as_filepointer(
                self._directory or "", self._filename
            ) as fp:
                self._load(fp, collection)
        elif self._url:
            r = requests.get(self._url)
            fp, temp_file_name = tempfile.mkstemp()
            os.close(fp)
            with open(temp_file_name, "w") as fp:
                fp.write(r.text)
            with open(temp_file_name) as fp:
                self._load(fp, collection)

        current_info.set_context(["collection", self._collection_name], collection)

    def _load(self, fp, collection):
        csv_reader = csv.reader(
            fp,
        )
        header_row = next(csv_reader)
        for row in csv_reader:
            if row:
                data = {header_row[i]: row[i] for i in range(1, len(row))}
                collection.add_record(CollectionRecord(id=row[0], data=data))

    # TODO reload on watch
