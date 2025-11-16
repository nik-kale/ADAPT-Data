# Upgrade Guide: v0.3.0 → v0.4.0

This guide helps you upgrade from ADAPT-Data v0.3.0 to v0.4.0, covering breaking changes, new features, migration steps, and best practices.

## Summary

**Good News:** v0.4.0 is **fully backward compatible** with v0.3.0. No breaking changes!

**What's New:**
- Configuration file system (`.adapt-data.yaml`)
- Progress indicators with Rich library
- Parameterized probability distributions
- Time-series patterns (daily, weekly, seasonal)
- Difficulty levels for challenges
- Correlation analysis
- Plugin system framework

**Migration Effort:** Low - optional features only

## Quick Start

### Minimal Upgrade

If you just want to upgrade and keep everything working as-is:

```bash
# 1. Backup your current setup (optional but recommended)
cp -r ./scenarios ./scenarios.backup

# 2. Pull/install v0.4.0
git pull origin main
# or
pip install --upgrade adapt-data

# 3. Test existing workflows
python -m cli.main generate --scenario latency_regression --output ./test

# 4. Done! Everything should work as before
```

No code changes required. All new features are opt-in.

### Recommended Upgrade

To take advantage of new features:

```bash
# 1. Create configuration file
cat > .adapt-data.yaml <<EOF
logging:
  level: INFO
  enable_colors: true

generation:
  default_duration: 1h
  default_severity: SEV3
  enable_progress: true

advanced:
  enable_distributions: true
  enable_patterns: true
  enable_correlation: true
EOF

# 2. Install optional dependencies for progress bars
pip install "adapt-data[tui]"
# or
pip install rich>=13.0

# 3. Test new features
python -m cli.main generate \
  --scenario latency_regression \
  --difficulty medium \
  --output ./test
```

## No Breaking Changes

v0.4.0 maintains **full backward compatibility**:

### CLI Commands

All v0.3.0 commands work identically in v0.4.0:

```bash
# These all work exactly as before
python -m cli.main generate --scenario latency_regression --output ./data
python -m cli.main validate ./data
python -m cli.main list-scenarios
python -m cli.main stats ./data
python -m cli.main wizard
python -m cli.main export ./data --format opentelemetry --output traces.json
python -m cli.main serve ./data --port 9090
```

### Scenario Files

All v0.3.0 scenario files work without modification:

```yaml
# v0.3.0 scenario - works perfectly in v0.4.0
type: latency_regression
description: Database query regression

parameters:
  affected_service: order-service
  baseline_latency_ms: 50.0
  degraded_latency_ms: 500.0
  error_threshold_ms: 1000.0
```

### Python API

All v0.3.0 Python APIs remain unchanged:

```python
# v0.3.0 code - works in v0.4.0
from generator.core.base import IncidentContext, BaseGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator

context = IncidentContext(
    incident_id="test",
    severity="SEV3",
    output_dir=Path("./output")
)

generator = LatencyRegressionGenerator(context)
generator.generate()
```

### Output Format

Generated data format is identical:

```json
// v0.3.0 and v0.4.0 produce the same schema
{
  "timestamp": "2025-01-16T10:15:00Z",
  "metric_name": "http.server.latency",
  "value": 523.4,
  "service": "order-service",
  "anomaly_injected": true
}
```

## New Features

### 1. Configuration File System

**What:** Centralized configuration via `.adapt-data.yaml`

**Why:** Avoid repeating CLI flags, team consistency

**Migration:**

```bash
# Before (v0.3.0)
python -m cli.main generate \
  --scenario latency \
  --output ./output \
  --duration 2h \
  --severity SEV2

# After (v0.4.0) - create .adapt-data.yaml
cat > .adapt-data.yaml <<EOF
generation:
  default_duration: 2h
  default_severity: SEV2
  default_output_dir: ./output
EOF

# Now just:
python -m cli.main generate --scenario latency
```

**Benefits:**
- Less typing
- Consistent settings across team
- Environment-specific configs
- Version control friendly

**See:** [Configuration Guide](configuration.md)

### 2. Progress Indicators

**What:** Beautiful progress bars and spinners

**Why:** Better UX for long-running operations

**Migration:**

```bash
# Install optional dependency
pip install rich>=13.0

# Enable in config
echo "generation:
  enable_progress: true" >> .adapt-data.yaml

# Or via environment
export ADAPT_ENABLE_PROGRESS=true

# Automatically shows progress during generation
python -m cli.main generate --scenario latency_regression
```

**Output:**
```
Generating latency_regression incident...
  ✓ Creating topology
  ⣾ Generating metrics... 45%
  ○ Generating logs...
  ○ Generating traces...
```

**Benefits:**
- Visual feedback for long operations
- Time estimates
- Better user experience
- Graceful fallback if Rich not installed

### 3. Parameterized Distributions

**What:** Realistic probability distributions for metrics

**Why:** More realistic data, better for ML training

**Migration:**

No code changes needed. Enable in config:

```yaml
# .adapt-data.yaml
advanced:
  enable_distributions: true  # Default in v0.4.0
```

**Effect:**
```python
# v0.3.0: Simple random values
latency = baseline + random.uniform(-10, 10)

# v0.4.0: Realistic distributions
latency = np.random.lognormal(mean=log(baseline), sigma=0.3)
```

**Benefits:**
- More realistic data
- Long-tail behavior (P99, P99.9)
- Better for benchmarking
- Configurable per metric type

**Disable if needed:**
```yaml
advanced:
  enable_distributions: false  # Use simple random for predictability
```

### 4. Time-Series Patterns

**What:** Daily, weekly, and seasonal patterns in metrics

**Why:** Realistic business patterns, better for time-series ML

**Migration:**

Enable in config:

```yaml
advanced:
  enable_patterns: true  # Default in v0.4.0
```

**Effect:**
```
Throughput Pattern:
200 RPS |     _______________           _______________
        |    /               \         /               \
100 RPS |___/                 \_______/                 \___
        |
        +-------------------------------------------------> Time
        0:00   9:00    17:00   0:00   9:00    17:00
        Night  Day     Night   Night  Day     Night
```

**Benefits:**
- Business hour patterns (higher load 9-5)
- Weekend patterns (lower load)
- Seasonal patterns (Q4 holiday traffic)
- More realistic for demos

**Disable for reproducibility:**
```yaml
advanced:
  enable_patterns: false  # Use constant baseline for testing
```

### 5. Difficulty Levels

**What:** Progressive complexity for RCA challenges

**Why:** Training, education, benchmarking

**Migration:**

Use new `--difficulty` flag:

```bash
# v0.3.0: No difficulty setting
python -m cli.main generate --scenario latency_regression

# v0.4.0: Set difficulty
python -m cli.main generate \
  --scenario latency_regression \
  --difficulty hard
```

**Difficulty Levels:**
- **Beginner**: Simple, single service, obvious signals
- **Easy**: 2-3 services, clear correlations
- **Medium**: 3-5 services, moderate noise
- **Hard**: 5-10 services, high noise, multiple anomalies
- **Expert**: 10+ services, very high noise, cascading failures

**Benefits:**
- Training progression
- Benchmarking at different complexity levels
- Educational scenarios

### 6. Correlation Analysis

**What:** Analyze correlations in generated datasets

**Why:** Validate data quality, find relationships

**Migration:**

Use new `correlate` command:

```bash
# v0.4.0: New command
python -m cli.main correlate ./data

# Export results
python -m cli.main correlate ./data --output correlations.json
```

**Output:**
```
=== Correlation Analysis ===

Metric Correlations:
  http.server.latency ↔ db.query.duration: 0.94 (strong)
  http.server.error_rate ↔ http.server.latency: 0.78 (strong)
  system.cpu.usage ↔ http.server.latency: 0.62 (moderate)

Temporal Patterns:
  http.server.latency: Upward trend detected
  db.query.duration: Spike pattern at T+15min

Anomaly Correlations:
  Services with anomalies: order-service (98%), api-gateway (45%)
  Anomaly overlap: 43% of anomalous metrics occur together
```

**Benefits:**
- Validate data realism
- Discover relationships
- Quality assurance
- Research and analysis

### 7. Plugin System

**What:** Extensibility framework for custom generators, exporters, analyzers

**Why:** Customize ADAPT-Data for your needs

**Migration:**

Create plugins in `~/.adapt-data/plugins/`:

```python
# ~/.adapt-data/plugins/my_generator.py
from generator.core.base import BaseGenerator, IncidentContext

class MyCustomGenerator(BaseGenerator):
    name = "my_custom_incident"
    version = "1.0.0"
    description = "My custom incident type"

    def generate(self):
        # Custom generation logic
        pass

# Auto-discovered on startup
```

Use with:

```bash
python -m cli.main list-plugins
python -m cli.main generate --scenario my_custom_incident
```

**Benefits:**
- Extend without forking
- Share custom generators
- Organization-specific incidents
- Custom exporters for proprietary formats

**See:** [Plugin Development](plugin_development.md)

## Migration Checklist

### For Individual Developers

- [ ] Backup existing scenarios and data
- [ ] Pull/install v0.4.0
- [ ] Test existing workflows (should work unchanged)
- [ ] Create `.adapt-data.yaml` in project root
- [ ] Install `rich` for progress bars: `pip install rich`
- [ ] Try new `--difficulty` flag
- [ ] Explore `correlate` command
- [ ] Update bookmarks/docs to new features

### For Teams

- [ ] Review upgrade guide with team
- [ ] Create project `.adapt-data.yaml` for consistency
- [ ] Add `.adapt-data.yaml` to version control
- [ ] Update CI/CD pipelines (optional: add env vars)
- [ ] Update documentation/runbooks
- [ ] Train team on new features
- [ ] Update scenario files with new metadata (optional)

### For CI/CD

**Recommended CI/CD config:**

```yaml
# .github/workflows/generate.yml
env:
  ADAPT_LOG_LEVEL: INFO
  ADAPT_ENABLE_PROGRESS: false  # No progress bars in CI
  ADAPT_RANDOM_SEED: 42         # Reproducible tests

steps:
  - name: Generate test data
    run: |
      python -m cli.main generate \
        --scenario latency_regression \
        --output ./test-data

  - name: Validate
    run: python -m cli.main validate ./test-data --strict
```

**Create `.adapt-data.yaml` for CI:**

```yaml
# .adapt-data.yaml (checked into repo)
logging:
  level: INFO
  enable_colors: false  # Plain text for CI logs

generation:
  enable_progress: false  # No progress bars in CI
  random_seed: 42        # Reproducible by default

validation:
  strict_mode: true  # Fail on warnings in CI

advanced:
  enable_patterns: false  # Disable time-based patterns for reproducibility
```

## Environment Variables

New environment variables in v0.4.0:

```bash
# Logging
export ADAPT_LOG_LEVEL=DEBUG          # Override log level

# Generation
export ADAPT_ENABLE_PROGRESS=false    # Disable progress indicators
export ADAPT_OUTPUT_DIR=/data/output  # Default output directory
export ADAPT_RANDOM_SEED=42           # Reproducible generation
```

These override `.adapt-data.yaml` settings.

## Performance Changes

### v0.4.0 Performance

Generation is slightly slower due to advanced features:

| Duration | v0.3.0 | v0.4.0 | Delta |
|----------|--------|--------|-------|
| 1h       | 2.5s   | 3.0s   | +20%  |
| 24h      | 35s    | 45s    | +29%  |

**Why:** More realistic distributions, patterns, correlations

**Optimize if needed:**

```yaml
# Fast generation (v0.3.0-like performance)
advanced:
  enable_distributions: false
  enable_patterns: false
  enable_correlation: false
  noise_level: 0.05  # Less noise
```

### Memory Usage

Slightly higher memory usage:

| Duration | v0.3.0 | v0.4.0 | Delta |
|----------|--------|--------|-------|
| 1h       | 45 MB  | 50 MB  | +11%  |
| 24h      | 450 MB | 500 MB | +11%  |

**Why:** Additional pattern state, correlation tracking

## Troubleshooting

### Issue: Commands still work but no new features

**Problem:** Installed v0.4.0 but not seeing progress bars or new features.

**Solution:**
1. Verify version: `python -m cli.main version`
2. Check if Rich installed: `pip list | grep rich`
3. Enable in config: `enable_progress: true`
4. Check env vars: `env | grep ADAPT_`

### Issue: Progress bars not showing

**Problem:** Progress bars don't appear.

**Solutions:**
1. Install Rich: `pip install rich>=13.0` or `pip install "adapt-data[tui]"`
2. Enable in config: `generation.enable_progress: true`
3. Check terminal supports color: `export TERM=xterm-256color`
4. Not available in pipes: `python -m cli.main generate ... | tee log.txt` won't show progress

### Issue: Data looks different from v0.3.0

**Problem:** Generated data has different values than v0.3.0 with same seed.

**Explanation:** New distributions and patterns create different (more realistic) data.

**Solution for exact reproduction:**
```yaml
# Disable new features for v0.3.0-like data
advanced:
  enable_distributions: false
  enable_patterns: false
  enable_correlation: false
```

### Issue: Slower generation

**Problem:** v0.4.0 generation is slower than v0.3.0.

**Solution:**
```yaml
# Optimize for speed
advanced:
  enable_distributions: false
  enable_patterns: false
  enable_correlation: false

generation:
  parallel_generation: true  # Experimental
```

### Issue: Configuration not loading

**Problem:** `.adapt-data.yaml` changes not taking effect.

**Solutions:**
1. Check file location: `python -m cli.main doctor --verbose`
2. Verify YAML syntax: Use a YAML linter
3. Check for env var overrides: `env | grep ADAPT_`
4. Restart terminal/shell

## Testing Your Upgrade

### Automated Testing

Create a test script:

```bash
#!/bin/bash
# test-upgrade.sh

set -e

echo "Testing v0.4.0 upgrade..."

# Test backward compatibility
echo "1. Testing v0.3.0 scenarios..."
python -m cli.main generate --scenario latency_regression --output /tmp/test1
python -m cli.main validate /tmp/test1

# Test new features
echo "2. Testing new difficulty levels..."
python -m cli.main generate --scenario auth_failure --difficulty hard --output /tmp/test2

# Test correlation
echo "3. Testing correlation analysis..."
python -m cli.main correlate /tmp/test2

# Test with config file
echo "4. Testing config file..."
cat > /tmp/.adapt-data.yaml <<EOF
generation:
  default_duration: 30m
  enable_progress: true
EOF
cd /tmp && python -m cli.main generate --scenario packet_loss --output test3

echo "All tests passed!"
```

Run with:
```bash
chmod +x test-upgrade.sh
./test-upgrade.sh
```

### Manual Testing

1. **Test existing workflow:**
   ```bash
   python -m cli.main generate --scenario latency_regression --output ./test-v0.4.0
   python -m cli.main validate ./test-v0.4.0
   ```

2. **Test new features:**
   ```bash
   python -m cli.main generate --scenario auth_failure --difficulty medium --output ./test-difficulty
   python -m cli.main correlate ./test-difficulty
   ```

3. **Test configuration:**
   ```bash
   cat > .adapt-data.yaml <<EOF
   generation:
     default_duration: 30m
     enable_progress: true
   EOF
   python -m cli.main generate --scenario packet_loss
   ```

## Rollback

If you need to rollback to v0.3.0:

```bash
# Git-based installation
git checkout v0.3.0
pip install -e .

# Pip installation
pip install adapt-data==0.3.0

# Verify
python -m cli.main version
```

**Note:** v0.4.0 data works in v0.3.0 (schemas unchanged).

## Getting Help

If you encounter issues:

1. **Check logs:** Enable DEBUG logging
   ```bash
   export ADAPT_LOG_LEVEL=DEBUG
   python -m cli.main generate --scenario latency_regression
   ```

2. **Run doctor:** Check system health
   ```bash
   python -m cli.main doctor --verbose
   ```

3. **Check documentation:**
   - [Configuration Guide](configuration.md)
   - [FAQ](FAQ.md)
   - [Troubleshooting](FAQ.md#troubleshooting)

4. **Report issues:**
   - GitHub: https://github.com/your-org/ADAPT-Data/issues
   - Include version, OS, logs, and reproduction steps

## What's Next

### Future Versions

Planned for upcoming releases:

- **v0.5.0**: Real-time streaming generation
- **v0.6.0**: Machine learning integration
- **v0.7.0**: Cloud provider integrations

### Staying Updated

- Watch GitHub repo for releases
- Subscribe to changelog
- Follow ADAPT project updates

## Summary

**v0.4.0 is a safe, backward-compatible upgrade** with powerful new features:

- ✅ No breaking changes
- ✅ All v0.3.0 code works unchanged
- ✅ New features are opt-in
- ✅ Configuration file system
- ✅ Progress indicators
- ✅ Better realism (distributions, patterns)
- ✅ Difficulty levels
- ✅ Correlation analysis
- ✅ Plugin system

**Recommended migration:**
1. Create `.adapt-data.yaml`
2. Install `rich` for progress bars
3. Enable new features in config
4. Test thoroughly
5. Enjoy improved experience!

## Related Documentation

- [Configuration Guide](configuration.md) - Complete config reference
- [FAQ](FAQ.md) - Common questions and issues
- [CHANGELOG](../CHANGELOG.md) - Detailed change history
- [Plugin Development](plugin_development.md) - Creating plugins
