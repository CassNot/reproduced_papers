"""Main entry point for the QCNN data classification reproduction."""

from __future__ import annotations

import argparse
import json
import statistics
from typing import Callable, List, Tuple

import numpy as np
import torch.nn as nn

from data import make_pca
from model import QConvModel, QuantumPatchKernel, SingleGI
from utils.circuit import (
    build_quantum_kernel_layer,
    required_input_params,
)
from utils.training import train_once


def _parse_configured_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parallel-columns GI on MNIST 0vs1 (PCA-8 everywhere)"
    )
    parser.add_argument("--config", type=str, help="Optional JSON file with CLI arguments")
    parser.add_argument("--steps", type=int, default=200, help="optimizer steps (not epochs)")
    parser.add_argument("--batch", type=int, default=25)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--opt", choices=["adam", "sgd"], default="adam")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--momentum", type=float, default=0.9)
    parser.add_argument("--shots", type=int, default=20000, help="measurement shots for the GI")
    parser.add_argument(
        "--angle_scale",
        choices=["none", "pi", "2pi"],
        default="none",
        help="map [0,1] → unchanged, [0,π], or [0,2π]",
    )
    parser.add_argument("--n_modes", type=int, default=8)
    parser.add_argument("--n_features", type=int, default=8)
    parser.add_argument("--reservoir_mode", action="store_true")
    parser.add_argument(
        "--state_pattern",
        choices=["default", "spaced", "sequential", "periodic"],
        default="default",
    )
    parser.add_argument("--n_photons", type=int, default=4)
    parser.add_argument("--pca_dim", type=int, default=8)

    parser.add_argument("--model", choices=["qconv", "single"], default="qconv")
    parser.add_argument("--qconv_kernels", type=int, default=4)
    parser.add_argument("--qconv_kernel_size", type=int, default=2)
    parser.add_argument("--qconv_stride", type=int, default=1)
    parser.add_argument("--qconv_classical", action="store_true")
    parser.add_argument("--compare_classical", action="store_true")
    parser.add_argument("--qconv_kernel_modes", type=int, default=8)
    parser.add_argument("--qconv_kernel_features", type=int, default=2)

    prelim_args, remaining = parser.parse_known_args()

    config_args: List[str] = []
    if prelim_args.config:
        with open(prelim_args.config, "r", encoding="utf-8") as fh:
            config_data = json.load(fh)
        for key, value in config_data.items():
            flag = f"--{key}"
            if isinstance(value, bool):
                if value:
                    config_args.append(flag)
            elif isinstance(value, list):
                config_args.append(flag)
                config_args.extend(str(item) for item in value)
            else:
                config_args.extend([flag, str(value)])

    args = parser.parse_args(config_args + remaining)
    return args


def _angle_factor(scale: str) -> float:
    if scale == "pi":
        return float(np.pi)
    if scale == "2pi":
        return float(2 * np.pi)
    return 1.0


def _build_quantum_kernel_modules(
    args: argparse.Namespace,
) -> Callable[[], List[QuantumPatchKernel]]:
    def factory() -> List[QuantumPatchKernel]:
        modules: List[QuantumPatchKernel] = []
        for _ in range(args.qconv_kernels):
            layer = build_quantum_kernel_layer(
                kernel_modes=args.qconv_kernel_modes or args.qconv_kernel_size,
                kernel_features=args.qconv_kernel_features,
                kernel_size=args.qconv_kernel_size,
                shots=args.shots,
                n_photons=args.n_photons,
                state_pattern=args.state_pattern,
                reservoir_mode=args.reservoir_mode,
            )
            modules.append(QuantumPatchKernel(layer, patch_dim=args.qconv_kernel_size))
        return modules

    return factory


def _prepare_models(
    args: argparse.Namespace,
    input_dim: int,
    required_inputs: int,
) -> Tuple[List[Tuple[str, Callable[[], nn.Module]]], List[str]]:
    logs: List[str] = []
    builders: List[Tuple[str, Callable[[], nn.Module]]] = []

    if args.model == "single":
        def build_single() -> nn.Module:
            return SingleGI(
                n_modes=args.n_modes,
                n_features=args.n_features,
                n_photons=args.n_photons,
                reservoir_mode=args.reservoir_mode,
                state_pattern=args.state_pattern,
                required_inputs=required_inputs,
                input_dim=input_dim,
                shots=args.shots,
            )

        builders.append(("single", build_single))
        return builders, logs

    # qconv path
    if args.qconv_kernel_size > args.pca_dim:
        raise ValueError("qconv kernel_size cannot exceed the PCA dimension.")
    if args.qconv_stride <= 0:
        raise ValueError("qconv stride must be a positive integer.")
    if args.qconv_kernel_features != args.qconv_kernel_size:
        raise ValueError("--qconv_kernel_features must match --qconv_kernel_size for quantum kernels.")

    num_windows = 1 + (input_dim - args.qconv_kernel_size) // args.qconv_stride
    if num_windows <= 0:
        raise ValueError("qconv configuration results in zero sliding windows.")

    base_kwargs = dict(
        input_dim=input_dim,
        n_kernels=args.qconv_kernels,
        kernel_size=args.qconv_kernel_size,
        stride=args.qconv_stride,
    )

    # Classical variant (always available for comparison/logging)
    classical_sample = QConvModel(bias=True, **base_kwargs)
    classical_output_dim = classical_sample.output_features

    def build_classical() -> nn.Module:
        return QConvModel(bias=True, **base_kwargs)

    use_quantum = not args.qconv_classical or args.compare_classical
    if args.qconv_classical and not args.compare_classical:
        logs.append(
            f"classical: {args.qconv_kernels} kernels → {classical_output_dim} dims"
        )
        builders.append(("qconv_classical_only", build_classical))
        return builders, logs

    quantum_factory = _build_quantum_kernel_modules(args)
    quantum_modules = quantum_factory()
    quantum_sample = QConvModel(bias=False, kernel_modules=quantum_modules, **base_kwargs)
    quantum_output_dim = quantum_sample.output_features
    logs.append(
        f"quantum: {args.qconv_kernels} kernels → {quantum_output_dim} dims"
    )

    def build_quantum() -> nn.Module:
        return QConvModel(
            bias=False,
            kernel_modules=quantum_factory(),
            **base_kwargs,
        )

    builders.append(("qconv_quantum", build_quantum))

    if args.compare_classical or not use_quantum:
        logs.append(
            f"classical: {args.qconv_kernels} kernels → {classical_output_dim} dims"
        )
        builders.append(("qconv_classical", build_classical))

    return builders, logs


def main() -> None:
    args = _parse_configured_args()

    angle_factor = _angle_factor(args.angle_scale)
    required_inputs = required_input_params(args.n_modes, args.n_features)

    (Ztr, ytr), (Zte, yte) = make_pca(args.pca_dim)
    input_dim = Ztr.shape[-1]

    if args.model == "single" and input_dim != required_inputs:
        raise ValueError(
            f"Single GI model requires feature dimension {required_inputs}, but PCA produced {input_dim}."
        )

    builders, conv_logs = _prepare_models(args, input_dim, required_inputs)

    print(
        f"PCA-{args.pca_dim} ready: train {Ztr.shape}, test {Zte.shape} | shots={args.shots}, angle={args.angle_scale}"
    )
    if conv_logs:
        print("Convolution configurations:")
        for log_entry in conv_logs:
            print(f"  - {log_entry}")

    comparison_results = []
    for name, builder in builders:
        print(f"\n=== Evaluating {name} ({args.seeds} seed{'s' if args.seeds > 1 else ''}) ===")
        variant_accs = []
        for s in range(args.seeds):
            print(f"[Seed {s+1}/{args.seeds}]")
            model = builder()
            print(
                f"Number of trainable parameters = {sum(p.numel() for p in model.parameters() if p.requires_grad)}"
            )
            acc = train_once(
                Ztr, ytr, Zte, yte,
                steps=args.steps,
                batch=args.batch,
                opt_name=args.opt,
                lr=args.lr,
                momentum=args.momentum,
                angle_factor=angle_factor,
                seed=1235 + s,
                model=model,
            )
            print(f"  Test accuracy: {acc*100:.2f}%")
            variant_accs.append(acc)
        mean = statistics.mean(variant_accs)
        std = statistics.stdev(variant_accs) if len(variant_accs) > 1 else 0.0
        print(f"→ Summary for {name}: mean {mean*100:.2f}% ± {std*100:.2f}%")
        comparison_results.append((name, variant_accs, mean, std))

    if len(comparison_results) > 1:
        print("\n=== Overall Comparison ===")
        for name, accs, mean, std in comparison_results:
            acc_line = ", ".join(f"{a*100:.2f}%" for a in accs)
            print(f"{name}: [{acc_line}] → mean {mean*100:.2f}% ± {std*100:.2f}%")
    elif comparison_results:
        name, accs, mean, std = comparison_results[0]
        print("\n=== Summary ===")
        print("Accuracies:", ", ".join(f"{a*100:.2f}%" for a in accs))
        print(f"Mean ± Std: {mean*100:.2f}% ± {std*100:.2f}%")


if __name__ == "__main__":
    main()
