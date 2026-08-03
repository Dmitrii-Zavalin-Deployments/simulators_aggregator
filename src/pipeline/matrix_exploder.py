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
    """Recursively computes concrete single-value permutations of any nested JSON structure."""
    if isinstance(target_dict, dict):
        keys = list(target_dict.keys())
        choices = [explode_dict(v) for v in target_dict.values()]
        permutations = []
        for combo in itertools.product(*choices):
            permutations.append(dict(zip(keys, combo)))
        return permutations

    elif isinstance(target_dict, list):
        if not target_dict:
            return [[]]
        if any(isinstance(x, (dict, list)) for x in target_dict):
            element_choices = [explode_dict(x) for x in target_dict]
            permutations = []
            for combo in itertools.product(*element_choices):
                permutations.append(list(combo))
            return permutations
        else:
            return target_dict
    else:
        return [target_dict]

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

    flat_combinations = explode_dict(raw_config)

    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(flat_combinations, f, indent=4)
        
    logger.info(f"✅ Success: Generated {len(flat_combinations)} permutations.")
    logger.info(f"💾 Output saved to: {args.output_path}")

if __name__ == "__main__":  # pragma: no cover
    main()