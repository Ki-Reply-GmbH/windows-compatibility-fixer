import logging
import os
import base64
import pandas as pd


class DataStore:
    """
    In our Caches prompt/answer pairs are stored.
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._log = logging.getLogger(__name__)

    def store(self, query: str, result: str) -> bool:
        raise NotImplementedError

    def remove(self, query: str) -> None:
        raise NotImplementedError

    def contains(self, query: str) -> bool:
        raise NotImplementedError

    def retrieve(self, query: str):
        raise NotImplementedError


class NullDataStore(DataStore):
    def contains(self, query: str) -> bool:
        _ = query
        return False

    def store(self, query: str, result: str) -> bool:
        _ = query, result
        return False

    def remove(self, query: str) -> None:
        _ = query

    def retrieve(self, query: str):
        _ = query


class FileBasedStore(DataStore):

    def __init__(
        self,
        base_dir: str,
        storage_dir: str = ".llm_cache",
        index_file: str = "prompts.csv",
    ) -> None:
        super().__init__(base_dir)
        self.storage_dir = os.path.join(base_dir, storage_dir)
        self.index_file = os.path.join(self.storage_dir, index_file)

        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        if not os.path.exists(self.index_file):
            data_frame = pd.DataFrame(columns=["prompt"])
            data_frame.to_csv(self.index_file, index=False)

    def store(self, query: str, result: str) -> bool:
        query = self._serialize_content(query)
        result = self._serialize_content(result)

        if os.path.exists(self.index_file):
            data_frame = pd.read_csv(self.index_file)

            if query in data_frame["prompt"].values:
                entry_id = data_frame.index[data_frame["prompt"] == query].tolist()[0]
                pd.read_csv(f"{self.storage_dir}/{entry_id}.csv")
                return False

            new_row = pd.DataFrame({"prompt": [query]})
            data_frame = pd.concat([data_frame, new_row], ignore_index=True)
        else:
            data_frame = pd.DataFrame({"prompt": [query]})

        data_frame.to_csv(self.index_file, index=False)

        result_df = pd.DataFrame({"answer": [result]})
        result_df.to_csv(f"{self.storage_dir}/{len(data_frame)-1}.csv", index=False)

        return True

    def remove(self, query: str) -> None:
        query = self._serialize_content(query)

        if os.path.exists(self.index_file):
            data_frame = pd.read_csv(self.index_file)

            if query in data_frame["prompt"].values:
                entry_id = data_frame.index[data_frame["prompt"] == query].tolist()[0]
                data_frame = data_frame.drop(entry_id)
                data_frame.to_csv(self.index_file, index=False)

                result_file = f"{self.storage_dir}/{entry_id}.csv"
                if os.path.exists(result_file):
                    os.remove(result_file)

    def contains(self, query: str) -> bool:
        query = self._serialize_content(query)

        if os.path.exists(self.index_file):
            data_frame = pd.read_csv(self.index_file)

            if query in data_frame["prompt"].values:
                self._log.info("Cache hit!")
                return True

        self._log.info("Cache miss!")
        return False

    def retrieve(self, query: str):
        query = self._serialize_content(query)
        if os.path.exists(self.index_file):
            data_frame = pd.read_csv(self.index_file)

            if query in data_frame["prompt"].values:
                entry_id = data_frame.index[data_frame["prompt"] == query].tolist()[0]
                result_df = pd.read_csv(f"{self.storage_dir}/{entry_id}.csv")
                return self._deserialize_content(result_df["answer"].values[0])

        return None

    def _serialize_content(self, text):
        if isinstance(text, dict):
            text = str(text)

        encoded_bytes = base64.b64encode(text.encode("utf-8"))
        encoded_string = encoded_bytes.decode("utf-8")
        return encoded_string

    def _deserialize_content(self, encoded_string):
        decoded_bytes = base64.b64decode(encoded_string.encode("utf-8"))
        decoded_string = decoded_bytes.decode("utf-8")

        return decoded_string