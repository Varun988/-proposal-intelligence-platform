import numpy as np


class FakeSentenceTransformerModel:
    """Fake Sentence Transformer model for unit tests."""

    def __init__(
        self,
        dimension: int = 3,
    ) -> None:
        self.dimension = dimension
        self.received_texts: list[str] = []
        self.received_normalize_embeddings: bool | None = None
        self.received_convert_to_numpy: bool | None = None
        self.received_show_progress_bar: bool | None = None

    def get_sentence_embedding_dimension(self) -> int:
        """Return the configured fake vector dimension."""

        return self.dimension

    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        """Return deterministic vectors for supplied text."""

        self.received_texts.extend(texts)
        self.received_convert_to_numpy = convert_to_numpy
        self.received_normalize_embeddings = normalize_embeddings
        self.received_show_progress_bar = show_progress_bar

        return np.array(
            [[float(len(text) + index) for index in range(self.dimension)] for text in texts],
            dtype=np.float32,
        )


class FailingSentenceTransformerModel(
    FakeSentenceTransformerModel,
):
    """Fake model that raises during encoding."""

    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        raise RuntimeError("Synthetic encoding failure.")


class InvalidDimensionSentenceTransformerModel(
    FakeSentenceTransformerModel,
):
    """Fake model returning vectors with an incorrect dimension."""

    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        return np.array(
            [[1.0, 2.0] for _ in texts],
            dtype=np.float32,
        )
