#!/usr/bin/env python3
import argparse
import itertools
import json
import logging
import os
import sys

# Configure logging to output to stdout (ideal for GitHub Actions console)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MatrixExploder")

def explode_dict(target_dict):
    """Recursively computes the Cartesian product of a dictionary containing lists."""
    if not isinstance(target_dict, dict):
        return [target_dict]
        
    keys, values = [], []
    for k, v in target_dict.items():
        keys.append(k)
        if isinstance(v, dict):
            values.append(explode_dict(v))
        elif isinstance(v, list):
            values.append(v)
        else:
            values.append([v])
            
    permutations = []
    for combination in itertools.product(*values):
        perm_dict = {}
        for k, v in zip(keys, combination):
            perm_dict[k] = v
        permutations.append(perm_dict)
    return permutations

def main():
    parser = argparse.ArgumentParser(description="Explode array configurations into flat single-value permutations.")
    parser.add_argument("--config-path", required=True, help="Path to input JSON with range arrays")
    parser.add_argument("--output-path", required=True, help="Target destination for output array")
    args = parser.parse_args()

    logger.info(f"🚀 Initializing Matrix Exploder. Reading: {args.config_path}")

    if not os.path.exists(args.config_path):
        error_msg = f"❌ Configuration file not found: {args.config_path}"
        logger.error(error_msg)
        sys.exit(1)

    try:
        with open(args.config_path, "r") as f:
            raw_config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        sys.exit(1)

    keys, values = [], []
    for k, v in raw_config.items():
        keys.append(k)
        if k == "boundary_map" and isinstance(v, dict):
            values.append(explode_dict(v))
        elif isinstance(v, list):
            values.append(v)
        else:
            values.append([v])

    flat_combinations = []
    for comb in itertools.product(*values):
        flat_combinations.append(dict(zip(keys, comb)))

    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(flat_combinations, f, indent=4)
        
    logger.info(f"✅ Success: Generated {len(flat_combinations)} permutations.")
    logger.info(f"💾 Output saved to: {args.output_path}")

if __name__ == "__main__":  # pragma: no cover
    main()