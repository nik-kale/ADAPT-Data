# Real-World Incident Library

This directory contains synthetic recreations of real-world incidents from major cloud providers and SaaS companies.

## Purpose

- **Benchmarking**: Test RCA algorithms against realistic scenarios
- **Education**: Learn from real incidents in a safe environment
- **Research**: Study incident patterns and detection methods

## Structure

Each incident is defined in a YAML file based on publicly available postmortems:

- AWS outages
- Google Cloud incidents
- Azure disruptions
- Major SaaS incidents (GitHub, Slack, etc.)

## Attribution

All incidents are based on publicly available postmortems and status pages. Links to original sources are provided in each file.

## Usage

```bash
# Generate recreation of real incident
python -m cli.main generate --scenario real_world/aws_us_east_1_2023

# Compare RCA results against known root cause
python -m cli.main benchmark --incident real_world/aws_us_east_1_2023
```

## Disclaimer

These are synthetic recreations for educational and testing purposes. They are inspired by real incidents but do not contain any proprietary or sensitive information.
