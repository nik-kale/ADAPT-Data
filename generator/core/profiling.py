"""Profiling data generation for ADAPT-Data.

Generates CPU, memory, heap, and other profiling data compatible with
OpenTelemetry profiling signals and pprof format.

Reference: https://opentelemetry.io/docs/specs/otel/profiles/
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from generator.core.utils import generate_uuid, timestamp_to_iso


@dataclass
class ProfileSample:
    """Represents a single profiling sample."""

    timestamp: datetime
    service: str
    host: str
    profile_type: str  # cpu, memory, heap, goroutine, etc.
    duration_ns: int  # Duration of the profiling sample
    samples: list[dict[str, Any]]  # Stack trace samples
    labels: dict[str, str]  # Additional labels


class ProfilingGenerator:
    """Generates profiling data for services."""

    # Common function names for realistic stack traces
    COMMON_FUNCTIONS = [
        # HTTP handlers
        "http.Handler.ServeHTTP",
        "http.(*ServeMux).ServeHTTP",
        "http.serverHandler.ServeHTTP",
        "http.HandlerFunc.ServeHTTP",

        # Database
        "database/sql.(*DB).Query",
        "database/sql.(*DB).Exec",
        "database/sql.(*Rows).Scan",
        "github.com/lib/pq.(*conn).Query",

        # Business logic
        "main.processRequest",
        "main.handleUserRequest",
        "main.fetchUserData",
        "main.validateInput",
        "main.processPayment",
        "main.updateInventory",

        # JSON/encoding
        "encoding/json.Marshal",
        "encoding/json.Unmarshal",
        "encoding/json.(*Encoder).Encode",

        # Crypto
        "crypto/sha256.Sum256",
        "crypto/tls.(*Conn).Handshake",

        # I/O
        "io.Copy",
        "io.ReadAll",
        "bufio.(*Reader).Read",

        # Runtime
        "runtime.mallocgc",
        "runtime.newobject",
        "runtime.makeslice",
        "runtime.mapassign",
        "runtime.growslice",
        "runtime.convT2E",

        # Sync
        "sync.(*Mutex).Lock",
        "sync.(*Mutex).Unlock",
        "sync.(*WaitGroup).Wait",
        "sync.(*RWMutex).RLock",
    ]

    # File paths for stack traces
    FILE_PATHS = [
        "/usr/local/go/src/net/http/server.go",
        "/usr/local/go/src/database/sql/sql.go",
        "/app/main.go",
        "/app/handlers/user.go",
        "/app/handlers/payment.go",
        "/app/models/user.go",
        "/app/utils/validator.go",
        "/usr/local/go/src/encoding/json/encode.go",
        "/usr/local/go/src/runtime/malloc.go",
        "/usr/local/go/src/runtime/slice.go",
    ]

    def __init__(self, service: str, host: str):
        """Initialize profiling generator.

        Args:
            service: Service name
            host: Host identifier
        """
        self.service = service
        self.host = host

    def generate_cpu_profile(
        self,
        start_time: datetime,
        duration: timedelta = timedelta(seconds=30),
        num_samples: int = 100,
        is_anomalous: bool = False
    ) -> ProfileSample:
        """Generate CPU profiling data.

        Args:
            start_time: Profile start time
            duration: Profile duration
            num_samples: Number of samples to generate
            is_anomalous: Whether to inject anomalous patterns

        Returns:
            ProfileSample with CPU profiling data
        """
        samples = []

        # Hot functions during anomalies
        hot_functions = [
            "database/sql.(*DB).Query",
            "encoding/json.Marshal",
            "runtime.mallocgc",
            "main.processRequest",
        ] if is_anomalous else []

        for _ in range(num_samples):
            # Generate stack trace
            stack_depth = random.randint(3, 12)
            stack_trace = self._generate_stack_trace(
                stack_depth,
                hot_functions=hot_functions
            )

            # Sample value (CPU time in nanoseconds)
            if is_anomalous:
                # More CPU time consumed during anomalies
                value = random.randint(1_000_000, 50_000_000)
            else:
                value = random.randint(100_000, 5_000_000)

            samples.append({
                "locations": stack_trace,
                "value": value,
            })

        return ProfileSample(
            timestamp=start_time,
            service=self.service,
            host=self.host,
            profile_type="cpu",
            duration_ns=int(duration.total_seconds() * 1e9),
            samples=samples,
            labels={
                "profile.type": "cpu",
                "service.name": self.service,
                "host.name": self.host,
            }
        )

    def generate_memory_profile(
        self,
        start_time: datetime,
        duration: timedelta = timedelta(seconds=30),
        num_samples: int = 100,
        is_anomalous: bool = False
    ) -> ProfileSample:
        """Generate memory/heap profiling data.

        Args:
            start_time: Profile start time
            duration: Profile duration
            num_samples: Number of samples to generate
            is_anomalous: Whether to inject anomalous patterns (memory leak)

        Returns:
            ProfileSample with memory profiling data
        """
        samples = []

        # Functions that allocate memory
        allocating_functions = [
            "runtime.mallocgc",
            "runtime.newobject",
            "runtime.makeslice",
            "runtime.growslice",
            "encoding/json.Unmarshal",
            "main.fetchUserData",
        ]

        for i in range(num_samples):
            # Generate stack trace
            stack_depth = random.randint(3, 10)
            stack_trace = self._generate_stack_trace(
                stack_depth,
                hot_functions=allocating_functions
            )

            # Allocation size in bytes
            if is_anomalous:
                # Memory leak: increasing allocations over time
                base_size = 1024 * 1024  # 1MB
                leak_multiplier = 1 + (i / num_samples) * 10
                value = int(base_size * leak_multiplier * random.uniform(0.8, 1.2))
            else:
                # Normal allocation sizes
                value = random.randint(1024, 1024 * 512)  # 1KB to 512KB

            samples.append({
                "locations": stack_trace,
                "value": value,
                "alloc_objects": random.randint(1, 100),
                "alloc_bytes": value,
            })

        return ProfileSample(
            timestamp=start_time,
            service=self.service,
            host=self.host,
            profile_type="memory",
            duration_ns=int(duration.total_seconds() * 1e9),
            samples=samples,
            labels={
                "profile.type": "heap",
                "service.name": self.service,
                "host.name": self.host,
            }
        )

    def generate_goroutine_profile(
        self,
        start_time: datetime,
        num_goroutines: int = None,
        is_anomalous: bool = False
    ) -> ProfileSample:
        """Generate goroutine profiling data.

        Args:
            start_time: Profile timestamp
            num_goroutines: Number of goroutines (auto if None)
            is_anomalous: Whether to show goroutine leak

        Returns:
            ProfileSample with goroutine profiling data
        """
        if num_goroutines is None:
            if is_anomalous:
                # Goroutine leak
                num_goroutines = random.randint(5000, 50000)
            else:
                # Normal goroutine count
                num_goroutines = random.randint(10, 500)

        samples = []

        # Generate goroutine stack traces
        for _ in range(min(num_goroutines, 100)):  # Sample up to 100
            stack_depth = random.randint(2, 8)
            stack_trace = self._generate_stack_trace(stack_depth)

            # Number of goroutines with this stack
            if is_anomalous:
                count = random.randint(50, 500)
            else:
                count = random.randint(1, 10)

            samples.append({
                "locations": stack_trace,
                "value": count,
            })

        return ProfileSample(
            timestamp=start_time,
            service=self.service,
            host=self.host,
            profile_type="goroutine",
            duration_ns=0,  # Snapshot profile
            samples=samples,
            labels={
                "profile.type": "goroutine",
                "service.name": self.service,
                "host.name": self.host,
                "total.goroutines": str(num_goroutines),
            }
        )

    def _generate_stack_trace(
        self,
        depth: int,
        hot_functions: list[str] = None
    ) -> list[dict[str, Any]]:
        """Generate a realistic stack trace.

        Args:
            depth: Stack depth
            hot_functions: Functions to appear more frequently (optional)

        Returns:
            List of stack frame locations
        """
        stack = []

        for i in range(depth):
            # Select function
            if hot_functions and random.random() < 0.6:
                function = random.choice(hot_functions)
            else:
                function = random.choice(self.COMMON_FUNCTIONS)

            # Select file path
            file_path = random.choice(self.FILE_PATHS)

            # Generate line number
            line_num = random.randint(10, 500)

            stack.append({
                "function": function,
                "filename": file_path,
                "line": line_num,
            })

        return stack

    def to_otlp_format(self, profile: ProfileSample) -> dict[str, Any]:
        """Convert ProfileSample to OTLP profiling format.

        Args:
            profile: ProfileSample to convert

        Returns:
            OTLP-formatted profile data
        """
        # Build function table
        function_table = []
        function_ids = {}

        # Build location table
        location_table = []
        location_ids = {}

        # Process samples
        otlp_samples = []
        for sample in profile.samples:
            location_indices = []

            for frame in sample["locations"]:
                # Add function if not seen
                func_key = (frame["function"], frame["filename"])
                if func_key not in function_ids:
                    function_ids[func_key] = len(function_table)
                    function_table.append({
                        "id": len(function_table),
                        "name": frame["function"],
                        "filename": frame["filename"],
                    })

                # Add location if not seen
                loc_key = (frame["function"], frame["filename"], frame["line"])
                if loc_key not in location_ids:
                    location_ids[loc_key] = len(location_table)
                    location_table.append({
                        "id": len(location_table),
                        "line": [{"functionId": function_ids[func_key], "line": frame["line"]}]
                    })

                location_indices.append(location_ids[loc_key])

            otlp_samples.append({
                "locationIndex": location_indices,
                "value": [sample["value"]],
                "attributes": []
            })

        return {
            "resourceProfiles": [{
                "resource": {
                    "attributes": [
                        {"key": k, "value": {"stringValue": v}}
                        for k, v in profile.labels.items()
                    ]
                },
                "scopeProfiles": [{
                    "scope": {"name": "adapt-data-profiling"},
                    "profiles": [{
                        "profileId": generate_uuid(),
                        "startTimeUnixNano": int(profile.timestamp.timestamp() * 1e9),
                        "endTimeUnixNano": int(profile.timestamp.timestamp() * 1e9) + profile.duration_ns,
                        "attributes": [],
                        "sampleType": [{
                            "type": profile.profile_type,
                            "unit": "nanoseconds" if profile.profile_type == "cpu" else "bytes"
                        }],
                        "sample": otlp_samples,
                        "location": location_table,
                        "function": function_table,
                    }]
                }]
            }]
        }

    def to_pprof_format(self, profile: ProfileSample) -> dict[str, Any]:
        """Convert ProfileSample to pprof-compatible format.

        Args:
            profile: ProfileSample to convert

        Returns:
            pprof-formatted profile data (simplified)
        """
        # Build string table (index 0 is always empty string)
        string_table = [""]
        string_ids = {"": 0}

        def get_string_id(s: str) -> int:
            if s not in string_ids:
                string_ids[s] = len(string_table)
                string_table.append(s)
            return string_ids[s]

        # Build function and location tables
        functions = []
        locations = []

        # Process samples
        samples = []
        for sample_data in profile.samples:
            location_ids = []

            for frame in sample_data["locations"]:
                # Add function
                func_id = len(functions) + 1
                functions.append({
                    "id": func_id,
                    "name": get_string_id(frame["function"]),
                    "filename": get_string_id(frame["filename"]),
                })

                # Add location
                loc_id = len(locations) + 1
                locations.append({
                    "id": loc_id,
                    "line": [{
                        "functionId": func_id,
                        "line": frame["line"]
                    }]
                })

                location_ids.append(loc_id)

            samples.append({
                "locationId": location_ids,
                "value": [sample_data["value"]],
            })

        return {
            "sampleType": [{
                "type": get_string_id(profile.profile_type),
                "unit": get_string_id("nanoseconds" if profile.profile_type == "cpu" else "bytes")
            }],
            "sample": samples,
            "location": locations,
            "function": functions,
            "stringTable": string_table,
            "timeNanos": int(profile.timestamp.timestamp() * 1e9),
            "durationNanos": profile.duration_ns,
        }
