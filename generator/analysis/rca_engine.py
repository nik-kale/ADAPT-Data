"""Automated Root Cause Analysis (RCA) Engine.

Analyzes synthetic incident data to suggest root causes and
diagnostic insights using pattern matching and heuristics.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class RCASuggestion:
    """Root cause analysis suggestion."""

    root_cause: str
    confidence: float  # 0.0 to 1.0
    evidence: list[str]
    mitigation_steps: list[str]
    related_metrics: list[str]
    category: str  # performance, availability, resource, configuration


class RCAEngine:
    """Automated root cause analysis engine.

    Analyzes incident data to provide automated RCA suggestions
    with confidence scores and supporting evidence.
    """

    def __init__(self, incident_dir: Path):
        """Initialize RCA engine.

        Args:
            incident_dir: Directory containing incident data
        """
        self.incident_dir = incident_dir
        self.logs = []
        self.metrics = []
        self.traces = []
        self.timeline = {}

    def load_incident_data(self) -> None:
        """Load all incident data from directory."""
        # Load logs
        logs_dir = self.incident_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.jsonl"):
                with open(log_file) as f:
                    for line in f:
                        if line.strip():
                            self.logs.append(json.loads(line))

        # Load metrics
        metrics_dir = self.incident_dir / "metrics"
        if metrics_dir.exists():
            for metric_file in metrics_dir.glob("*.jsonl"):
                with open(metric_file) as f:
                    for line in f:
                        if line.strip():
                            self.metrics.append(json.loads(line))

        # Load traces
        traces_dir = self.incident_dir / "traces"
        if traces_dir.exists():
            for trace_file in traces_dir.glob("*.jsonl"):
                with open(trace_file) as f:
                    for line in f:
                        if line.strip():
                            self.traces.append(json.loads(line))

        # Load timeline
        timeline_dir = self.incident_dir / "timelines"
        if timeline_dir.exists():
            timeline_files = list(timeline_dir.glob("*.json"))
            if timeline_files:
                with open(timeline_files[0]) as f:
                    self.timeline = json.load(f)

    def analyze(self) -> list[RCASuggestion]:
        """Perform automated root cause analysis.

        Returns:
            List of RCA suggestions ordered by confidence
        """
        suggestions = []

        # Analyze different aspects
        suggestions.extend(self._analyze_latency_issues())
        suggestions.extend(self._analyze_error_patterns())
        suggestions.extend(self._analyze_resource_exhaustion())
        suggestions.extend(self._analyze_configuration_changes())
        suggestions.extend(self._analyze_dependency_failures())
        suggestions.extend(self._analyze_genai_issues())

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        return suggestions

    def _analyze_latency_issues(self) -> list[RCASuggestion]:
        """Analyze latency-related issues."""
        suggestions = []

        # Find latency metrics
        latency_metrics = [
            m for m in self.metrics
            if 'latency' in m.get('metric_name', '').lower()
            or 'duration' in m.get('metric_name', '').lower()
        ]

        if not latency_metrics:
            return suggestions

        # Calculate statistics
        values = [m['value'] for m in latency_metrics]
        baseline = np.percentile(values, 25)  # First quartile as baseline
        p95 = np.percentile(values, 95)
        p99 = np.percentile(values, 99)

        # Check for latency spike
        if p95 > baseline * 3:
            evidence = [
                f"p95 latency: {p95:.2f}ms (baseline: {baseline:.2f}ms)",
                f"p99 latency: {p99:.2f}ms",
                f"{len(latency_metrics)} latency measurements analyzed"
            ]

            # Check logs for clues
            slow_query_logs = [
                log for log in self.logs
                if 'slow query' in log.get('message', '').lower()
                or 'inefficient' in log.get('message', '').lower()
            ]

            if slow_query_logs:
                evidence.append(f"Found {len(slow_query_logs)} slow query log entries")
                root_cause = "Database performance degradation due to inefficient queries"
                mitigation = [
                    "Add indexes to frequently queried columns",
                    "Optimize query execution plans",
                    "Enable query result caching",
                    "Consider read replicas for read-heavy workloads"
                ]
                confidence = 0.85
            else:
                root_cause = "Application latency spike detected"
                mitigation = [
                    "Profile application code for bottlenecks",
                    "Check external API response times",
                    "Review resource utilization (CPU, memory)",
                    "Examine network latency"
                ]
                confidence = 0.70

            suggestions.append(RCASuggestion(
                root_cause=root_cause,
                confidence=confidence,
                evidence=evidence,
                mitigation_steps=mitigation,
                related_metrics=['latency', 'duration', 'response_time'],
                category='performance'
            ))

        return suggestions

    def _analyze_error_patterns(self) -> list[RCASuggestion]:
        """Analyze error patterns in logs."""
        suggestions = []

        error_logs = [log for log in self.logs if log.get('level') == 'ERROR']

        if not error_logs:
            return suggestions

        # Categorize errors
        error_types = {}
        for log in error_logs:
            msg = log.get('message', '').lower()
            if 'connection' in msg or 'timeout' in msg:
                error_types['connection'] = error_types.get('connection', 0) + 1
            elif 'auth' in msg or 'permission' in msg or 'forbidden' in msg:
                error_types['auth'] = error_types.get('auth', 0) + 1
            elif 'database' in msg or 'sql' in msg:
                error_types['database'] = error_types.get('database', 0) + 1
            elif 'memory' in msg or 'oom' in msg:
                error_types['memory'] = error_types.get('memory', 0) + 1

        # Generate suggestions based on dominant error type
        if error_types:
            dominant_type = max(error_types.items(), key=lambda x: x[1])
            error_category, count = dominant_type

            if error_category == 'connection':
                suggestions.append(RCASuggestion(
                    root_cause="Connection pool exhaustion or network issues",
                    confidence=0.80,
                    evidence=[
                        f"{count} connection-related errors found",
                        f"Total error logs: {len(error_logs)}"
                    ],
                    mitigation_steps=[
                        "Increase connection pool size",
                        "Implement connection retry logic",
                        "Check network connectivity",
                        "Review firewall and security group rules"
                    ],
                    related_metrics=['connection_pool_active', 'connection_errors'],
                    category='availability'
                ))
            elif error_category == 'auth':
                suggestions.append(RCASuggestion(
                    root_cause="Authentication or authorization failures",
                    confidence=0.85,
                    evidence=[
                        f"{count} auth-related errors found",
                        f"Total error logs: {len(error_logs)}"
                    ],
                    mitigation_steps=[
                        "Verify credentials and API keys",
                        "Check token expiration",
                        "Review permission policies",
                        "Examine auth service health"
                    ],
                    related_metrics=['auth_failures', 'token_validations'],
                    category='availability'
                ))

        return suggestions

    def _analyze_resource_exhaustion(self) -> list[RCASuggestion]:
        """Analyze resource exhaustion patterns."""
        suggestions = []

        # Find resource metrics
        cpu_metrics = [m for m in self.metrics if 'cpu' in m.get('metric_name', '').lower()]
        memory_metrics = [m for m in self.metrics if 'memory' in m.get('metric_name', '').lower()]

        # Check CPU exhaustion
        if cpu_metrics:
            cpu_values = [m['value'] for m in cpu_metrics]
            avg_cpu = np.mean(cpu_values)
            max_cpu = np.max(cpu_values)

            if avg_cpu > 80 or max_cpu > 95:
                suggestions.append(RCASuggestion(
                    root_cause="CPU exhaustion",
                    confidence=0.90,
                    evidence=[
                        f"Average CPU: {avg_cpu:.1f}%",
                        f"Peak CPU: {max_cpu:.1f}%",
                        f"{len(cpu_metrics)} CPU measurements"
                    ],
                    mitigation_steps=[
                        "Scale horizontally (add more instances)",
                        "Scale vertically (larger instance type)",
                        "Optimize CPU-intensive code paths",
                        "Enable auto-scaling based on CPU"
                    ],
                    related_metrics=['cpu_usage', 'cpu_throttling'],
                    category='resource'
                ))

        # Check memory exhaustion
        if memory_metrics:
            mem_values = [m['value'] for m in memory_metrics]
            avg_mem = np.mean(mem_values)
            max_mem = np.max(mem_values)

            if avg_mem > 85 or max_mem > 95:
                # Check for memory leak
                trend = np.polyfit(range(len(mem_values)), mem_values, 1)[0]
                is_leak = trend > 0.1

                if is_leak:
                    root_cause = "Memory leak detected"
                    confidence = 0.85
                    mitigation = [
                        "Profile application for memory leaks",
                        "Review object retention and garbage collection",
                        "Check for unbounded caches or collections",
                        "Restart affected instances as immediate mitigation"
                    ]
                else:
                    root_cause = "Memory exhaustion"
                    confidence = 0.80
                    mitigation = [
                        "Increase instance memory",
                        "Optimize memory usage",
                        "Implement memory limits and quotas",
                        "Review data structure sizes"
                    ]

                suggestions.append(RCASuggestion(
                    root_cause=root_cause,
                    confidence=confidence,
                    evidence=[
                        f"Average memory: {avg_mem:.1f}%",
                        f"Peak memory: {max_mem:.1f}%",
                        f"Memory trend: {'increasing' if is_leak else 'stable'}"
                    ],
                    mitigation_steps=mitigation,
                    related_metrics=['memory_usage', 'heap_size'],
                    category='resource'
                ))

        return suggestions

    def _analyze_configuration_changes(self) -> list[RCASuggestion]:
        """Analyze configuration changes."""
        suggestions = []

        config_logs = [
            log for log in self.logs
            if 'config' in log.get('message', '').lower()
            or 'setting' in log.get('message', '').lower()
        ]

        if config_logs:
            suggestions.append(RCASuggestion(
                root_cause="Recent configuration change",
                confidence=0.75,
                evidence=[
                    f"{len(config_logs)} configuration-related log entries",
                    "Configuration changes detected during incident window"
                ],
                mitigation_steps=[
                    "Review recent configuration changes",
                    "Rollback to previous configuration",
                    "Compare current vs previous settings",
                    "Implement configuration validation"
                ],
                related_metrics=['config_version', 'deployment_time'],
                category='configuration'
            ))

        return suggestions

    def _analyze_dependency_failures(self) -> list[RCASuggestion]:
        """Analyze dependency failures."""
        suggestions = []

        # Check traces for failed downstream calls
        failed_spans = []
        for trace in self.traces:
            for span in trace.get('spans', []):
                if span.get('status') != 'OK':
                    failed_spans.append(span)

        if failed_spans:
            # Group by service
            failed_services = {}
            for span in failed_spans:
                service = span.get('service', 'unknown')
                failed_services[service] = failed_services.get(service, 0) + 1

            if failed_services:
                most_failed = max(failed_services.items(), key=lambda x: x[1])
                service, count = most_failed

                suggestions.append(RCASuggestion(
                    root_cause=f"Dependency failure: {service}",
                    confidence=0.88,
                    evidence=[
                        f"{count} failed calls to {service}",
                        f"Total failed spans: {len(failed_spans)}",
                        f"Affected services: {list(failed_services.keys())}"
                    ],
                    mitigation_steps=[
                        f"Check health of {service}",
                        "Implement circuit breaker pattern",
                        "Add fallback mechanisms",
                        "Review retry policies"
                    ],
                    related_metrics=['dependency_errors', 'circuit_breaker_open'],
                    category='availability'
                ))

        return suggestions

    def _analyze_genai_issues(self) -> list[RCASuggestion]:
        """Analyze GenAI/LLM-specific issues."""
        suggestions = []

        # Check for GenAI metrics
        genai_metrics = [
            m for m in self.metrics
            if 'genai' in m.get('metric_name', '').lower()
            or 'token' in m.get('metric_name', '').lower()
        ]

        if not genai_metrics:
            return suggestions

        # Analyze token usage
        token_metrics = [m for m in genai_metrics if 'token' in m.get('metric_name', '').lower()]
        if token_metrics:
            token_values = [m['value'] for m in token_metrics]
            avg_tokens = np.mean(token_values)
            max_tokens = np.max(token_values)

            # Check if approaching context window limits (assuming 8192)
            if max_tokens > 7000:
                suggestions.append(RCASuggestion(
                    root_cause="LLM context window exhaustion",
                    confidence=0.90,
                    evidence=[
                        f"Average token usage: {avg_tokens:.0f}",
                        f"Peak token usage: {max_tokens:.0f}",
                        "Token usage approaching model limits"
                    ],
                    mitigation_steps=[
                        "Implement prompt compression",
                        "Truncate conversation history",
                        "Use sliding window for long contexts",
                        "Consider models with larger context windows"
                    ],
                    related_metrics=['genai.token.usage', 'genai.request.duration'],
                    category='performance'
                ))

        # Check for rate limiting
        rate_limit_logs = [
            log for log in self.logs
            if 'rate limit' in log.get('message', '').lower()
        ]

        if rate_limit_logs:
            suggestions.append(RCASuggestion(
                root_cause="LLM API rate limiting",
                confidence=0.85,
                evidence=[
                    f"{len(rate_limit_logs)} rate limit messages",
                    "API request rate exceeding limits"
                ],
                mitigation_steps=[
                    "Implement request queueing",
                    "Add exponential backoff",
                    "Upgrade API tier for higher limits",
                    "Distribute load across multiple API keys"
                ],
                related_metrics=['genai.request.rate', 'genai.request.error_rate'],
                category='availability'
            ))

        return suggestions

    def generate_report(self, suggestions: list[RCASuggestion]) -> dict[str, Any]:
        """Generate RCA report.

        Args:
            suggestions: List of RCA suggestions

        Returns:
            Comprehensive RCA report
        """
        if not suggestions:
            return {
                "status": "no_suggestions",
                "message": "No root cause suggestions generated"
            }

        top_suggestion = suggestions[0]

        return {
            "incident_summary": {
                "incident_id": self.timeline.get("incident_id"),
                "severity": self.timeline.get("severity"),
                "duration": self._calculate_duration(),
                "affected_services": self._get_affected_services()
            },
            "root_cause_analysis": {
                "primary_cause": top_suggestion.root_cause,
                "confidence": top_suggestion.confidence,
                "category": top_suggestion.category,
                "evidence": top_suggestion.evidence
            },
            "recommended_actions": {
                "immediate": top_suggestion.mitigation_steps[:2],
                "short_term": top_suggestion.mitigation_steps[2:],
                "monitoring": top_suggestion.related_metrics
            },
            "alternative_hypotheses": [
                {
                    "cause": s.root_cause,
                    "confidence": s.confidence,
                    "category": s.category
                }
                for s in suggestions[1:4]  # Top 3 alternatives
            ] if len(suggestions) > 1 else [],
            "data_analyzed": {
                "log_entries": len(self.logs),
                "metrics": len(self.metrics),
                "traces": len(self.traces)
            }
        }

    def _calculate_duration(self) -> str:
        """Calculate incident duration."""
        if not self.timeline:
            return "unknown"

        start = datetime.fromisoformat(self.timeline.get("start_time", "").replace('Z', '+00:00'))
        end = datetime.fromisoformat(self.timeline.get("end_time", "").replace('Z', '+00:00'))
        duration = end - start

        hours = duration.total_seconds() / 3600
        if hours < 1:
            return f"{int(duration.total_seconds() / 60)} minutes"
        else:
            return f"{hours:.1f} hours"

    def _get_affected_services(self) -> list[str]:
        """Get list of affected services."""
        services = set()

        for log in self.logs:
            if log.get('service'):
                services.add(log['service'])

        for metric in self.metrics:
            if metric.get('service'):
                services.add(metric['service'])

        return list(services)
