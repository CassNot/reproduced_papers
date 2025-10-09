"""Data preparation utilities for the QCNN reproduction."""

from __future__ import annotations

import torch
from torchvision import datasets, transforms
from sklearn.decomposition import PCA


def make_pca(k: int):
    to_t = transforms.Compose([transforms.ToTensor()])
    base_tr = datasets.MNIST("./data", train=True, download=True, transform=to_t)
    base_te = datasets.MNIST("./data", train=False, download=True, transform=to_t)

    def filt(base):
        Xs, Ys = [], []
        for img, lab in base:
            if int(lab) in (0, 1):
                Xs.append(img.view(-1).float())
                Ys.append(0 if int(lab) == 0 else 1)
        return torch.stack(Xs, 0), torch.tensor(Ys, dtype=torch.long)

    Xtr, ytr = filt(base_tr)
    Xte, yte = filt(base_te)
    pca = PCA(n_components=k, svd_solver="full", whiten=False, random_state=0)
    Ztr_raw = torch.from_numpy(pca.fit_transform(Xtr.numpy())).float()
    Zte_raw = torch.from_numpy(pca.transform(Xte.numpy())).float()
    mins = Ztr_raw.min(0, keepdim=True).values
    maxs = Ztr_raw.max(0, keepdim=True).values
    Ztr = torch.clamp((Ztr_raw - mins) / (maxs - mins + 1e-8), 0.0, 1.0)
    Zte = torch.clamp((Zte_raw - mins) / (maxs - mins + 1e-8), 0.0, 1.0)
    return (Ztr, ytr), (Zte, yte)
