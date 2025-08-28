#!/usr/bin/env python3
"""
Main entry point for GuideLLM Reports.

This tool combines summary metrics analysis and per-request deep dives
into an HTML report with multiple tabs and visualizations.
"""

import argparse
import sys
import os
from typing import Optional

try:
    from . import config
    from . import data_parsers
    from . import html_generator
except ImportError:
    # Support running directly as a script
    import config
    import data_parsers
    import html_generator


def main() -> None:
    """Main entry point for GuideLLM Reports."""
    parser = argparse.ArgumentParser(
        description='Benchmark analysis and visualization tool for GuideLLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate-report.py config.yaml --output report.html
  python generate-report.py config.yaml --title "Performance Analysis" --subtitle "H100 vs A100"
        """
    )
    
    parser.add_argument(
        'config', 
        help='YAML configuration file specifying data sources and options'
    )
    parser.add_argument(
        '--output', 
        default='benchmark_analysis_report.html',
        help='Output HTML file path (default: benchmark_analysis_report.html)'
    )
    parser.add_argument(
        '--title', 
        help='Report title (optional)'
    )
    parser.add_argument(
        '--subtitle', 
        help='Report subtitle (optional)'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Generate report using only summary metrics (no deep dive analysis)'
    )
    parser.add_argument(
        '--requests-only',
        action='store_true', 
        help='Generate report using only individual request data (no summary metrics)'
    )
    
    args = parser.parse_args()
    
    # Check for conflicting options
    if args.summary_only and args.requests_only:
        print("Error: --summary-only and --requests-only are mutually exclusive")
        sys.exit(1)
    
    try:
        # Load configuration
        print(f"Loading configuration from {args.config}...")
        cfg = config.load_config(args.config)
        
        # Get configuration options
        axis_mode = config.get_axis_mode(cfg)
        color_col = config.get_color_column(cfg)
        
        print(f"Axis mode: {axis_mode}")
        print(f"Color/grouping column: {color_col}")
        
        # Load data based on options
        summary_df = None
        requests_df = None
        
        if not args.requests_only:
            print("\nLoading summary metrics data...")
            try:
                summary_df = data_parsers.load_data_from_config(cfg, data_parsers.parse_benchmark_metrics)
                
                if not summary_df.empty:
                    # Create dataset identifier and filter data
                    summary_df = data_parsers.create_dataset_identifier(summary_df)
                    
                    # Apply level filtering if configured
                    if axis_mode == 'concurrency':
                        levels = config.get_concurrency_levels(cfg)
                        summary_df = data_parsers.filter_data_by_levels(summary_df, axis_mode, levels)
                    else:
                        levels = config.get_rps_levels(cfg)
                        summary_df = data_parsers.filter_data_by_levels(summary_df, axis_mode, levels)
                    
                    print(f"Loaded {len(summary_df)} summary data points")
                    if color_col in summary_df.columns:
                        groups = sorted(summary_df[color_col].unique())
                        print(f"Groups: {groups}")
                    else:
                        print(f"Warning: Color column '{color_col}' not found in summary data")
                        # Fall back to dataset_id if available
                        if 'dataset_id' in summary_df.columns:
                            color_col = 'dataset_id'
                            print(f"Using 'dataset_id' as color column instead")
                else:
                    print("No summary data found")
            except Exception as e:
                print(f"Error loading summary data: {e}")
                if args.summary_only:
                    sys.exit(1)
        
        if not args.summary_only:
            print("\nLoading individual request data...")
            try:
                requests_df = data_parsers.load_data_from_config(cfg, data_parsers.parse_individual_requests)
                
                if not requests_df.empty:
                    # Create dataset identifier and filter data
                    requests_df = data_parsers.create_dataset_identifier(requests_df)
                    
                    # Apply level filtering if configured
                    if axis_mode == 'concurrency':
                        levels = config.get_concurrency_levels(cfg)
                        requests_df = data_parsers.filter_data_by_levels(requests_df, axis_mode, levels)
                    else:
                        levels = config.get_rps_levels(cfg)
                        requests_df = data_parsers.filter_data_by_levels(requests_df, axis_mode, levels)
                    
                    print(f"Loaded {len(requests_df)} individual requests")
                    
                    # Use color column from requests data if summary data wasn't loaded
                    if summary_df is None or summary_df.empty:
                        if color_col in requests_df.columns:
                            groups = sorted(requests_df[color_col].unique())
                            print(f"Groups: {groups}")
                        else:
                            print(f"Warning: Color column '{color_col}' not found in request data")
                            if 'dataset_id' in requests_df.columns:
                                color_col = 'dataset_id'
                                print(f"Using 'dataset_id' as color column instead")
                else:
                    print("No individual request data found")
            except Exception as e:
                print(f"Error loading request data: {e}")
                if args.requests_only:
                    sys.exit(1)
        
        # Check that we have at least some data
        if (summary_df is None or summary_df.empty) and (requests_df is None or requests_df.empty):
            print("Error: No data loaded from any source")
            sys.exit(1)
        
        # Ensure we have empty DataFrames instead of None for the generator
        if summary_df is None:
            import pandas as pd
            summary_df = pd.DataFrame()
        if requests_df is None:
            import pandas as pd
            requests_df = pd.DataFrame()
        
        # Generate the HTML report
        print(f"\nGenerating HTML report...")
        
        # Reconstruct the command line for metadata
        cmd_parts = ['python', 'generate-report.py', args.config]
        if args.output != 'benchmark_analysis_report.html':
            cmd_parts.extend(['--output', args.output])
        if args.title:
            cmd_parts.extend(['--title', f'"{args.title}"'])
        if args.subtitle:
            cmd_parts.extend(['--subtitle', f'"{args.subtitle}"'])
        if args.summary_only:
            cmd_parts.append('--summary-only')
        if args.requests_only:
            cmd_parts.append('--requests-only')
        command_line = ' '.join(cmd_parts)
        
        html_generator.generate_html_report(
            summary_df=summary_df,
            requests_df=requests_df,
            output_path=args.output,
            config_file=args.config,
            title=args.title,
            subtitle=args.subtitle,
            color_col=color_col,
            axis_mode=axis_mode,
            command_line=command_line
        )
        
        print(f"\nReport generation complete!")
        print(f"Open {args.output} in your browser to view the analysis.")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
