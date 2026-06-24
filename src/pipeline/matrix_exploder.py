# src/pipeline/matrix_exploder.py

import itertools
from typing import Dict, Any, List

def _flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, list]:
    """
    Recursively flattens a nested dictionary into a 1D key-value map.
    Example: {'boundary': {'wall': ['no-slip']}} -> {'boundary.wall': ['no-slip']}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, v))
        else:
            raise TypeError(f"CRITICAL: Value at '{new_key}' is not a list. All leaf nodes must be arrays.")
    return dict(items)

def _unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
    """
    Reconstructs a flat dictionary back into a nested structural hierarchy.
    """
    result_dict = {}
    for k, v in d.items():
        parts = k.split(sep)
        d_ref = result_dict
        for part in parts[:-1]:
            if part not in d_ref:
                d_ref[part] = {}
            d_ref = d_ref[part]
        d_ref[parts[-1]] = v
    return result_dict

def explode_configuration(base_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Takes a configuration dictionary with arrays as leaf nodes and generates 
    all possible single-value Cartesian permutations.
    """
    # 1. Flatten the nested structure to isolate the value arrays
    flat_config = _flatten_dict(base_config)
    
    # 2. Extract keys and their corresponding value domains
    keys = list(flat_config.keys())
    value_domains = list(flat_config.values())
    
    permutations = []
    
    # 3. Compute Cartesian Product across all value domains
    for combination in itertools.product(*value_domains):
        # Bind the generated combination back to the flattened keys
        flat_permutation = dict(zip(keys, combination))
        
        # 4. Reconstruct the original nested architecture
        nested_permutation = _unflatten_dict(flat_permutation)
        permutations.append(nested_permutation)
        
    return permutations