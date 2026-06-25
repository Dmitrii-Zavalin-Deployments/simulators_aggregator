#!/usr/bin/env python3
import argparse
import json
import itertools
import os

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

    if not os.path.exists(args.config_path):
        raise FileNotFoundError(f"Source configuration file not found at: {args.config_path}")

    with open(args.config_path, "r") as f:
        raw_config = json.load(f)

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
        
    print(f"✅ Matrix exploder completed. Saved {len(flat_combinations)} unique entries to {args.output_path}")

if __name__ == "__main__":
    main()