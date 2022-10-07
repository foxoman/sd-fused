#%%
from __future__ import annotations
from typing import Optional

import math

import torch
from torch import Tensor


class DDIMScheduler:
    # https://arxiv.org/abs/2010.02502
    def __init__(
        self,
        *,
        steps: int,
        device: Optional[torch.device] = None,
        dtype: Optional[torch.dtype] = None,
        # seeds: list[int], # TODO pre-generate noises based on seeds
        # ? DO NOT CHANGE!? Make it GLOBAL constant?
        trained_steps: int = 1_000,
        beta_start: float = 0.00085,
        beta_end: float = 0.012,
        power: float = 2,
    ) -> None:
        assert steps <= trained_steps

        self.steps = steps
        self.device = device
        self.dtype = dtype

        # scheduler betas and alphas
        beta_start = math.pow(beta_start, 1 / power)
        beta_end = math.pow(beta_end, 1 / power)
        β = torch.linspace(beta_start, beta_end, trained_steps,).pow(power)

        # increase steps by 1 to account last timestep
        steps += 1

        # trimmed timesteps for selection
        timesteps = torch.linspace(0, 1, steps) * (
            trained_steps - 1
        )  # ?why -1?
        timesteps = timesteps.flip(0).ceil().long()

        # cummulative ᾱ trimmed
        α = 1 - β
        ᾱ = α.cumprod(dim=0)
        ᾱ /= ᾱ.max()  # makes last-value=1
        ᾱ = ᾱ[timesteps]
        ϖ = 1 - ᾱ
        del α, β  # reminder that is not used anymore

        # standard deviation, eq (16)
        σ = torch.sqrt(ϖ[1:] / ϖ[:-1] * (1 - ᾱ[:-1] / ᾱ[1:]))

        # use device/dtype
        self.ᾱ = ᾱ.to(device=device, dtype=dtype)
        self.ϖ = ϖ.to(device=device, dtype=dtype)
        self.σ = σ.to(device=device, dtype=dtype)
        self.timesteps = timesteps.to(device=device)

    def step(
        self, pred_noise: Tensor, latents: Tensor, i: int, eta: float = 0,
    ) -> Tensor:
        """Get the previous latents according to the DDIM paper."""

        assert 0 <= i < self.steps
        # TODO add support for i as Tensor

        # eq (12) part 1
        pred_latent = latents - self.ϖ[i].sqrt() * pred_noise
        pred_latent /= self.ᾱ[i].sqrt()

        # eq (12) part 2
        temp = 1 - self.ᾱ[i + 1] - self.σ[i].mul(eta).square()
        pred_dir = torch.sqrt(temp) * pred_noise

        # eq (12) part 3
        # TODO add seeds
        noise = torch.randn_like(latents) * self.σ[i] * eta

        # full eq (12)
        return pred_latent * self.ᾱ[i + 1].sqrt() + pred_dir + noise

    def add_noise(self, latents: Tensor, eps: Tensor, i: int) -> Tensor:
        """Add noise to latents according to the index i."""

        assert 0 <= i < self.steps
        # TODO add support for i as Tensor

        # eq 4
        return latents * self.ᾱ[i].sqrt() + eps * self.ϖ[i].sqrt()

    def cutoff_index(self, strength: float) -> int:
        """For a given strength [0, 1) what is the cutoff index?"""

        assert 0 < strength <= 1

        return math.ceil(len(self) * (1 - strength))

    def __len__(self) -> int:
        return self.steps
