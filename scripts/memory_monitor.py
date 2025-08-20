#!/usr/bin/env python3
"""
Memory stress test and monitoring for ZMQ server
"""

import sys
import time

import psutil


def monitor_process_memory(process_name: str = "python", duration: int = 300):
    """Monitor memory usage of a process for a specified duration"""

    print(f"🔍 Monitoring memory usage for processes containing '{process_name}'...")
    print(f"📊 Duration: {duration} seconds")
    print("=" * 60)

    start_time = time.time()
    max_memory = 0
    max_memory_time = 0
    samples = []

    try:
        while time.time() - start_time < duration:
            current_time = time.time() - start_time

            # Find processes matching the name
            matching_processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "memory_info", "cpu_percent"]
            ):
                try:
                    if process_name.lower() in proc.info["name"].lower() or any(
                        process_name.lower() in arg.lower()
                        for arg in proc.info["cmdline"]
                    ):
                        matching_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not matching_processes:
                print(f"⚠️  No processes found matching '{process_name}'")
                time.sleep(5)
                continue

            total_memory_mb = 0
            total_cpu = 0

            for proc in matching_processes:
                try:
                    memory_mb = proc.info["memory_info"].rss / 1024 / 1024
                    cpu_percent = proc.info["cpu_percent"]
                    total_memory_mb += memory_mb
                    total_cpu += cpu_percent
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Track maximum memory usage
            if total_memory_mb > max_memory:
                max_memory = total_memory_mb
                max_memory_time = current_time

            # Store sample
            samples.append(
                {
                    "time": current_time,
                    "memory_mb": total_memory_mb,
                    "cpu_percent": total_cpu,
                    "process_count": len(matching_processes),
                }
            )

            # Print status every 10 seconds
            if len(samples) % 20 == 0:  # Every 10 seconds (0.5s intervals)
                memory_trend = (
                    "📈"
                    if len(samples) > 1 and total_memory_mb > samples[-2]["memory_mb"]
                    else "📉"
                )
                print(
                    f"⏰ {current_time:6.1f}s | "
                    f"💾 {total_memory_mb:7.1f}MB {memory_trend} | "
                    f"🔥 {total_cpu:5.1f}% CPU | "
                    f"📊 Peak: {max_memory:.1f}MB"
                )

            time.sleep(0.5)  # Sample every 0.5 seconds

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")

    # Print summary
    print("\n" + "=" * 60)
    print("📋 MEMORY MONITORING SUMMARY")
    print("=" * 60)

    if samples:
        initial_memory = samples[0]["memory_mb"]
        final_memory = samples[-1]["memory_mb"]
        memory_growth = final_memory - initial_memory

        print(f"📊 Initial Memory:    {initial_memory:.1f} MB")
        print(f"📊 Final Memory:      {final_memory:.1f} MB")
        print(f"📊 Peak Memory:       {max_memory:.1f} MB (at {max_memory_time:.1f}s)")
        print(f"📊 Memory Growth:     {memory_growth:+.1f} MB")

        # Memory leak detection
        if memory_growth > 100:
            print("🚨 POTENTIAL MEMORY LEAK DETECTED!")
        elif memory_growth > 50:
            print("⚠️  Significant memory growth detected")
        else:
            print("✅ Memory usage appears stable")

        # Calculate memory growth rate
        if len(samples) > 1:
            time_span = samples[-1]["time"] - samples[0]["time"]
            growth_rate = memory_growth / time_span * 60  # MB per minute
            print(f"📊 Growth Rate:       {growth_rate:+.2f} MB/minute")

        print(f"📊 Total Samples:     {len(samples)}")
        print(f"📊 Monitoring Duration: {samples[-1]['time']:.1f} seconds")
    else:
        print("❌ No data collected")


def main():
    if len(sys.argv) > 1:
        process_name = sys.argv[1]
    else:
        process_name = "zmq_server"

    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    else:
        duration = 300  # 5 minutes default

    print("🔬 ZMQ Server Memory Monitor")
    print(f"🎯 Target: {process_name}")
    print(f"⏱️  Duration: {duration}s")
    print("\nPress Ctrl+C to stop monitoring early\n")

    monitor_process_memory(process_name, duration)


if __name__ == "__main__":
    main()
