from __future__ import annotations
from typing import Optional
from typing_extensions import Self

from dataclasses import dataclass, field
from PIL.PngImagePlugin import PngInfo

import torch
from torch import Tensor

from ..image import ResizeModes, image2tensor, image_base64

SAVE_ARGS = [
    "eta",
    "steps",
    "scale",
    "height",
    "width",
    "seed",
    "negative_prompt",
    "sub_seed",
    "interpolation",
    "prompt",
    "strength",
    "mode",
    "image_base64",
    "mask_base64",
]


@dataclass
class Parameters:
    """Hold information from a single image generation."""

    eta: float
    steps: int
    scale: float  # TODO optional!
    height: int
    width: int
    seed: int
    negative_prompt: str
    sub_seed: Optional[int] = None
    interpolation: Optional[float] = None
    prompt: Optional[str] = None
    img: Optional[str] = None
    mask: Optional[str] = None
    strength: Optional[float] = None
    mode: Optional[ResizeModes] = None

    device: Optional[torch.device] = field(default=None, repr=False)
    dtype: Optional[torch.dtype] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        assert self.height % 8 == 0
        assert self.width % 8 == 0

        if self.img is None:
            assert self.mode is None
            assert self.strength is None
            assert self.mask is None
        else:
            assert self.mode is not None
            assert self.strength is not None

        if self.sub_seed is None:
            assert self.interpolation is None
        else:
            assert self.interpolation is not None

    @property
    def unconditional(self) -> bool:
        return self.prompt is None

    def can_share_batch(self, other: Self) -> bool:
        """Determine if two parameters can share a batch."""

        value = self.steps == other.steps
        value &= self.strength == other.strength
        value &= self.height == other.height
        value &= self.width == other.width
        # guided/inguided?
        value &= self.unconditional == other.unconditional  # XNOR?

        return value

    @property
    # @lru_cache(None) # TODO cached_property?
    def image_data(self) -> Optional[Tensor]:
        """Image data as a Tensor."""

        if self.img is None or self.mode is None:
            return

        return image2tensor(
            self.img, self.height, self.width, self.mode, self.device
        )

    @property
    # @lru_cache(None)
    def mask_data(self) -> Optional[Tensor]:
        """Mask data as a Tensor."""

        if self.mask is None or self.mode is None:
            return

        data = image2tensor(
            self.mask, self.height, self.width, self.mode, self.device
        )

        # single-channel
        data = data.float().mean(dim=1, keepdim=True)

        return data >= 255 / 2  # bool-Tensor

    @property
    # @lru_cache(None)
    def image_base64(self) -> Optional[str]:
        """Image data as a base64 string."""

        if self.img is None:
            return

        return image_base64(self.img)

    @property
    # @lru_cache(None)
    def mask_base64(self) -> Optional[str]:
        """Mask data as a base64 string."""

        if self.mask is None:
            return

        return image_base64(self.mask)

    @property
    def png_info(self) -> PngInfo:
        """PNG metadata."""

        info = PngInfo()

        for key in SAVE_ARGS:
            value = getattr(self, key)

            if value is None:
                continue
            if isinstance(value, (int, float)):
                value = str(value)

            info.add_text(f"SD {key}", value)

        return info
