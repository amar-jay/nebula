#!/usr/bin/env python3
"""
Memory monitoring utility for ZMQ server
"""

import gc
import os
import psutil
import logging
from typing import Dict, Optional

logger = logging.getLogger("memory-monitor")

class MemoryMonitor:
    """Simple memory monitoring utility"""
    
    def __init__(self, process_name: str = "zmq_server"):
        self.process_name = process_name
        self.last_memory_mb = 0
        self.peak_memory_mb = 0
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            rss_mb = memory_info.rss / 1024 / 1024  # Resident Set Size in MB
            vms_mb = memory_info.vms / 1024 / 1024  # Virtual Memory Size in MB
            
            # Update peak memory
            if rss_mb > self.peak_memory_mb:
                self.peak_memory_mb = rss_mb
                
            return {
                "rss_mb": rss_mb,
                "vms_mb": vms_mb,
                "peak_mb": self.peak_memory_mb,
                "cpu_percent": process.cpu_percent()
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def log_memory_usage(self) -> None:
        """Log current memory usage"""
        usage = self.get_memory_usage()
        if usage:
            rss_mb = usage.get("rss_mb", 0)
            peak_mb = usage.get("peak_mb", 0)
            cpu_percent = usage.get("cpu_percent", 0)
            
            # Calculate memory change
            memory_change = rss_mb - self.last_memory_mb
            change_indicator = "📈" if memory_change > 10 else "📉" if memory_change < -10 else "➡️"
            
            logger.info(
                f"Memory: {rss_mb:.1f}MB {change_indicator} "
                f"(Peak: {peak_mb:.1f}MB, CPU: {cpu_percent:.1f}%)"
            )
            
            # Warning if memory is growing too much
            if memory_change > 50:
                logger.warning(f"Memory increased by {memory_change:.1f}MB - potential leak!")
            
            self.last_memory_mb = rss_mb
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return stats"""
        before = self.get_memory_usage().get("rss_mb", 0)
        
        # Force garbage collection
        collected = gc.collect()
        
        after = self.get_memory_usage().get("rss_mb", 0)
        freed_mb = before - after
        
        stats = {
            "objects_collected": collected,
            "memory_freed_mb": freed_mb,
            "before_mb": before,
            "after_mb": after
        }
        
        if freed_mb > 1:  # Only log if significant memory was freed
            logger.info(f"GC: Freed {freed_mb:.1f}MB, collected {collected} objects")
        
        return stats
    
    def check_memory_threshold(self, threshold_mb: float = 500) -> bool:
        """Check if memory usage exceeds threshold"""
        usage = self.get_memory_usage()
        current_mb = usage.get("rss_mb", 0)
        
        if current_mb > threshold_mb:
            logger.warning(
                f"Memory usage ({current_mb:.1f}MB) exceeds threshold ({threshold_mb}MB)!"
            )
            return True
        return False
