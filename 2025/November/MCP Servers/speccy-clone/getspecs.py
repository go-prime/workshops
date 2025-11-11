from datetime import datetime
import platform
import psutil
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any


mcp = FastMCP(
    name="System_Monitor_Server",
)


def get_size(bytes_val, suffix="B"):
    """Convert bytes to human-readable format"""
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f}{unit}{suffix}"
        bytes_val /= 1024
    return f"{bytes_val:.2f}P{suffix}"


def get_system_specs() -> Dict[str, Any]:
    """Gather comprehensive system specifications"""
    specs = {}

    # System Info
    uname = platform.uname()
    specs['System'] = uname.system
    specs['Node_Name'] = uname.node
    specs['Release'] = uname.release
    specs['Machine'] = uname.machine
    specs['Processor'] = uname.processor

    # Boot Time
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    specs['Boot_Time'] = bt.strftime("%Y-%m-%d %H:%M:%S")

    # CPU Info
    specs['CPU_Cores_Physical'] = psutil.cpu_count(logical=False)
    specs['CPU_Cores_Total'] = psutil.cpu_count(logical=True)
    specs['CPU_Usage_Total'] = f"{psutil.cpu_percent(interval=1)}%"

    # Memory Info
    svmem = psutil.virtual_memory()
    specs['Memory_Total'] = get_size(svmem.total)
    specs['Memory_Available'] = get_size(svmem.available)
    specs['Memory_Used'] = get_size(svmem.used)
    specs['Memory_Used_Percent'] = f"{svmem.percent}%"

    # Disk Info
    disk_info = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                'Device': partition.device,
                'Mountpoint': partition.mountpoint,
                'Filesystem': partition.fstype,
                'Total': get_size(usage.total),
                'Used': get_size(usage.used),
                'Free': get_size(usage.free),
                'Percent': f"{usage.percent}%"
            })
        except (PermissionError, OSError):
            continue
    specs['Disk_Partitions'] = disk_info
    
    return specs


@mcp.tool()
def get_current_system_metrics() -> Dict[str, Any]:
    """
    Retrieves comprehensive system metrics including:
    - System information (OS, hostname, processor)
    - CPU usage and core count
    - Memory usage statistics
    - Disk partition information and usage
    """
    return get_system_specs()