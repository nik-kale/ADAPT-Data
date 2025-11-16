# RCA Challenge Sets

This directory contains challenge scenarios for testing and training RCA (Root Cause Analysis) capabilities.

## Structure

Each challenge is defined in a YAML file with:
- **Title**: Challenge name
- **Description**: Scenario description
- **Difficulty**: easy, medium, hard, or expert
- **Incident**: Configuration for generating the incident
- **Hints**: Progressive hints for solving
- **Solution**: Expected root cause and mitigation
- **Evaluation Criteria**: Scoring rubric

## Example Usage

```bash
# Generate a challenge
python -m cli.main challenge generate challenge_001

# Attempt to solve
python -m cli.main challenge attempt challenge_001 --output ./my_solution

# Validate solution
python -m cli.main challenge validate challenge_001 ./my_solution
```

## Creating Challenges

Use the wizard:
```bash
python -m cli.main challenge create
```

Or manually create a YAML file following the schema in `challenge_schema.yaml`.
