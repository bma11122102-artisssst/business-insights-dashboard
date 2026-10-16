"""Train and evaluate locally fitted Track 4 models; no hosted model required.

Convenience entry point for Round 2 reviewers. The implementation remains in
vaultdata/ml, including temporal splits, preprocessing, and baseline selection.
"""
import argparse
from vaultdata.ml.evaluate import run_evaluation
from vaultdata.data.track4 import TRACK4_PATH


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='reports', help='Evaluation output directory')
    parser.add_argument('--data', default=str(TRACK4_PATH), help='Directory containing the five official CSV files')
    args = parser.parse_args()
    run_evaluation(args.output, args.data)
