"""
Usage 1 (after running 'run_two_fold_readout.py' for k=7 and k=8):
    python readout_visu.py --first
    -> Enter the path to first_readout_detailed_results_k_7.json:
    -> Enter the path to first_readout_detailed_results_k_8.json:

Usage 2 (after running 'run_modes_pair_readout.py'):
    python readout_visu.py --second
    -> Enter the path to second_readout_detailed_results.json:

Usage 1 is to reproduce Figure 4 b) from the reference paper which displays the train and test accuracies reached with
the first readout training method: associate 7 or 8 two-fold events to label 0 and the rest to label 1.

Usage 2 is to reproduce Figure 4 a) from the reference paper which displays the train and test accuracies reached with
the second readout training method: associate a pair of modes to label 0 and the rest to label 1.
"""

import argparse
import json
import os

import matplotlib.pyplot as plt
import numpy as np


def readout_visu_first():
    path_7 = input("Enter the path to first_readout_detailed_results_k_7.json: ").strip()
    path_8 = input("Enter the path to first_readout_detailed_results_k_8.json: ").strip()

    output_path_7 = os.path.join(
        os.path.dirname(path_7),
        "first_readout_tain_vs_test_accs.png"
    )
    output_path_8 = os.path.join(
        os.path.dirname(path_8),
        "first_readout_tain_vs_test_accs.png"
    )

    # Load data for k=7
    with open(path_7) as f:
        data_7 = json.load(f)

    # Load data for k=8
    with open(path_8) as f:
        data_8 = json.load(f)

    # Process k=7 data
    train_accs_7 = []
    test_accs_7 = []
    run_idx = 0
    while f"k_7_run_{run_idx}" in data_7:
        train_accs_7.append(data_7[f"k_7_run_{run_idx}"]["final_train_acc"])
        test_accs_7.append(data_7[f"k_7_run_{run_idx}"]["final_test_acc"])
        run_idx += 1

    # Process k=8 data
    train_accs_8 = []
    test_accs_8 = []
    run_idx = 0
    while f"k_8_run_{run_idx}" in data_8:
        train_accs_8.append(data_8[f"k_8_run_{run_idx}"]["final_train_acc"])
        test_accs_8.append(data_8[f"k_8_run_{run_idx}"]["final_test_acc"])
        run_idx += 1

    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Scatter plot with matching colors
    ax.scatter(train_accs_8, test_accs_8, color='blue', alpha=0.7,
               label='k=8', s=20)
    ax.scatter(train_accs_7, test_accs_7, color='orange', alpha=0.7,
               label='k=7', s=20)

    # Define tolerance (you can adjust this threshold as needed)
    tolerance = 1e-2  # A small tolerance to consider values close to 1.0

    # For blue (k=8)
    blue_mask = (np.isclose(train_accs_8, 1.0, atol=tolerance)) & (np.isclose(test_accs_8, 1.0, atol=tolerance))
    blue_proportion = np.sum(blue_mask) / len(train_accs_8)

    # For orange (k=7)
    orange_mask = (np.isclose(train_accs_7, 1.0, atol=tolerance)) & (np.isclose(test_accs_7, 1.0, atol=tolerance))
    orange_proportion = np.sum(orange_mask) / len(train_accs_7)

    # Print the results
    print(f"Proportion of (1.0, 1.0) ± {tolerance} points for k=8 (blue): {blue_proportion:.4f}")
    print(f"Proportion of (1.0, 1.0) ± {tolerance} points for k=7 (orange): {orange_proportion:.4f}")

    # Formatting
    ax.set_xlabel('Training accuracy')
    ax.set_ylabel('Testing accuracy')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Adjust axis ranges based on data
    all_train = train_accs_7 + train_accs_8
    all_test = test_accs_7 + test_accs_8

    if all_train and all_test:
        x_min, x_max = min(all_train), max(all_train)
        y_min, y_max = min(all_test), max(all_test)

        # Add small margins
        x_margin = (x_max - x_min) * 0.05 if x_max != x_min else 0.05
        y_margin = (y_max - y_min) * 0.05 if y_max != y_min else 0.05

        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)

    plt.tight_layout()

    # Save to both paths
    plt.savefig(output_path_7, dpi=300, bbox_inches='tight')
    plt.savefig(output_path_8, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Figure saved to: {output_path_7}")
    print(f"Figure saved to: {output_path_8}")

    return


def readout_visu_second():
    path = input("Enter the path to second_readout_detailed_results.json: ").strip()
    output_path = os.path.join(os.path.dirname(path), "second_readout_accs_vs_modes.png")

    # Load data
    with open(path) as f:
        data = json.load(f)

    # Create mode pair mapping
    mode_pairs = []
    for i in range(3, 8):
        for j in range(i + 1, 9):
            mode_pairs.append((i, j))

    # Process data
    train_means = []
    train_stds = []
    test_means = []
    test_stds = []
    x_labels = []

    for pair_idx, (mode1, mode2) in enumerate(mode_pairs):
        # Find all runs for this pair
        train_accs = []
        test_accs = []

        run_idx = 0
        while f"pair_{pair_idx}_run_{run_idx}" in data:
            train_accs.append(data[f"pair_{pair_idx}_run_{run_idx}"]["final_train_acc"])
            test_accs.append(data[f"pair_{pair_idx}_run_{run_idx}"]["final_test_acc"])
            run_idx += 1

        if train_accs:  # If we have data for this pair
            train_means.append(np.mean(train_accs))
            train_stds.append(np.std(train_accs))
            test_means.append(np.mean(test_accs))
            test_stds.append(np.std(test_accs))
            x_labels.append(f"({mode1},{mode2})")

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x_pos = np.arange(len(x_labels))
    offset = 0.1  # Small horizontal offset to separate train and test points

    # Plot with error bars and slight horizontal separation
    ax.errorbar(x_pos - offset, train_means, yerr=train_stds, fmt='o', color='blue',
                label='Training set', capsize=3, markersize=4)
    ax.errorbar(x_pos + offset, test_means, yerr=test_stds, fmt='o', color='red',
                label='Test set', capsize=3, markersize=4)

    # Formatting
    ax.set_xlabel('Modes associated to label 0')
    ax.set_ylabel('Average accuracy')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Adjust y-axis based on data
    train_means + test_means
    y_min = 0.0
    y_max = 1.0
    ax.set_ylim(y_min, y_max)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Figure saved to: {output_path}")

    return


def main():
    parser = argparse.ArgumentParser(description="Example script with flags")

    # Create a mutually exclusive group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--first', action='store_true', help='Use first option')
    group.add_argument('--second', action='store_true', help='Use second option')

    args = parser.parse_args()

    # Check which flag was used
    if args.first:
        readout_visu_first()
    elif args.second:
        readout_visu_second()
    else:
        raise Exception('You must specify either first or second usage with "--first" or "--second".')


if __name__ == '__main__':
    main()
