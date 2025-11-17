"""Data parsing module for benchmark analysis tool."""

import json
import pandas as pd
import os
from glob import glob
from typing import Dict, Any, List, Optional, Callable, Tuple


def extract_dataset_settings(request_loader: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract dataset settings from request_loader or config.requests data.
    
    Args:
        request_loader: Request loader configuration from JSON (v0.3.0) or config.requests (v0.4.0)
        
    Returns:
        Dictionary containing dataset settings
    """
    if request_loader is None:
        return {
            'prompt_tokens': 400,
            'prompt_tokens_stdev': 0,
            'output_tokens': 200,
            'output_tokens_stdev': 0,
            'processor': "multiturn"
        }

    data_str = request_loader.get('data', '')
    if not data_str:
        return {}
    
    # Try v0.4.0 format first: "['prompt_tokens=512,output_tokens=256']"
    if isinstance(data_str, str) and data_str.startswith("['") and data_str.endswith("']"):
        try:
            # Parse the string representation of a list
            import ast
            data_list = ast.literal_eval(data_str)
            if isinstance(data_list, list) and data_list:
                # Parse the first item which is in format "prompt_tokens=512,output_tokens=256"
                settings = {}
                for item in data_list[0].split(','):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        settings[key] = int(value) if value.isdigit() else value
                
                return {
                    'prompt_tokens': settings.get('prompt_tokens', 0),
                    'prompt_tokens_stdev': 0,
                    'output_tokens': settings.get('output_tokens', 0),
                    'output_tokens_stdev': 0,
                    'processor': request_loader.get('processor', '')
                }
        except (ValueError, SyntaxError):
            pass  # Fall through to v0.3.0 format
    
    # Try v0.3.0 format: JSON string
    try:
        # Parse the JSON-like string in the data field
        data_dict = json.loads(data_str)
        return {
            'prompt_tokens': data_dict.get('prompt_tokens', 0),
            'prompt_tokens_stdev': data_dict.get('prompt_tokens_stdev', 0),
            'output_tokens': data_dict.get('output_tokens', 0),
            'output_tokens_stdev': data_dict.get('output_tokens_stdev', 0),
            'processor': request_loader.get('processor', '')
        }
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_benchmark_metrics(filepath: str, extra_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Parse a single JSON file and extract benchmark metrics.

    Args:
        filepath: Path to the JSON file
        extra_metadata: Additional metadata to include in each row

    Returns:
        List of dictionaries containing parsed benchmark metrics
    """
    filename = os.path.basename(filepath)
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []
    
    benchmarks = data.get('benchmarks', [])
    if not benchmarks:
        print(f"No benchmarks found in {filepath}")
        return []
    
    rows = []
    for benchmark in benchmarks:
        # Extract concurrency/RPS from config (v0.4.0+) or args (v0.3.0)
        config = benchmark.get('config', {})
        args = benchmark.get('args', {})
        
        # Try v0.4.0 structure first (config.strategy)
        strategy = config.get('strategy', {})
        if not strategy:
            # Fallback to v0.3.0 structure (args.strategy)
            strategy = args.get('strategy', {})
        
        profile = config.get('profile', {})
        if not profile:
            # Fallback to v0.3.0 structure (args.profile)
            profile = args.get('profile', {})

        # Concurrency mode
        # v0.4.0: config.strategy.max_concurrency
        # v0.3.0: args.strategy.streams
        concurrency = strategy.get('max_concurrency', None)
        if concurrency is None:
            concurrency = strategy.get('streams', None)

        # RPS mode (constant-rate profile)
        rps = None
        # v0.4.0: config.strategy.type_ == 'constant' or similar
        # v0.3.0: args.profile.strategy_type == 'constant'
        strategy_type = strategy.get('type_', profile.get('strategy_type'))
        if strategy_type == 'constant':
            # Prefer strategy.rate, fallback to profile.rate[0]
            rate = strategy.get('rate')
            if rate is None:
                rate_list = profile.get('rate') or []
                if isinstance(rate_list, list) and rate_list:
                    rate = rate_list[0]
            rps = float(rate) if rate is not None else None

        # If neither concurrency nor rps is present, skip
        if concurrency is None and rps is None:
            print(f"Warning: Neither concurrency nor RPS found in {filepath}")
            continue
        
        # Extract dataset settings
        # v0.4.0: config.requests
        # v0.3.0: request_loader
        request_config = config.get('requests', {})
        request_loader = benchmark.get('request_loader', {})
        dataset_settings = extract_dataset_settings(request_config if request_config else request_loader)
        
        # Extract metrics
        metrics = benchmark.get('metrics', {})
        
        # Get output tokens per second
        output_tps_mean = metrics.get('output_tokens_per_second', {}).get('successful', {}).get('mean', 0)
        if output_tps_mean == 0:
            output_tps_mean = metrics.get('output_tokens_per_second', {}).get('total', {}).get('mean', 0)
        
        # Get total tokens per second
        total_tps_mean = metrics.get('tokens_per_second', {}).get('successful', {}).get('mean', 0)
        if total_tps_mean == 0:
            total_tps_mean = metrics.get('tokens_per_second', {}).get('total', {}).get('mean', 0)
        
        # Get latency metrics
        request_latency = metrics.get('request_latency', {}).get('successful', {})
        ttft = metrics.get('time_to_first_token_ms', {}).get('successful', {})
        itl = metrics.get('inter_token_latency_ms', {}).get('successful', {})
        
        # Extract percentiles for box plots
        request_latency_percentiles = request_latency.get('percentiles', {})
        ttft_percentiles = ttft.get('percentiles', {})
        itl_percentiles = itl.get('percentiles', {})
        
        row = {
            'filename': filename,
            'filepath': filepath,
            'concurrency': concurrency,
            'rps': rps,
            'prompt_tokens': dataset_settings.get('prompt_tokens', 0),
            'prompt_tokens_stdev': dataset_settings.get('prompt_tokens_stdev', 0),
            'output_tokens': dataset_settings.get('output_tokens', 0),
            'output_tokens_stdev': dataset_settings.get('output_tokens_stdev', 0),
            'processor': dataset_settings.get('processor', ''),
            'mean_output_tokens_per_second': output_tps_mean,
            'mean_total_tokens_per_second': total_tps_mean,
            # Basic latency stats
            'request_latency_mean': request_latency.get('mean', 0),
            'request_latency_median': request_latency.get('median', 0),
            'ttft_mean': ttft.get('mean', 0),
            'ttft_median': ttft.get('median', 0),
            'itl_mean': itl.get('mean', 0),
            'itl_median': itl.get('median', 0),
            # Request latency percentiles
            'request_latency_p95': request_latency_percentiles.get('p95', 0),
            'request_latency_p99': request_latency_percentiles.get('p99', 0),
            # TTFT percentiles
            'ttft_p95': ttft_percentiles.get('p95', 0),
            'ttft_p99': ttft_percentiles.get('p99', 0),
            # ITL percentiles
            'itl_p95': itl_percentiles.get('p95', 0),
            'itl_p99': itl_percentiles.get('p99', 0),
            # Sequence lengths
            'input_sequence_length': metrics.get('prompt_token_count', {}).get('successful', {}).get('mean', 0),
            'output_sequence_length': metrics.get('output_token_count', {}).get('successful', {}).get('mean', 0),
        }
        
        # Add extra metadata if provided
        if extra_metadata:
            row.update(extra_metadata)
        
        rows.append(row)
    
    return rows


def parse_individual_requests(filepath: str, extra_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Parse individual request data from a JSON file.

    Args:
        filepath: Path to the JSON file
        extra_metadata: Additional metadata to include in each row

    Returns:
        List of dictionaries containing individual request data
    """
    filename = os.path.basename(filepath)
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []
    
    benchmarks = data.get('benchmarks', [])
    if not benchmarks:
        print(f"No benchmarks found in {filepath}")
        return []
    
    all_requests = []
    for benchmark in benchmarks:
        # Extract test start time from run_stats (v0.3.0) or start_time (v0.4.0)
        run_stats = benchmark.get('run_stats', {})
        test_start_time = run_stats.get('start_time', None)
        if test_start_time is None:
            test_start_time = benchmark.get('start_time', None)
        
        # Extract concurrency/RPS from config (v0.4.0+) or args (v0.3.0)
        config = benchmark.get('config', {})
        args = benchmark.get('args', {})
        
        # Try v0.4.0 structure first (config.strategy)
        strategy = config.get('strategy', {})
        if not strategy:
            # Fallback to v0.3.0 structure (args.strategy)
            strategy = args.get('strategy', {})
        
        profile = config.get('profile', {})
        if not profile:
            # Fallback to v0.3.0 structure (args.profile)
            profile = args.get('profile', {})
        
        # Concurrency mode
        # v0.4.0: config.strategy.max_concurrency
        # v0.3.0: args.strategy.streams
        concurrency = strategy.get('max_concurrency', None)
        if concurrency is None:
            concurrency = strategy.get('streams', None)
        
        # RPS mode (constant-rate profile)
        rps = None
        # v0.4.0: config.strategy.type_ == 'constant' or similar
        # v0.3.0: args.profile.strategy_type == 'constant'
        strategy_type = strategy.get('type_', profile.get('strategy_type'))
        if strategy_type == 'constant':
            rate = strategy.get('rate')
            if rate is None:
                rate_list = profile.get('rate') or []
                if isinstance(rate_list, list) and rate_list:
                    rate = rate_list[0]
            rps = float(rate) if rate is not None else None
        
        if concurrency is None and rps is None:
            print(f"Warning: Neither concurrency nor RPS found in {filepath}")
            continue
        
        # Extract dataset settings
        # v0.4.0: config.requests
        # v0.3.0: request_loader
        request_config = config.get('requests', {})
        request_loader = benchmark.get('request_loader', {})
        dataset_settings = extract_dataset_settings(request_config if request_config else request_loader)
        
        # Get successful requests
        requests = benchmark.get('requests', {})
        successful_requests = requests.get('successful', [])
        
        if not successful_requests:
            print(f"No successful requests in {filepath}")
            continue
        
        label = f"c{concurrency}" if concurrency is not None else (f"rps{int(rps)}" if rps is not None else "")
        print(f"Found {len(successful_requests)} successful requests in {filename} ({label})")
        
        # Parse each individual request
        for request in successful_requests:
            # Handle both v0.3.0 and v0.4.0 timestamp field names
            # v0.4.0: request_start_time, request_end_time
            # v0.3.0: start_time, end_time
            start_time = request.get('request_start_time', request.get('start_time', 0))
            end_time = request.get('request_end_time', request.get('end_time', 0))
            
            request_data = {
                'filename': filename,
                'filepath': filepath,
                'concurrency': concurrency,
                'rps': rps,
                'dataset_prompt_tokens': dataset_settings.get('prompt_tokens', 0),
                'dataset_output_tokens': dataset_settings.get('output_tokens', 0),
                'request_id': request.get('request_id', ''),
                'prompt_tokens': request.get('prompt_tokens', 0),
                'output_tokens': request.get('output_tokens', 0),
                'request_latency': request.get('request_latency', 0),
                'time_to_first_token_ms': request.get('time_to_first_token_ms', 0),
                'inter_token_latency_ms': request.get('inter_token_latency_ms', 0),
                'tokens_per_second': request.get('tokens_per_second', 0),
                'output_tokens_per_second': request.get('output_tokens_per_second', 0),
                'first_token_time': request.get('first_token_time', 0),
                'start_time': start_time,
                'end_time': end_time,
            }
            
            # Calculate relative times from test start
            if test_start_time is not None:
                first_token_time = request.get('first_token_time', 0)
                request_start_time = start_time
                request_end_time = end_time
                
                if first_token_time > 0:
                    request_data['first_token_time_relative'] = first_token_time - test_start_time
                else:
                    request_data['first_token_time_relative'] = 0
                    
                if request_start_time > 0:
                    request_data['start_time_relative'] = request_start_time - test_start_time
                else:
                    request_data['start_time_relative'] = 0
                
                if request_end_time > 0:
                    request_data['end_time_relative'] = request_end_time - test_start_time
                else:
                    request_data['end_time_relative'] = 0
            else:
                # Fallback: use 0 if no test start time available
                request_data['first_token_time_relative'] = 0
                request_data['start_time_relative'] = 0
                request_data['end_time_relative'] = 0
            
            # Add extra metadata if provided
            if extra_metadata:
                request_data.update(extra_metadata)
            
            all_requests.append(request_data)
    
    return all_requests


def load_data_from_config(config: Dict[str, Any], parser_func: Callable) -> pd.DataFrame:
    """Load data from multiple file groups specified in config.
    
    Args:
        config: Configuration dictionary
        parser_func: Function to parse individual files (parse_benchmark_metrics or parse_individual_requests)
        
    Returns:
        DataFrame containing all parsed data
    """
    all_data = []
    
    for data_group in config['data']:
        extra_metadata = data_group.get('extra_metadata', {})
        file_patterns = data_group.get('files', [])
        
        # Expand file patterns to actual files
        files = []
        for pattern in file_patterns:
            files.extend(glob(pattern))
        
        print(f"Processing {len(files)} files with metadata: {extra_metadata}")
        
        # Parse each file
        for filepath in files:
            print(f"  Processing: {filepath}")
            rows = parser_func(filepath, extra_metadata)
            all_data.extend(rows)
    
    return pd.DataFrame(all_data)


def create_dataset_identifier(df: pd.DataFrame) -> pd.DataFrame:
    """Create a dataset identifier for grouping similar configurations.
    
    Args:
        df: DataFrame to add dataset identifier to
        
    Returns:
        DataFrame with dataset_id column added
    """
    if 'prompt_tokens' in df.columns:
        df['dataset_id'] = df['prompt_tokens'].astype(str) + '-' + df['output_tokens'].astype(str)
    elif 'dataset_prompt_tokens' in df.columns:
        df['dataset_id'] = df['dataset_prompt_tokens'].astype(str) + '-' + df['dataset_output_tokens'].astype(str)
    return df


def filter_data_by_levels(df: pd.DataFrame, axis_mode: str, levels: Optional[List[float]]) -> pd.DataFrame:
    """Filter data by concurrency or RPS levels.
    
    Args:
        df: DataFrame to filter
        axis_mode: Either 'concurrency' or 'rps'
        levels: List of levels to keep, or None to keep all
        
    Returns:
        Filtered DataFrame
    """
    if levels is None:
        return df
    
    field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    
    if field not in df.columns:
        print(f"Warning: {field} column not found in data")
        return df
    
    filtered_df = df[df[field].isin(levels)]
    
    if filtered_df.empty:
        print(f"Warning: No data remains after filtering by {field} levels: {levels}")
    
    return filtered_df


def get_available_levels(df: pd.DataFrame, axis_mode: str) -> List[float]:
    """Get available concurrency or RPS levels from data.
    
    Args:
        df: DataFrame containing the data
        axis_mode: Either 'concurrency' or 'rps'
        
    Returns:
        Sorted list of available levels
    """
    field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    
    if field not in df.columns:
        return []
    
    levels = df[field].dropna().unique()
    return sorted([float(level) for level in levels])

