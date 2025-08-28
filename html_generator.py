"""HTML report generation module."""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import yaml
from typing import Dict, Any, Optional

try:
    from . import visualizations
except ImportError:
    import visualizations


def generate_metadata_text(summary_df: pd.DataFrame, requests_df: pd.DataFrame, 
                          config_file: Optional[str], color_col: str, axis_mode: str,
                          command_line: Optional[str] = None) -> str:
    """Generate metadata text for the report.
    
    Args:
        summary_df: DataFrame containing summary metrics
        requests_df: DataFrame containing individual request data
        config_file: Path to configuration file
        color_col: Column used for grouping/coloring
        axis_mode: Either 'concurrency' or 'rps'
        
    Returns:
        Formatted metadata string
    """
    generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    metadata_lines = [f"Generated: {generation_time}"]
    
    # Add command line used to generate the report
    if command_line:
        metadata_lines.append(f"Command: {command_line}")
    
    metadata_lines.append("")
    
    # Add basic stats
    if not summary_df.empty:
        metadata_lines.append(f"Summary data points: {len(summary_df)}")
    if not requests_df.empty:
        metadata_lines.append(f"Individual requests: {len(requests_df)}")
    
    metadata_lines.append("")
    
    # Include the actual parsed YAML config for reproducibility (without comments)
    if config_file and os.path.exists(config_file):
        metadata_lines.append("Configuration used:")
        metadata_lines.append("=" * 50)
        try:
            with open(config_file, 'r') as f:
                parsed_config = yaml.safe_load(f)
            # Pretty print the parsed config without comments
            clean_yaml = yaml.dump(parsed_config, default_flow_style=False, sort_keys=False)
            metadata_lines.append(clean_yaml.strip())
        except Exception as e:
            metadata_lines.append(f"Error parsing config file: {e}")
    else:
        metadata_lines.append(f"Configuration file: {config_file or 'N/A'}")
    
    return '\n'.join(metadata_lines)


def generate_all_charts(summary_df: pd.DataFrame, requests_df: pd.DataFrame, 
                       color_col: str, axis_mode: str) -> Dict[str, str]:
    """Generate all charts for the report.
    
    Args:
        summary_df: DataFrame containing summary metrics
        requests_df: DataFrame containing individual request data
        color_col: Column used for grouping/coloring
        axis_mode: Either 'concurrency' or 'rps'
        
    Returns:
        Dictionary mapping chart names to HTML strings
    """
    charts = {}
    
    # Throughput chart
    if not summary_df.empty:
        charts['throughput_chart'] = visualizations.create_throughput_chart(
            summary_df, color_col, axis_mode
        )
    else:
        charts['throughput_chart'] = "<p>No summary data available for throughput analysis</p>"
    
    # TTFT charts (all subtabs)
    ttft_metrics = [
        ('ttft_mean', 'TTFT Mean', 'ms'),
        ('ttft_median', 'TTFT Median', 'ms'),
        ('ttft_p95', 'TTFT P95', 'ms'),
        ('ttft_p99', 'TTFT P99', 'ms')
    ]
    
    for metric_col, title, y_label in ttft_metrics:
        chart_key = f"{metric_col}_chart"
        if not summary_df.empty:
            charts[chart_key] = visualizations.create_latency_chart(
                summary_df, metric_col, color_col, axis_mode, title, y_label
            )
        else:
            charts[chart_key] = f"<p>No summary data available for {title}</p>"
    
    # ITL charts (all subtabs)
    itl_metrics = [
        ('itl_mean', 'ITL Mean', 'ms'),
        ('itl_median', 'ITL Median', 'ms'),
        ('itl_p95', 'ITL P95', 'ms'),
        ('itl_p99', 'ITL P99', 'ms')
    ]
    
    for metric_col, title, y_label in itl_metrics:
        chart_key = f"{metric_col}_chart"
        if not summary_df.empty:
            charts[chart_key] = visualizations.create_latency_chart(
                summary_df, metric_col, color_col, axis_mode, title, y_label
            )
        else:
            charts[chart_key] = f"<p>No summary data available for {title}</p>"
    
    # Request Latency charts (all subtabs)
    request_latency_metrics = [
        ('request_latency_mean', 'Request Latency Mean', 'ms'),
        ('request_latency_median', 'Request Latency Median', 'ms'),
        ('request_latency_p95', 'Request Latency P95', 'ms'),
        ('request_latency_p99', 'Request Latency P99', 'ms')
    ]
    
    for metric_col, title, y_label in request_latency_metrics:
        chart_key = f"{metric_col}_chart"
        if not summary_df.empty:
            charts[chart_key] = visualizations.create_latency_chart(
                summary_df, metric_col, color_col, axis_mode, title, y_label
            )
        else:
            charts[chart_key] = f"<p>No summary data available for {title}</p>"
    
    # Input and output length charts (using per-request data for distributions)
    if not requests_df.empty:
        charts['input_length_chart'] = visualizations.create_token_length_histograms(
            requests_df, 'prompt_tokens', color_col, axis_mode, 'Input Length'
        )
        charts['output_length_chart'] = visualizations.create_token_length_histograms(
            requests_df, 'output_tokens', color_col, axis_mode, 'Output Length'
        )
    else:
        charts['input_length_chart'] = "<p>No individual request data available for Input Length distribution</p>"
        charts['output_length_chart'] = "<p>No individual request data available for Output Length distribution</p>"
    
    # Deep dive charts (require individual request data)
    if not requests_df.empty:
        charts['ttft_deep_dive_chart'] = visualizations.create_histogram_deep_dive(
            requests_df, 'time_to_first_token_ms', color_col, axis_mode, 'TTFT'
        )
        charts['itl_deep_dive_chart'] = visualizations.create_histogram_deep_dive(
            requests_df, 'inter_token_latency_ms', color_col, axis_mode, 'ITL'
        )
        charts['scheduling_chart'] = visualizations.create_request_scheduling_charts(
            requests_df, color_col, axis_mode
        )
    else:
        charts['ttft_deep_dive_chart'] = "<p>No individual request data available for TTFT deep dive</p>"
        charts['itl_deep_dive_chart'] = "<p>No individual request data available for ITL deep dive</p>"
        charts['scheduling_chart'] = "<p>No individual request data available for scheduling analysis</p>"
    
    return charts


def generate_html_report(summary_df: pd.DataFrame, requests_df: pd.DataFrame,
                        output_path: str, config_file: Optional[str] = None,
                        title: Optional[str] = None, subtitle: Optional[str] = None,
                        color_col: str = 'dataset_id', axis_mode: str = 'concurrency',
                        command_line: Optional[str] = None) -> None:
    """Generate the HTML report.
    
    Args:
        summary_df: DataFrame containing summary metrics
        requests_df: DataFrame containing individual request data
        output_path: Path where to save the HTML report
        config_file: Path to configuration file (for metadata)
        title: Optional title for the report
        subtitle: Optional subtitle for the report
        color_col: Column to use for grouping/coloring
        axis_mode: Either 'concurrency' or 'rps'
    """
    print("Generating charts...")
    
    # Generate all charts
    charts = generate_all_charts(summary_df, requests_df, color_col, axis_mode)
    
    # Generate metadata
    metadata = generate_metadata_text(summary_df, requests_df, config_file, color_col, axis_mode, command_line)
    
    # Load template
    template_dir = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('template.html')
    
    # Render HTML
    html_title = title or "Benchmark Analysis Report"
    html_content = template.render(
        html_title=html_title,
        title=title,
        subtitle=subtitle,
        metadata=metadata,
        **charts
    )
    
    # Write to file
    print(f"Writing report to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_path}")
