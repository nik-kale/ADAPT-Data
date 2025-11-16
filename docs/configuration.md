# Configuration Guide

This document provides a comprehensive guide to configuring ADAPT-Data through configuration files, environment variables, and CLI flags.

## Overview

ADAPT-Data supports multiple configuration methods with a clear precedence order:

1. **CLI flags** (highest precedence)
2. **Environment variables**
3. **`.adapt-data.yaml` configuration file**
4. **Default values** (lowest precedence)

## Configuration File

### File Location

ADAPT-Data searches for `.adapt-data.yaml` (or `.adapt-data.yml`) in the following order:

1. Current working directory
2. Parent directories (up to 10 levels)
3. Home directory (`~/.adapt-data.yaml`)

The first file found is used. This allows project-specific and user-specific configurations.

### Creating a Configuration File

Create a `.adapt-data.yaml` file in your project root:

```yaml
# ADAPT-Data Configuration File

logging:
  level: INFO
  enable_colors: true
  log_file: adapt-data.log

generation:
  default_duration: 1h
  default_severity: SEV3
  default_output_dir: ./output
  enable_progress: true
  parallel_generation: false
  random_seed: 42

validation:
  strict_mode: false
  max_scenario_size_mb: 1
  validate_on_generation: true

export:
  default_format: opentelemetry
  prometheus_port: 9090
  replay_speed: 1.0

advanced:
  enable_distributions: true
  enable_patterns: true
  enable_correlation: true
  noise_level: 0.1
```

## Configuration Sections

### 1. Logging Configuration

Controls logging behavior throughout ADAPT-Data.

```yaml
logging:
  level: INFO                    # Log level: DEBUG, INFO, WARNING, ERROR
  enable_colors: true            # Enable colored terminal output
  log_file: adapt-data.log       # Optional: Write logs to file
```

**Options:**

- **`level`** (string, default: `"INFO"`)
  - Sets the logging verbosity
  - Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`
  - `DEBUG`: Detailed diagnostic information
  - `INFO`: General informational messages
  - `WARNING`: Warning messages only
  - `ERROR`: Error messages only

- **`enable_colors`** (boolean, default: `true`)
  - Enables colored terminal output for better readability
  - INFO messages: green
  - WARNING messages: yellow
  - ERROR messages: red
  - Set to `false` for plain text (useful for CI/CD or file logging)

- **`log_file`** (string, optional, default: `null`)
  - Path to log file for persistent logging
  - If omitted, logs only go to stdout/stderr
  - Relative paths are resolved from current working directory
  - Example: `"./logs/adapt-data.log"` or `"/var/log/adapt-data.log"`

**Example:**

```yaml
logging:
  level: DEBUG
  enable_colors: true
  log_file: ./logs/debug.log
```

### 2. Generation Configuration

Default settings for data generation.

```yaml
generation:
  default_duration: 1h           # Default incident duration
  default_severity: SEV3         # Default severity level
  default_output_dir: ./output   # Default output directory
  enable_progress: true          # Show progress indicators
  parallel_generation: false     # Enable parallel generation
  random_seed: 42                # Optional: Random seed for reproducibility
```

**Options:**

- **`default_duration`** (string, default: `"1h"`)
  - Default incident duration when not specified via CLI
  - Format: `<number><unit>` where unit is `m` (minutes) or `h` (hours)
  - Examples: `"30m"`, `"1h"`, `"2h"`, `"90m"`

- **`default_severity`** (string, default: `"SEV3"`)
  - Default incident severity level
  - Valid values: `SEV1`, `SEV2`, `SEV3`, `SEV4`
  - `SEV1`: Critical, widespread impact
  - `SEV2`: Major, significant impact
  - `SEV3`: Moderate, limited impact
  - `SEV4`: Minor, minimal impact

- **`default_output_dir`** (string, default: `"./output"`)
  - Default directory for generated datasets
  - Can be absolute or relative path
  - Directory will be created if it doesn't exist

- **`enable_progress`** (boolean, default: `true`)
  - Show progress bars and spinners during generation
  - Requires `rich` library (optional dependency)
  - Automatically disabled if rich is not available
  - Set to `false` for cleaner output in CI/CD

- **`parallel_generation`** (boolean, default: `false`)
  - Enable experimental parallel generation
  - Can speed up large dataset generation
  - May use more memory
  - **Note**: Experimental feature, may cause issues

- **`random_seed`** (integer, optional, default: `null`)
  - Random seed for reproducible generation
  - Same seed produces identical output
  - Omit for non-deterministic generation
  - Useful for testing and benchmarking

**Example:**

```yaml
generation:
  default_duration: 2h
  default_severity: SEV2
  default_output_dir: /data/incidents
  enable_progress: true
  random_seed: 12345
```

### 3. Validation Configuration

Settings for dataset validation.

```yaml
validation:
  strict_mode: false             # Enable strict validation
  max_scenario_size_mb: 1        # Max scenario file size in MB
  validate_on_generation: true   # Validate after generation
```

**Options:**

- **`strict_mode`** (boolean, default: `false`)
  - When enabled, validation fails on warnings (not just errors)
  - Useful for ensuring highest data quality
  - Can be overly strict for development

- **`max_scenario_size_mb`** (integer, default: `1`)
  - Maximum allowed scenario file size in megabytes
  - Prevents accidentally loading huge files
  - Security measure against DoS attacks

- **`validate_on_generation`** (boolean, default: `true`)
  - Automatically validate datasets after generation
  - Catches issues immediately
  - Can be disabled for faster iteration during development

**Example:**

```yaml
validation:
  strict_mode: true
  max_scenario_size_mb: 5
  validate_on_generation: true
```

### 4. Export Configuration

Settings for data export and serving.

```yaml
export:
  default_format: opentelemetry  # Default export format
  prometheus_port: 9090          # Prometheus server port
  replay_speed: 1.0              # Replay speed multiplier
```

**Options:**

- **`default_format`** (string, default: `"opentelemetry"`)
  - Default export format for `adapt-data export` command
  - Valid values: `opentelemetry`, `prometheus`, or plugin name
  - Can be overridden via CLI flag

- **`prometheus_port`** (integer, default: `9090`)
  - Default HTTP port for `adapt-data serve` command
  - Must be a valid port number (1-65535)
  - Ensure port is not already in use

- **`replay_speed`** (float, default: `1.0`)
  - Speed multiplier for metric replay in serve mode
  - `1.0`: Real-time replay
  - `2.0`: 2x speed (twice as fast)
  - `0.5`: Half speed (slower)
  - Useful for testing and demos

**Example:**

```yaml
export:
  default_format: prometheus
  prometheus_port: 8080
  replay_speed: 2.0
```

### 5. Advanced Configuration

Advanced features and tuning parameters.

```yaml
advanced:
  enable_distributions: true     # Use parameterized distributions
  enable_patterns: true          # Apply time-series patterns
  enable_correlation: true       # Generate correlated anomalies
  noise_level: 0.1               # Base noise level (0.0-1.0)
```

**Options:**

- **`enable_distributions`** (boolean, default: `true`)
  - Use parameterized probability distributions for realistic data
  - Includes: Normal, Exponential, LogNormal, Poisson, Weibull, Bimodal
  - Disable for simpler, deterministic generation

- **`enable_patterns`** (boolean, default: `true`)
  - Apply time-series patterns to metrics
  - Patterns: Daily cycles, weekly trends, seasonal variation, bursts
  - Makes data more realistic but less predictable

- **`enable_correlation`** (boolean, default: `true`)
  - Generate correlated anomalies across services
  - When one service fails, dependent services also show issues
  - Disable for isolated incidents

- **`noise_level`** (float, default: `0.1`)
  - Base noise level for metric variance
  - Range: 0.0 (no noise) to 1.0 (maximum noise)
  - Higher values create more realistic but noisier data
  - Recommended: 0.05-0.15

**Example:**

```yaml
advanced:
  enable_distributions: true
  enable_patterns: false
  enable_correlation: true
  noise_level: 0.15
```

## Environment Variables

Environment variables override configuration file settings.

### Available Environment Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `ADAPT_LOG_LEVEL` | string | Override logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ADAPT_ENABLE_PROGRESS` | boolean | Enable/disable progress indicators | `true`, `false`, `1`, `0`, `yes`, `no` |
| `ADAPT_OUTPUT_DIR` | string | Override default output directory | `/data/output`, `./results` |
| `ADAPT_RANDOM_SEED` | integer | Set random seed for reproducibility | `42`, `12345` |

### Usage Examples

**Linux/macOS:**

```bash
# Set log level to DEBUG
export ADAPT_LOG_LEVEL=DEBUG

# Disable progress indicators
export ADAPT_ENABLE_PROGRESS=false

# Set custom output directory
export ADAPT_OUTPUT_DIR=/data/incidents

# Set random seed
export ADAPT_RANDOM_SEED=42

# Use for single command
ADAPT_LOG_LEVEL=DEBUG python -m cli.main generate --scenario latency_regression
```

**Windows (PowerShell):**

```powershell
# Set environment variables
$env:ADAPT_LOG_LEVEL = "DEBUG"
$env:ADAPT_ENABLE_PROGRESS = "false"
$env:ADAPT_OUTPUT_DIR = "C:\data\incidents"
$env:ADAPT_RANDOM_SEED = "42"
```

**Windows (CMD):**

```cmd
set ADAPT_LOG_LEVEL=DEBUG
set ADAPT_ENABLE_PROGRESS=false
set ADAPT_OUTPUT_DIR=C:\data\incidents
set ADAPT_RANDOM_SEED=42
```

## CLI Flags

CLI flags have the highest precedence and override both environment variables and configuration file settings.

### Generate Command Flags

```bash
python -m cli.main generate [OPTIONS]
```

**Required:**
- `--scenario SCENARIO`: Scenario name or path to YAML file

**Optional:**
- `--output DIR`: Output directory (default: from config or `./output`)
- `--duration DURATION`: Incident duration (default: from config or `1h`)
- `--severity SEVERITY`: Severity level - `SEV1`, `SEV2`, `SEV3`, `SEV4` (default: from config or `SEV3`)
- `--difficulty LEVEL`: Difficulty level - `beginner`, `easy`, `medium`, `hard`, `expert`

**Examples:**

```bash
# Use all defaults from config
python -m cli.main generate --scenario latency_regression

# Override output and duration
python -m cli.main generate \
  --scenario latency_regression \
  --output ./my-incident \
  --duration 2h

# Set severity and difficulty
python -m cli.main generate \
  --scenario auth_failure \
  --severity SEV1 \
  --difficulty hard
```

### Validate Command Flags

```bash
python -m cli.main validate DATASET_DIR [OPTIONS]
```

**Required:**
- `DATASET_DIR`: Path to dataset directory

**Optional:**
- `--strict`: Enable strict validation mode (fail on warnings)

**Examples:**

```bash
# Standard validation
python -m cli.main validate ./output

# Strict validation
python -m cli.main validate ./output --strict
```

### Other Command Flags

See individual command help for more flags:

```bash
python -m cli.main stats --help
python -m cli.main export --help
python -m cli.main serve --help
```

## Precedence Order

When the same setting is configured in multiple places, ADAPT-Data uses this precedence order (highest to lowest):

1. **CLI flags**: `--output ./my-data`
2. **Environment variables**: `ADAPT_OUTPUT_DIR=./my-data`
3. **Configuration file**: `generation.default_output_dir: ./my-data`
4. **Hard-coded defaults**: `./output`

### Example Precedence

Configuration file:
```yaml
generation:
  default_output_dir: ./config-output
  default_severity: SEV3
```

Environment:
```bash
export ADAPT_OUTPUT_DIR=./env-output
```

Command:
```bash
python -m cli.main generate \
  --scenario latency \
  --output ./cli-output \
  --severity SEV1
```

**Result:**
- Output directory: `./cli-output` (from CLI flag)
- Severity: `SEV1` (from CLI flag)
- Duration: from config file or default `1h`

## Best Practices

### 1. Project Configuration

Create a `.adapt-data.yaml` in your project root for team consistency:

```yaml
logging:
  level: INFO
  enable_colors: true

generation:
  default_output_dir: ./datasets
  enable_progress: true
  # Let developers set their own random seed

validation:
  validate_on_generation: true

advanced:
  enable_distributions: true
  enable_patterns: true
  enable_correlation: true
  noise_level: 0.1
```

### 2. User Configuration

Create `~/.adapt-data.yaml` for personal preferences:

```yaml
logging:
  level: DEBUG  # Personal preference for verbose output
  log_file: ~/adapt-data.log

generation:
  enable_progress: true
```

### 3. CI/CD Configuration

Use environment variables in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
env:
  ADAPT_LOG_LEVEL: INFO
  ADAPT_ENABLE_PROGRESS: false  # No progress bars in CI
  ADAPT_OUTPUT_DIR: /tmp/adapt-data-tests
  ADAPT_RANDOM_SEED: 42  # Reproducible tests
```

### 4. Reproducible Generation

For reproducible datasets (testing, benchmarking):

```yaml
generation:
  random_seed: 42  # Fixed seed

advanced:
  enable_patterns: false  # Disable time-based patterns
  noise_level: 0.0  # Disable noise
```

### 5. Realistic Generation

For production-like datasets (demos, training):

```yaml
generation:
  # Omit random_seed for variety

advanced:
  enable_distributions: true
  enable_patterns: true
  enable_correlation: true
  noise_level: 0.1
```

## Troubleshooting

### Configuration Not Loading

**Problem:** Changes to `.adapt-data.yaml` are not taking effect.

**Solutions:**
1. Verify file location: `python -m cli.main doctor --verbose`
2. Check YAML syntax: Use a YAML validator
3. Check for environment variable overrides
4. Restart your shell/terminal

### Invalid Configuration Values

**Problem:** Configuration validation errors.

**Solutions:**
1. Check data types (string vs boolean vs integer)
2. Verify enum values (e.g., log level must be DEBUG/INFO/WARNING/ERROR)
3. Check numeric ranges (e.g., noise_level must be 0.0-1.0)

### Finding Active Configuration

Use the `doctor` command to see active configuration:

```bash
python -m cli.main doctor --verbose
```

This shows:
- Configuration file location
- Active settings
- Environment variable overrides
- System information

## Related Documentation

- [Tutorial](tutorial.md) - Getting started guide
- [Scenarios](scenarios.md) - Creating custom scenarios
- [CLI Reference](../README.md#cli-commands) - All CLI commands
