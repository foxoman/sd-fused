from __future__ import annotations
from typing import Optional

import torch
from torch import Tensor

from ...utils import softmax


def attention(
    q: Tensor,  # (B, T, C)
    k: Tensor,  # (B, T', C)
    v: Tensor,  # (B, T', C)
    chunks: Optional[int] = None,
) -> Tensor:
    assert q.shape[0] == k.shape[0] == v.shape[0]
    assert q.shape[2] == k.shape[2] == v.shape[2]
    assert k.shape[1] == v.shape[1]

    k = k.transpose(1, 2)

    if chunks is None:
        attn = softmax(q @ k, dim=-1)
        del q, k

        return attn @ v

    # split-attention score
    shape = (q.size(0), q.size(1), k.size(1))
    out = torch.empty(shape, device=q.device, dtype=q.dtype)
    for i in range(0, len(k), chunks):
        s = slice(i, i + chunks)

        attn = softmax(q[s] @ k[s], dim=-1)
        out[s] = attn @ v[s]
        del attn

    return out


q = torch.randn(8, 1024, 80)
k = torch.randn(8, 1024, 80)
v = torch.randn(8, 1024, 80)
out = attention(q, k, v)
out.shape
