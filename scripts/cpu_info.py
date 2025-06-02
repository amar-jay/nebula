#!/usr/bin/env python3
# filepath: thread_info.py

import os
import threading
import time

import psutil  # You might need to install this: pip install psutil


def get_thread_info():
    # Get current active threads in this process
    active_threads = threading.active_count()

    # Get available CPU cores/logical processors
    available_processors = os.cpu_count()

    # Get system-wide thread count (all processes)
    system_threads = len(psutil.Process().threads())

    # Calculate usage percentage based on this process
    usage_percentage = (
        (active_threads / available_processors) * 100 if available_processors else 0
    )

    print(f"Active threads in current process: {active_threads}")
    print(f"Available logical processors: {available_processors}")
    print(f"System thread count for this process: {system_threads}")
    print(f"Thread usage percentage: {usage_percentage:.2f}%")


def get_system_thread_info():
    total_threads = 0
    active_processes = 0

    # CPU usage snapshot
    psutil.cpu_percent(interval=None)
    # Wait a moment to get meaningful CPU readings
    time.sleep(0.1)

    # Get all processes and analyze their activity
    for proc in psutil.process_iter(["pid", "name", "num_threads", "cpu_percent"]):
        try:
            # Update CPU percentage for this process
            proc_cpu = proc.cpu_percent(interval=0)
            total_threads += proc.info["num_threads"]

            # Consider a process active if it's using CPU
            if proc_cpu > 0.1:  # Using a small threshold to identify active processes
                active_processes += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Estimate active threads (roughly proportional to CPU usage)
    cpu_usage = psutil.cpu_percent()
    cpu_count = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)

    # Estimate active threads based on CPU usage
    active_threads_estimate = int((cpu_usage / 100) * cpu_count)

    print(f"Total system threads: {total_threads}")
    print(f"Active processes (using CPU): {active_processes}")
    print(f"Estimated active threads: {active_threads_estimate}")
    print(f"CPU Usage: {cpu_usage:.2f}%")
    print(f"Available physical CPU cores: {physical_cores}")
    print(f"Available logical CPU threads: {cpu_count}")
    print(f"System thread saturation: {(total_threads / cpu_count):.2f}x")


if __name__ == "__main__":
    print("=== Process Thread Information ===")
    get_thread_info()
    print("\n=== System-wide Thread Information ===")
    get_system_thread_info()
