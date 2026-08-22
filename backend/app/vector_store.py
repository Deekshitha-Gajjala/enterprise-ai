import pickle
from pathlib import Path

import numpy as np

from sentence_transformers import SentenceTransformer


class VectorStore:
    """
    Local semantic vector store.

    Uses:
        SentenceTransformers
        NumPy

    No FAISS.
    No Pinecone.

    This avoids the old records/index mismatch problem.
    """

    def __init__(
        self,
        folder_path: str = "vector_db",
    ):

        self.folder_path = Path(
            folder_path
        )

        self.folder_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.records_path = (
            self.folder_path / "records.pkl"
        )

        self.vectors_path = (
            self.folder_path / "vectors.npy"
        )

        print(
            "Loading embedding model..."
        )

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.dimension = 384

        self.records = []

        self.vectors = np.empty(
            (0, self.dimension),
            dtype=np.float32,
        )

        self.load()

    # ============================================================
    # EMPTY STORE
    # ============================================================

    def _empty(self):

        self.records = []

        self.vectors = np.empty(
            (0, self.dimension),
            dtype=np.float32,
        )

    # ============================================================
    # LOAD
    # ============================================================

    def load(self):
        """
        Load existing vector database.

        IMPORTANT:
        This function takes NO arguments.
        """

        if (
            not self.records_path.exists()
            or not self.vectors_path.exists()
        ):

            self._empty()

            return

        try:

            with open(
                self.records_path,
                "rb",
            ) as file:

                records = pickle.load(file)

            vectors = np.load(
                self.vectors_path
            )

            if not isinstance(
                records,
                list,
            ):

                raise ValueError(
                    "records.pkl does not contain a list"
                )

            if (
                vectors.ndim != 2
                or vectors.shape[1]
                != self.dimension
            ):

                raise ValueError(
                    f"Invalid vector shape: {vectors.shape}"
                )

            if (
                len(records)
                != vectors.shape[0]
            ):

                raise ValueError(
                    "Record/vector count mismatch"
                )

            self.records = records

            self.vectors = vectors.astype(
                np.float32
            )

            print(
                "Vector database loaded successfully:",
                len(self.records),
                "chunks",
            )

        except Exception as error:

            print(
                "Old vector database is invalid:"
            )

            print(error)

            print(
                "Starting with an empty vector database."
            )

            self._empty()

    # ============================================================
    # SAVE
    # ============================================================

    def save(self):

        with open(
            self.records_path,
            "wb",
        ) as file:

            pickle.dump(
                self.records,
                file,
            )

        np.save(
            self.vectors_path,
            self.vectors,
        )

    # ============================================================
    # REBUILD
    # ============================================================

    def rebuild(
        self,
        records,
    ):

        records = records or []

        self.records = list(records)

        if not self.records:

            self._empty()

            self.save()

            print(
                "Vector database rebuilt: 0 chunks"
            )

            return

        texts = [
            str(
                record.get(
                    "text",
                    "",
                )
            )
            for record in self.records
        ]

        print(
            "Creating embeddings..."
        )

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        vectors = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if (
            vectors.ndim != 2
            or vectors.shape[1]
            != self.dimension
        ):

            raise ValueError(
                f"Invalid embedding shape: {vectors.shape}"
            )

        self.vectors = vectors

        self.save()

        print(
            "Vector database rebuilt:",
            len(self.records),
            "chunks",
        )

    # ============================================================
    # SEARCH
    # ============================================================

    def search(
        self,
        query: str,
        top_k: int = 6,
    ):

        if (
            not self.records
            or self.vectors.size == 0
        ):

            return []

        query_vector = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        query_vector = query_vector.astype(
            np.float32
        )

        scores = np.dot(
            self.vectors,
            query_vector,
        )

        top_k = max(
            1,
            min(
                int(top_k),
                len(self.records),
            ),
        )

        order = np.argsort(
            scores
        )[::-1][:top_k]

        results = []

        for idx in order:

            index = int(idx)

            record = self.records[index]

            results.append(
                {
                    **record,
                    "score": float(
                        scores[index]
                    ),
                }
            )

        return results