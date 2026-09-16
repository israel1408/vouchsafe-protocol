import time
import logging
import aiohttp

logger = logging.getLogger("vouchsafe.verifier")

async def verify_host_node(host_endpoint: str):
    """
    Verifies host node endpoint availability, status codes, and latency response.
    Returns a tuple of (is_valid: bool, report: str).
    """
    if not host_endpoint.startswith(("http://", "https://")):
        host_endpoint = f"https://{host_endpoint}"

    start_time = time.perf_counter()

    try:
        timeout = aiohttp.ClientTimeout(total=8.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(host_endpoint) as response:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                
                if response.status in [200, 201, 204]:
                    report = (
                        f"HTTP Status: {response.status} OK\n"
                        f"Target Endpoint: {host_endpoint}\n"
                        f"Response Latency: {latency_ms}ms\n"
                        f"Node Compliance: VERIFIED"
                    )
                    return True, report
                else:
                    report = (
                        f"HTTP Status: {response.status}\n"
                        f"Target Endpoint: {host_endpoint}\n"
                        f"Response Latency: {latency_ms}ms\n"
                        f"Compliance Check: FAILED (Expected 200 OK)"
                    )
                    return False, report
    except Exception as e:
        logger.error(f"Host node verification error for {host_endpoint}: {e}")
        report = (
            f"Target Endpoint: {host_endpoint}\n"
            f"Connection State: UNREACHABLE\n"
            f"Error Details: {str(e)}"
        )
        return False, report
