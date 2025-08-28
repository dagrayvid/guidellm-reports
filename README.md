# GuideLLM Reports

> **Note**: This tool was created with an AI code generation tool (Cursor), and has not yet been thoroughly vetted by a human. Use at your own risk.

A tool for analyzing and visualizing benchmark results from GuideLLM tests. This tool combines summary metrics analysis and per-request deep dives into a single HTML report with multiple tabs and interactive visualizations.

## Features

- **Summary Metrics Analysis**: Throughput, TTFT, ITL, and request latency statistics (mean, median, p95, p99)
- **Deep Dive Analysis**: Distribution histograms for TTFT and ITL across all individual requests
- **Request Scheduling Analysis**: Timeline visualization and request rate analysis
- **Flexible Configuration**: Support for both concurrency and RPS-based analysis
- **Interactive HTML Reports**: Tabbed interface with minimal monospace styling
- **Modular Architecture**: Clean separation between data parsing, visualization, and report generation

## Usage

### Basic Usage

```bash
cd guidellm-reports
python generate-report.py config.yaml --output report.html
```

### With Custom Title and Subtitle

```bash
python generate-report.py config.yaml \
    --title "H100 Performance Analysis" \
    --subtitle "Comparing RHOAI vs llm-d platforms" \
    --output performance_report.html
```

### Summary Only (faster, no deep dive)

```bash
python generate-report.py config.yaml --summary-only --output summary_report.html
```

### Requests Only (deep dive analysis without summary charts)

```bash
python generate-report.py config.yaml --requests-only --output deep_dive_report.html
```

## Configuration

The tool uses YAML configuration files to specify data sources and analysis options:

```yaml
data:
  - extra_metadata:
      platform: RHOAI
      GPU: H100
      GPU_count: 16
    files:
      - "../results/RHOAI/*-1000-1000-sweep.json"
  - extra_metadata:
      platform: llm-d
      GPU: H100  
      GPU_count: 16
    files:
      - "../results/llm-d/*-1000-1000-sweep.json"

options:
  color: platform
  axis_mode: concurrency  # or 'rps'
  concurrency_levels: [1, 2, 4, 8, 16]  # optional filtering
  # rps_levels: [10, 50, 100]  # alternative for RPS mode
```

### Configuration Options

The configuration file consists of two main sections:

#### Data Sources (`data`)
Each data group defines a set of result files and metadata:

- **`files`**: List of file paths to benchmark result JSON files. Supports wildcards (e.g., `"../results/platform-a/*.json"`) for matching multiple files automatically.
- **`extra_metadata`**: Custom metadata fields to attach to all results from these files. This metadata can be used for grouping and comparison in charts (e.g., platform, GPU type, configuration details).

#### Analysis Options (`options`)
- **`color`**: Metadata field to use for grouping/coloring data points in charts. This allows easy visual comparison between different configurations (e.g., 'platform', 'GPU', 'dataset_id').
- **`axis_mode`**: Either 'concurrency' or 'rps' to determine x-axis scaling in charts.
- **`concurrency_levels`**: Optional list to filter analysis to specific concurrency levels only.
- **`rps_levels`**: Optional list to filter analysis to specific RPS levels only (used when axis_mode is 'rps').

The `extra_metadata` feature is particularly useful for comparing results across different test environments, hardware configurations, or software versions - simply add descriptive metadata to each data group and set the `color` option to that field.

## Report Structure

The generated HTML report contains the following tabs:

1. **Throughput**: Output tokens per second vs concurrency/RPS
2. **TTFT**: Time to First Token with subtabs for mean, median, p95, p99
3. **ITL**: Inter-Token Latency with subtabs for mean, median, p95, p99  
4. **Request Latency**: Total request latency with subtabs for mean, median, p95, p99
5. **Input Length**: Average input sequence length
6. **Output Length**: Average output sequence length
7. **TTFT Deep Dive**: Histograms showing TTFT distribution for each configuration
8. **ITL Deep Dive**: Histograms showing ITL distribution for each configuration
9. **Request Scheduling**: Request start/end rates and TTFT timeline analysis

## Requirements

- Python 3.7+
- pandas
- plotly
- jinja2
- pyyaml
- numpy

Install dependencies:

```bash
pip install pandas plotly jinja2 pyyaml numpy
```

## Architecture

The tool is organized into modular components:

- `config.py`: Configuration file handling and validation
- `data_parsers.py`: Parsing summary metrics and individual request data from JSON files
- `visualizations.py`: Creating interactive Plotly charts and graphs
- `html_generator.py`: Assembling charts into final HTML report
- `main.py`: CLI interface and orchestration
- `template.html`: Minimal monospace HTML template

This modular design makes it easy to extend with new chart types, modify styling, or integrate into other workflows.
