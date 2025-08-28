"""Configuration handling module for benchmark analysis tool."""

import yaml
import os
from typing import Dict, Any, List, Optional


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the configuration data
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the config file is invalid YAML
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate required fields
    if 'data' not in config:
        raise ValueError("Configuration must contain 'data' section")
    
    return config


def get_axis_mode(config: Dict[str, Any]) -> str:
    """Get the axis mode from configuration (concurrency or rps).
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Either 'concurrency' or 'rps'
    """
    options = config.get('options', {})
    axis_mode = options.get('axis_mode', 'concurrency')
    
    if axis_mode not in ('concurrency', 'rps'):
        axis_mode = 'concurrency'
    
    return axis_mode


def get_color_column(config: Dict[str, Any]) -> str:
    """Get the color column from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Name of the column to use for coloring/grouping
    """
    options = config.get('options', {})
    return options.get('color', 'dataset_id')


def get_concurrency_levels(config: Dict[str, Any]) -> Optional[List[float]]:
    """Get configured concurrency levels if specified.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of concurrency levels or None if not specified
    """
    options = config.get('options', {})
    levels = options.get('concurrency_levels')
    
    if levels:
        try:
            return [float(level) for level in levels]
        except (ValueError, TypeError):
            return None
    
    return None


def get_rps_levels(config: Dict[str, Any]) -> Optional[List[float]]:
    """Get configured RPS levels if specified.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of RPS levels or None if not specified
    """
    options = config.get('options', {})
    levels = options.get('rps_levels')
    
    if levels:
        try:
            return [float(level) for level in levels]
        except (ValueError, TypeError):
            return None
    
    return None


def get_data_groups(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get data groups from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of data group configurations
    """
    return config.get('data', [])

