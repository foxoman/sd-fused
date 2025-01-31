from __future__ import annotations

import torch.nn as nn
from torch import Tensor

from ..activation import SiLU
from ..base import Linear


class TimestepEmbedding(nn.Sequential):
    def __init__(
        self,
        *,
        channel: int,
        time_embed_dim: int,
        use_silu: bool = True,
    ) -> None:

        self.channel = channel
        self.time_embed_dim = time_embed_dim
        self.use_silu = use_silu

        layers = (
            Linear(channel, time_embed_dim),
            SiLU() if use_silu else nn.Identity(),
            Linear(time_embed_dim, time_embed_dim),
        )

        super().__init__(*layers)

    def __call__(self, x: Tensor) -> Tensor:
        return super().forward(x)
