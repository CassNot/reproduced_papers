"""Training utilities for the QCNN reproduction."""

from __future__ import annotations

import random
from typing import Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, angle_factor: float) -> float:
    model.eval()
    correct = total = 0
    for xb, yb in loader:
        logits = model(xb * angle_factor)
        pred = logits.argmax(1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return correct / max(1, total)


def train_once(
    Ztr: torch.Tensor,
    ytr: torch.Tensor,
    Zte: torch.Tensor,
    yte: torch.Tensor,
    steps: int,
    batch: int,
    opt_name: str,
    lr: float,
    momentum: float,
    angle_factor: float,
    seed: int,
    model: nn.Module,
) -> float:
    set_seed(seed)

    if opt_name == "adam":
        optim = torch.optim.Adam(model.parameters(), lr=lr)
    else:
        optim = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum, nesterov=True)
    lossf = nn.CrossEntropyLoss()

    train_loader = DataLoader(TensorDataset(Ztr, ytr), batch_size=batch, shuffle=True, drop_last=True)
    test_loader = DataLoader(TensorDataset(Zte, yte), batch_size=512, shuffle=False)

    model.train()
    it = 0
    while it < steps:
        for xb, yb in train_loader:
            optim.zero_grad(set_to_none=True)
            logits = model(xb * angle_factor)
            loss = lossf(logits, yb)
            loss.backward()
            optim.step()
            it += 1
            if it >= steps:
                break

    return evaluate(model, test_loader, angle_factor)
