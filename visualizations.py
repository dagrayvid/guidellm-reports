"""Visualization module for generating plotly charts."""

import plotly.express as px
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
# MC
from dynaconf import Dynaconf
import os
# End MC

# MC
def create_throughput_vs_resp_time_chart(df: pd.DataFrame, color_col: str, axis_mode: str, latency_stats_type: str) -> str:
    """Create throughput vs concurrency/RPS chart.
    
    Args:
        df: DataFrame containing benchmark metrics
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        latency_stats_type: 'mean', 'median', 'p95', 'p99'
        
    Returns:
        HTML string of the chart
    """
    if df.empty:
        return "<p>No data available for throughput</p>"
    
    x_field = 'mean_output_tokens_per_second'
    x_label = 'Output Tokens per Second' 
    
    # Group by x_field and color_col, take mean if multiple values
    grouped_data = []
    for group in sorted(df[color_col].unique()):
        group_data = df[df[color_col] == group]
        for x_val in sorted(group_data[x_field].dropna().unique()):
            x_data = group_data[group_data[x_field] == x_val]
            req_latency_field = f'request_latency_{latency_stats_type}'
            req_latency_value = x_data[req_latency_field].mean()
            grouped_data.append({
                'x_value': x_val,
                'req_latency': req_latency_value,
                'group': group,
                'concurrency': x_data['concurrency'].iloc[0]
            })
    
    if not grouped_data:
        return "<p>No valid throughput data available</p>"
    
    plot_df = pd.DataFrame(grouped_data)

    plot_df.sort_values(by='concurrency', inplace=True)

    fig = px.scatter(
        plot_df,
        x='x_value',
        y='req_latency',
        color='group',
        title=f'Throughput vs Request Response Time',
        labels={
            'x_value': x_label,
            'req_latency': 'Request latency (sec)',
            'group': color_col.replace('_', ' ').title()
        },
        hover_data=['concurrency']
    )
 
    fig.update_traces(mode='markers+lines')

    fig.update_layout(
        template='plotly_white',
        height=max(500, len(fig.data[0].x) * 20),  # dynamic height
        font_family='monospace',
        margin=dict(l=80, r=40, t=80, b=120, pad=10),
        showlegend=True,
    )

    # Critical for scatter plots with categorical/text x-axis:
    fig.update_xaxes(
        tickangle=-45,
        automargin=True,
        tickfont=dict(size=10),
        categoryorder='total ascending'  # or 'category ascending', 'trace', etc.
    )

    fig.update_yaxes(automargin=True)
    div_id = f"tpvsrt-{latency_stats_type}"
    #div_id="tpvsrt-chart"
    #return fig.to_html(include_plotlyjs='cdn', div_id=div_id)
    return fig.to_html(include_plotlyjs=False, div_id=div_id)
# End MC
def create_throughput_chart(df: pd.DataFrame, color_col: str, axis_mode: str) -> str:
    """Create throughput vs concurrency/RPS chart.
    
    Args:
        df: DataFrame containing benchmark metrics
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        
    Returns:
        HTML string of the chart
    """
    # MC
    settings=Dynaconf(settings_files=[os.getenv('DYNACONF_SETTINGS_MODULE')], environments=False)
    try:
        x_axis_categorical = settings.options.x_axis_categorical
    except Exception:
        x_axis_categorical = False
    # End MC
    if df.empty:
        return "<p>No data available for throughput</p>"
    
    x_field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    x_label = 'Concurrency' if axis_mode == 'concurrency' else 'RPS'
    
    # Group by x_field and color_col, take mean if multiple values
    grouped_data = []
    for group in sorted(df[color_col].unique()):
        group_data = df[df[color_col] == group]
        for x_val in sorted(group_data[x_field].dropna().unique()):
            x_data = group_data[group_data[x_field] == x_val]
            mean_throughput = x_data['mean_output_tokens_per_second'].mean()
            grouped_data.append({
                'x_value': x_val,
                'throughput': mean_throughput,
                'group': group,
                'samples': len(x_data)
            })
    
    if not grouped_data:
        return "<p>No valid throughput data available</p>"
    
    plot_df = pd.DataFrame(grouped_data)
    plot_df.sort_values(by='x_value', inplace=True)  # sort by actual numeric value
    ## Original
    if not x_axis_categorical:
#        fig = px.bar(
        fig = px.line(
            plot_df,
            x='x_value',
            y='throughput',
            color='group',
            title=f'Throughput vs {x_label}',
            labels={
                'x_value': x_label,
                'throughput': 'Output Tokens/sec',
                'group': color_col.replace('_', ' ').title()
            },
            hover_data=['samples'],
            markers=True
        )
        
        fig.update_layout(
            template='plotly_white',
            height=500,
            font_family='monospace',
            barmode='group'
        )    
    else:
#        fig = px.bar(
        fig = px.line(
            plot_df,
            x='x_value',               # ← keep as numeric/int/float
            y='throughput',
            color='group',
            title=f'Throughput vs {x_label}',
            labels={
                'x_value': x_label,
                'throughput': 'Output Tokens/sec',
                'group': color_col.replace('_', ' ').title()
            },
            markers=True,
            hover_data=['samples'],     # This is the magic line:
            category_orders={'x_value': sorted(plot_df['x_value'].unique())}
            
        )
        fig.update_xaxes(type='category')  # Force treat x-axis as categorical/text
        fig.update_layout(
            template='plotly_white',
            height=500,
            font_family='monospace',
            barmode='group',
            xaxis_title=x_label,
            yaxis_title='Output Tokens/sec'
        )

        # Force the x-axis to show the values in the correct numeric order
        fig.update_xaxes(
            tickmode='array',
            tickvals=plot_df['x_value'],                    # positions (numeric)
            ticktext=plot_df['x_value'].astype(str)         # what is displayed
        )
    # End MC

    
    #return fig.to_html(include_plotlyjs='cdn', div_id="throughput-chart")
    return fig.to_html(include_plotlyjs=False, div_id=f"throughput-{axis_mode}-chart")  


def create_latency_chart(df: pd.DataFrame, metric_col: str, color_col: str, axis_mode: str, 
                        title: str, y_label: str) -> str:
    """Create a latency metric chart.
    
    Args:
        df: DataFrame containing benchmark metrics
        metric_col: Column containing the metric to plot
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        title: Chart title
        y_label: Y-axis label
        
    Returns:
        HTML string of the chart
    """
    # MC
    settings=Dynaconf(settings_files=[os.getenv('DYNACONF_SETTINGS_MODULE')], environments=False)
    try:
        y_axis_log_scale = settings.options.y_axis_log_scale
    except Exception:
        y_axis_log_scale = False
    try:
        x_axis_categorical = settings.options.x_axis_categorical
    except Exception:
        x_axis_categorical = False        
    # End MC
    if df.empty or metric_col not in df.columns:
        return f"<p>No data available for {title}</p>"
    
    x_field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    x_label = 'Concurrency' if axis_mode == 'concurrency' else 'RPS'
    
    # Group by x_field and color_col, take mean if multiple values
    grouped_data = []
    for group in sorted(df[color_col].unique()):
        group_data = df[df[color_col] == group]
        for x_val in sorted(group_data[x_field].dropna().unique()):
            x_data = group_data[group_data[x_field] == x_val]
            mean_value = x_data[metric_col].mean()
            grouped_data.append({
                'x_value': x_val,
                'metric_value': mean_value,
                'group': group,
                'samples': len(x_data)
            })
    
    if not grouped_data:
        return f"<p>No valid data available for {title}</p>"
    
    plot_df = pd.DataFrame(grouped_data)
    if not x_axis_categorical:
        fig = px.bar(
            plot_df,
            x='x_value',
            y='metric_value',
            color='group',
            title=f'{title} vs {x_label}',
            labels={
                'x_value': x_label,
                'metric_value': y_label,
                'group': color_col.replace('_', ' ').title()
            },
            hover_data=['samples']
        )

        fig.update_layout(
            template='plotly_white',
            height=500,
            font_family='monospace',
            barmode='group'
        )
    else:
        fig = px.line(
            plot_df,
            x='x_value',               # ← keep as numeric/int/float
            y='metric_value',
            color='group',
            title=f'{title} vs {x_label}',
            labels={
                'x_value': x_label,
                'metric_value': y_label,
                'group': color_col.replace('_', ' ').title()
            },
            markers=True,
            hover_data=['samples'],     # This is the magic line:
            category_orders={'x_value': sorted(plot_df['x_value'].unique())}
            
        )
        fig.update_xaxes(type='category')  # Force treat x-axis as categorical/text
        fig.update_layout(
            template='plotly_white',
            height=500,
            font_family='monospace',
            barmode='group',
            xaxis_title=x_label,
            yaxis_title=y_label
        )

        # Force the x-axis to show the values in the correct numeric order
        fig.update_xaxes(
            tickmode='array',
            tickvals=plot_df['x_value'],                    # positions (numeric)
            ticktext=plot_df['x_value'].astype(str)         # what is displayed
        )
    # 
    # MC
    # Set y-axis to log scale if configured
    if y_axis_log_scale:
        fig.update_yaxes(type='log')
    # End MC
    chart_id = metric_col.replace('_', '-') + '-chart'
    #return fig.to_html(include_plotlyjs='cdn', div_id=chart_id)
    return fig.to_html(include_plotlyjs=False, div_id=chart_id)

def create_histogram_deep_dive(df: pd.DataFrame, metric_col: str, color_col: str, 
                               axis_mode: str, title_prefix: str) -> str:
    """Create separate histograms for deep dive analysis of per-request data.
    
    Args:
        df: DataFrame containing individual request data
        metric_col: Column containing the metric to plot (e.g., 'time_to_first_token_ms')
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        title_prefix: Prefix for the chart title (e.g., 'TTFT', 'ITL')
        
    Returns:
        HTML string containing separate histograms for each benchmark result
    """
    if df.empty or metric_col not in df.columns:
        return f"<p>No data available for {title_prefix} deep dive</p>"
    
    level_field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    level_label = 'Concurrency' if axis_mode == 'concurrency' else 'RPS'
    
    # Get unique combinations of level and group (each represents a unique benchmark result)
    benchmark_combinations = []
    for level in sorted(df[level_field].dropna().unique()):
        for group in sorted(df[color_col].unique()):
            combination_data = df[(df[level_field] == level) & (df[color_col] == group)]
            if not combination_data.empty and combination_data[metric_col].dropna().any():
                benchmark_combinations.append((level, group, combination_data))
    
    if not benchmark_combinations:
        return f"<p>No valid data for {title_prefix} histograms</p>"
    
    html_parts = []
    
    # Create one histogram for each unique benchmark result
    for level, group, data in benchmark_combinations:
        metric_values = data[metric_col].dropna()
        
        if len(metric_values) == 0:
            continue
        
        # Determine bin size based on metric type
        if 'ttft' in metric_col.lower() or title_prefix.upper() == 'TTFT':
            bin_size = 100  # 100ms for TTFT
        elif 'itl' in metric_col.lower() or 'inter_token' in metric_col.lower() or title_prefix.upper() == 'ITL':
            bin_size = 2    # 2ms for ITL
        else:
            bin_size = 10   # Default 10ms for other latency metrics
        
        # Calculate number of bins based on data range and desired bin size
        min_val = metric_values.min()
        max_val = metric_values.max()
        data_range = max_val - min_val
        calculated_nbins = max(10, int(data_range / bin_size) + 1)  # Minimum 10 bins
        
        # Create histogram using plotly express
        hist_df = pd.DataFrame({
            metric_col: metric_values
        })
        
        fig = px.histogram(
            hist_df,
            x=metric_col,
            nbins=calculated_nbins,
            title=f'{title_prefix} Distribution - {level_label}={level}, {color_col.replace("_", " ").title()}={group}',
            labels={
                metric_col: f'{title_prefix} (ms)'
            }
        )
        
        fig.update_layout(
            template='plotly_white',
            height=400,
            font_family='monospace',
            showlegend=False,
            yaxis_title='Count'
        )
        
        # Add sample count and bin size in subtitle
        sample_count = len(metric_values)
        fig.add_annotation(
            text=f"Samples: {sample_count} | Bin size: {bin_size}ms",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, family="monospace"),
            bgcolor="rgba(255,255,255,0.8)"
        )
        
        chart_id = f"{title_prefix.lower()}-{str(level).replace('.', '_')}-{str(group).replace(' ', '-')}"
        #chart_html = fig.to_html(include_plotlyjs='cdn', div_id=chart_id)
        chart_html = fig.to_html(include_plotlyjs=False, div_id=chart_id)
        html_parts.append(f'<div style="margin-bottom: 30px;">{chart_html}</div>')
    
    return '\n'.join(html_parts)


def create_token_length_histograms(df: pd.DataFrame, token_col: str, color_col: str, 
                                   axis_mode: str, title_prefix: str) -> str:
    """Create histograms for token length distributions from per-request data.
    
    Args:
        df: DataFrame containing individual request data
        token_col: Column containing token counts ('prompt_tokens' or 'output_tokens')
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        title_prefix: Prefix for the chart title (e.g., 'Input Length', 'Output Length')
        
    Returns:
        HTML string containing separate histograms for each benchmark result
    """
    if df.empty or token_col not in df.columns:
        return f"<p>No data available for {title_prefix} distribution</p>"
    
    level_field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    level_label = 'Concurrency' if axis_mode == 'concurrency' else 'RPS'
    
    # Get unique combinations of level and group (each represents a unique benchmark result)
    benchmark_combinations = []
    for level in sorted(df[level_field].dropna().unique()):
        for group in sorted(df[color_col].unique()):
            combination_data = df[(df[level_field] == level) & (df[color_col] == group)]
            if not combination_data.empty and combination_data[token_col].dropna().any():
                benchmark_combinations.append((level, group, combination_data))
    
    if not benchmark_combinations:
        return f"<p>No valid data for {title_prefix} histograms</p>"
    
    html_parts = []
    
    # Create one histogram for each unique benchmark result
    for level, group, data in benchmark_combinations:
        token_values = data[token_col].dropna()
        
        if len(token_values) == 0:
            continue
        
        # Use smaller bin size for token counts (tokens are typically integers)
        bin_size = 50  # 50 tokens per bin
        
        # Calculate number of bins based on data range and desired bin size
        min_val = token_values.min()
        max_val = token_values.max()
        data_range = max_val - min_val
        calculated_nbins = max(10, int(data_range / bin_size) + 1)  # Minimum 10 bins
        
        # Create histogram using plotly express
        hist_df = pd.DataFrame({
            token_col: token_values
        })
        
        fig = px.histogram(
            hist_df,
            x=token_col,
            nbins=calculated_nbins,
            title=f'{title_prefix} Distribution - {level_label}={level}, {color_col.replace("_", " ").title()}={group}',
            labels={
                token_col: f'{title_prefix} (tokens)'
            }
        )
        
        fig.update_layout(
            template='plotly_white',
            height=400,
            font_family='monospace',
            showlegend=False,
            yaxis_title='Count'
        )
        
        # Add sample count and bin size in subtitle
        sample_count = len(token_values)
        mean_tokens = token_values.mean()
        fig.add_annotation(
            text=f"Samples: {sample_count} | Bin size: {bin_size} tokens | Mean: {mean_tokens:.1f}",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, family="monospace"),
            bgcolor="rgba(255,255,255,0.8)"
        )
        
        chart_id = f"{title_prefix.lower().replace(' ', '-')}-{str(level).replace('.', '_')}-{str(group).replace(' ', '-')}"
        #chart_html = fig.to_html(include_plotlyjs='cdn', div_id=chart_id)
        chart_html = fig.to_html(include_plotlyjs=False, div_id=chart_id)
        html_parts.append(f'<div style="margin-bottom: 30px;">{chart_html}</div>')
    
    return '\n'.join(html_parts)


def create_request_scheduling_charts(df: pd.DataFrame, color_col: str, axis_mode: str) -> str:
    """Create request scheduling analysis charts.
    
    Args:
        df: DataFrame containing individual request data
        color_col: Column to use for coloring/grouping
        axis_mode: Either 'concurrency' or 'rps'
        
    Returns:
        HTML string containing the scheduling analysis charts
    """
    if df.empty:
        return "<p>No data available for request scheduling analysis</p>"
    
    level_field = 'concurrency' if axis_mode == 'concurrency' else 'rps'
    level_label = 'Concurrency' if axis_mode == 'concurrency' else 'RPS'
    
    html_parts = []
    
    # Chart 1: Request start rate over time
    start_rate_html = create_request_rate_chart(
        df, 'start_time_relative', 'Requests Started per Second', 
        color_col, level_field, level_label
    )
    html_parts.append(f'<div style="margin-bottom: 30px;">{start_rate_html}</div>')
    
    # Chart 2: Request completion rate over time
    end_rate_html = create_request_rate_chart(
        df, 'end_time_relative', 'Requests Completed per Second',
        color_col, level_field, level_label
    )
    html_parts.append(f'<div style="margin-bottom: 30px;">{end_rate_html}</div>')
    
    # Chart 3: TTFT Timeline
    timeline_html = create_ttft_timeline_chart(df, color_col, level_field, level_label)
    html_parts.append(f'<div style="margin-bottom: 30px;">{timeline_html}</div>')
    
    return '\n'.join(html_parts)


def create_request_rate_chart(df: pd.DataFrame, time_col: str, title: str, 
                             color_col: str, level_field: str, level_label: str) -> str:
    """Create request rate charts (sliding window) stacked vertically by level.
    
    Args:
        df: DataFrame with request data
        time_col: Column containing relative time values
        title: Chart title
        color_col: Column for grouping/coloring
        level_field: Field containing concurrency/RPS levels
        level_label: Label for the level field
        
    Returns:
        HTML string of the charts stacked vertically
    """
    if time_col not in df.columns:
        return f"<p>No {time_col} data available</p>"
    
    # Filter out invalid times
    valid_data = df[pd.notna(df[time_col]) & (df[time_col] >= 0)]
    
    if valid_data.empty:
        return f"<p>No valid time data for {title}</p>"
    
    # Get unique levels
    levels = sorted(valid_data[level_field].dropna().unique())
    
    if not levels:
        return f"<p>No level data available for {title}</p>"
    
    html_parts = []
    
    # Create separate chart for each level
    for level in levels:
        level_data = valid_data[valid_data[level_field] == level]
        
        if level_data.empty:
            continue
        
        # Calculate sliding window rates for this level
        rate_data = []
        for group in sorted(level_data[color_col].unique()):
            group_data = level_data[level_data[color_col] == group]
            
            if group_data.empty:
                continue
            
            # Round times to integer seconds for counting
            times = group_data[time_col].apply(lambda x: int(x) if x >= 0 else 0)
            time_counts = times.value_counts().sort_index()
            
            for time_sec, count in time_counts.items():
                rate_data.append({
                    'time_sec': time_sec,
                    'rate': count,
                    'group': group
                })
        
        if not rate_data:
            continue
        
        rate_df = pd.DataFrame(rate_data)
        
        fig = px.scatter(
            rate_df,
            x='time_sec',
            y='rate',
            color='group',
            title=f'{title} - {level_label}={level}',
            labels={
                'time_sec': 'Time from Test Start (seconds)',
                'rate': 'Requests per Second',
                'group': color_col.replace('_', ' ').title()
            }
        )
        
        fig.update_layout(
            template='plotly_white',
            height=350,
            font_family='monospace'
        )
        
        chart_id = f"{title.lower().replace(' ', '-').replace('/', '-')}-{str(level).replace('.', '_')}"
        #chart_html = fig.to_html(include_plotlyjs='cdn', div_id=chart_id)
        chart_html = fig.to_html(include_plotlyjs=False, div_id=chart_id)
        html_parts.append(f'<div style="margin-bottom: 30px;">{chart_html}</div>')
    
    if not html_parts:
        return f"<p>No rate data computed for {title}</p>"
    
    return '\n'.join(html_parts)


def create_ttft_timeline_chart(df: pd.DataFrame, color_col: str, level_field: str, level_label: str) -> str:
    """Create TTFT timeline scatter plots stacked vertically by level.
    
    Args:
        df: DataFrame with request data
        color_col: Column for grouping/coloring
        level_field: Field containing concurrency/RPS levels
        level_label: Label for the level field
        
    Returns:
        HTML string of the charts stacked vertically
    """
    required_cols = ['first_token_time_relative', 'time_to_first_token_ms']
    
    if not all(col in df.columns for col in required_cols):
        return "<p>Required columns missing for TTFT timeline</p>"
    
    # Filter valid data
    valid_data = df[
        pd.notna(df['first_token_time_relative']) & 
        pd.notna(df['time_to_first_token_ms']) &
        (df['first_token_time_relative'] >= 0)
    ]
    
    if valid_data.empty:
        return "<p>No valid TTFT timeline data</p>"
    
    levels = sorted(valid_data[level_field].dropna().unique())
    
    if not levels:
        return "<p>No level data for TTFT timeline</p>"
    
    html_parts = []
    
    # Create separate chart for each level
    for level in levels:
        level_data = valid_data[valid_data[level_field] == level]
        
        if level_data.empty:
            continue
        
        fig = px.scatter(
            level_data,
            x='first_token_time_relative',
            y='time_to_first_token_ms',
            color=color_col,
            title=f'TTFT Timeline Analysis - {level_label}={level}',
            labels={
                'first_token_time_relative': 'First Token Time (seconds from test start)',
                'time_to_first_token_ms': 'TTFT (ms)',
                color_col: color_col.replace('_', ' ').title()
            }
        )
        
        fig.update_layout(
            template='plotly_white',
            height=350,
            font_family='monospace'
        )
        
        chart_id = f"ttft-timeline-{str(level).replace('.', '_')}"
        #chart_html = fig.to_html(include_plotlyjs='cdn', div_id=chart_id)
        chart_html = fig.to_html(include_plotlyjs=False, div_id=chart_id)   
        html_parts.append(f'<div style="margin-bottom: 30px;">{chart_html}</div>')
    
    if not html_parts:
        return "<p>No valid TTFT timeline data</p>"
    
    return '\n'.join(html_parts)

