import socket
import json
import time
import subprocess
import requests
import concurrent.futures
from PyQt6.QtCore import QThread, pyqtSignal
import config

def get_default_gateways():
    """Retrieve default gateway IPs from ipconfig (handles hotspot tethering gateway detection)."""
    gateways = ["127.0.0.1"] # Always fallback/probe localhost for simulation
    try:
        output = subprocess.check_output("ipconfig", shell=True, text=True, errors="ignore")
        for line in output.splitlines():
            if "Default Gateway" in line or "Gateway" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    gw = parts[1].strip()
                    # Filter out IPv6 addresses and empty configurations
                    if gw and not gw.startswith("0.0.0.0") and "." in gw:
                        gateways.append(gw)
    except Exception as e:
        print(f"[Discovery] Failed to query default gateways: {e}")
    return list(set(gateways))

def get_local_subnet_prefix():
    """Returns local subnet prefix (e.g., '192.168.100.') or None."""
    ip = "127.0.0.1"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        pass
    finally:
        s.close()
    
    if ip != "127.0.0.1" and "." in ip:
        parts = ip.split(".")
        return ".".join(parts[:3]) + "."
    return None

def check_ip_port(ip, port):
    """Probes a single IP address to see if it is our FastAPI receiver."""
    try:
        # Fast socket connection check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2) # Short timeout for speed
        res = sock.connect_ex((ip, port))
        sock.close()
        
        if res == 0:
            # If port is open, query the endpoint to confirm it's our app
            url = f"http://{ip}:{port}/storage"
            resp = requests.get(url, timeout=0.4)
            if resp.status_code == 200:
                data = resp.json()
                if "total_gb" in data:
                    return ip
    except Exception:
        pass
    return None

def scan_active_subnet(prefix, port):
    """Scans all 254 IP addresses in the subnet prefix concurrently."""
    ips = [f"{prefix}{i}" for i in range(1, 255)]
    # Use ThreadPoolExecutor to check IPs concurrently in parallel threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
        futures = {executor.submit(check_ip_port, ip, port): ip for ip in ips}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                return res
    return None

class NetworkDiscoveryListener(QThread):
    # Signals to communicate with the main UI thread
    device_found = pyqtSignal(str, int, str)  # IP, Port, Device Name
    device_lost = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = False
        self.connected_device = None
        self.last_seen = 0
        self.timeout_threshold = 5.0 # Seconds before declaring device offline

    def run(self):
        self.running = True
        
        # Setup UDP socket for broadcast beacons
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            sock.bind(('', config.UDP_DISCOVERY_PORT))
        except Exception:
            pass
            
        sock.settimeout(0.5)
        print(f"[Discovery] Auto-discovery active (UDP, Gateway probing, and Subnet scanning).")
        
        last_gateway_probe = 0
        last_subnet_scan = 0
        
        while self.running:
            now = time.time()
            
            # --- LAYER A: Probe Gateway IPs (Tethering Hotspot Bypass) ---
            if not self.connected_device and (now - last_gateway_probe >= 3.0):
                last_gateway_probe = now
                gateways = get_default_gateways()
                for gw in gateways:
                    res = check_ip_port(gw, config.DEFAULT_FASTAPI_PORT)
                    if res and not self.connected_device:
                        name = f"Android Phone ({res})" if res != "127.0.0.1" else "Local Simulator"
                        print(f"[Discovery] Discovered phone via gateway probe: {res}")
                        self.device_found.emit(res, config.DEFAULT_FASTAPI_PORT, name)
                        self.connected_device = (res, config.DEFAULT_FASTAPI_PORT)
                        self.last_seen = now
                        break

            # --- LAYER B: Active Subnet Scan (AP Isolation Wi-Fi Router Bypass) ---
            if not self.connected_device and (now - last_subnet_scan >= 8.0):
                last_subnet_scan = now
                prefix = get_local_subnet_prefix()
                if prefix:
                    # Scan the entire /24 subnet prefix concurrently in less than 2 seconds
                    found_ip = scan_active_subnet(prefix, config.DEFAULT_FASTAPI_PORT)
                    if found_ip and not self.connected_device:
                        name = f"Android Phone ({found_ip})"
                        print(f"[Discovery] Discovered phone via active subnet scan: {found_ip}")
                        self.device_found.emit(found_ip, config.DEFAULT_FASTAPI_PORT, name)
                        self.connected_device = (found_ip, config.DEFAULT_FASTAPI_PORT)
                        self.last_seen = now

            # --- LAYER C: Listen for UDP Broadcast Beacons (Standard Wi-Fi Router) ---
            try:
                if sock.fileno() != -1:
                    data, addr = sock.recvfrom(1024)
                    try:
                        payload = json.loads(data.decode('utf-8'))
                        device_ip = payload.get("ip")
                        device_port = payload.get("port", config.DEFAULT_FASTAPI_PORT)
                        device_name = payload.get("device_name", "Android Phone")
                        
                        if not device_ip or device_ip == "127.0.0.1":
                            device_ip = addr[0]
                            
                        # If not connected, or IP changed
                        if not self.connected_device or self.connected_device != (device_ip, device_port):
                            print(f"[Discovery] Discovered device via UDP beacon: {device_name} at {device_ip}:{device_port}")
                            self.device_found.emit(device_ip, device_port, device_name)
                            self.connected_device = (device_ip, device_port)
                            
                        self.last_seen = now
                    except Exception:
                        pass
            except socket.timeout:
                pass
            except Exception:
                if sock.fileno() == -1:
                    time.sleep(0.5)

            # --- LAYER D: Keep-alive Pings & Heartbeat ---
            if self.connected_device:
                # Periodically ping the active server to refresh the connection timestamp
                if now - self.last_seen >= 1.5:
                    ip, port = self.connected_device
                    res = check_ip_port(ip, port)
                    if res:
                        self.last_seen = now
                
                # If no successful ping or beacon updates self.last_seen, trigger timeout
                if now - self.last_seen > self.timeout_threshold:
                    print(f"[Discovery] Device connection timed out: {self.connected_device[0]}")
                    self.device_lost.emit()
                    self.connected_device = None
                    last_gateway_probe = 0
                    last_subnet_scan = 0
                    
        sock.close()
        print("[Discovery] Discovery listener stopped.")

    def stop(self):
        self.running = False
        self.wait()
