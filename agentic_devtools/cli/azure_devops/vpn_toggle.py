"""
VPN toggle utilities for Ivanti Secure Access Client (formerly Pulse Secure).

Provides functions to detect VPN status, corporate network connectivity, and
temporarily disconnect/reconnect when operations need direct internet access
(e.g., fetching Azure DevOps logs, accessing npm registry).

Supports three connection scenarios:
1. Resume: VPN was suspended → use pulselauncher -resume
2. Auto-connect: VPN fully disconnected → use UI automation to click Connect button
3. Fallback: If UI automation fails → open GUI for manual connection
"""

import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

# Path to pulselauncher.exe - the CLI tool for Pulse Secure/Ivanti
PULSE_LAUNCHER_PATH = Path(r"C:\Program Files (x86)\Common Files\Pulse Secure\Integration\pulselauncher.exe")

# Path to Pulse.exe GUI client
PULSE_GUI_PATH = Path(r"C:\Program Files (x86)\Common Files\Pulse Secure\JamUI\Pulse.exe")

# Default VPN URL (can be overridden via state)
DEFAULT_VPN_URL = "https://portal.swica.ch/pulse"

# Internal host used to detect corporate network (only accessible via VPN or in-office)
# dragonfly.swica.ch returns 403 when on corporate network, unreachable otherwise
CORPORATE_NETWORK_TEST_HOST = "dragonfly.swica.ch"

# Timeout for VPN operations
VPN_OPERATION_TIMEOUT_SECONDS = 30


class NetworkStatus(Enum):
    """Network status for external access checks."""

    EXTERNAL_ACCESS_OK = "external_access_ok"  # Can reach external resources
    VPN_CONNECTED = "vpn_connected"  # VPN is on, blocking external access
    CORPORATE_NETWORK_NO_VPN = "corporate_network_no_vpn"  # In office without VPN
    UNKNOWN = "unknown"  # Reserved for future edge cases (e.g., partial connectivity)


def is_pulse_secure_installed() -> bool:
    """Check if Pulse Secure/Ivanti client is installed."""
    return PULSE_LAUNCHER_PATH.exists()


def _get_pulse_window_handle() -> Optional[int]:  # pragma: no cover
    """
    Get the window handle for the Pulse GUI if it's running.

    The Pulse process has multiple windows. We need to find the main GUI window
    which has class 'JamShadowClass', not the message-only window 'JamPostMessageWindow'
    that MainWindowHandle often points to.

    Returns:
        Window handle (HWND) as int, or None if not found.
    """
    try:
        # Find the JamShadowClass window which is the actual GUI
        # MainWindowHandle often points to JamPostMessageWindow which has no UI elements
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                """
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                using System.Text;
                public class PulseWindowFinder {
                    [DllImport("user32.dll")]
                    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
                    [DllImport("user32.dll")]
                    private static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
                    [DllImport("user32.dll", CharSet = CharSet.Auto)]
                    private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
                    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

                    public static IntPtr FindJamShadowWindow(int processId) {
                        IntPtr found = IntPtr.Zero;
                        EnumWindows((hWnd, lParam) => {
                            int pid;
                            GetWindowThreadProcessId(hWnd, out pid);
                            if (pid == processId) {
                                var className = new StringBuilder(256);
                                GetClassName(hWnd, className, 256);
                                if (className.ToString() == "JamShadowClass") {
                                    found = hWnd;
                                    return false; // Stop enumeration
                                }
                            }
                            return true;
                        }, IntPtr.Zero);
                        return found;
                    }
                }
"@
                $pulse = Get-Process -Name "Pulse" -ErrorAction SilentlyContinue
                if ($pulse) {
                    $hwnd = [PulseWindowFinder]::FindJamShadowWindow($pulse.Id)
                    [int64]$hwnd
                } else {
                    0
                }
                """,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            hwnd = int(result.stdout.strip())
            return hwnd if hwnd > 0 else None
    except (subprocess.TimeoutExpired, ValueError, Exception):
        pass
    return None


def _bring_window_to_foreground(hwnd: int) -> bool:  # pragma: no cover
    """
    Bring a window to the foreground using its handle.

    Args:
        hwnd: Window handle to bring to foreground

    Returns:
        True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                f"""
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class WindowHelper {{
                    [DllImport("user32.dll")]
                    public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    [DllImport("user32.dll")]
                    public static extern bool IsIconic(IntPtr hWnd);
                    public const int SW_RESTORE = 9;
                    public const int SW_SHOW = 5;
                }}
"@
                $hwnd = [IntPtr]{hwnd}
                # If minimized, restore first
                if ([WindowHelper]::IsIconic($hwnd)) {{
                    [WindowHelper]::ShowWindow($hwnd, [WindowHelper]::SW_RESTORE)
                }} else {{
                    [WindowHelper]::ShowWindow($hwnd, [WindowHelper]::SW_SHOW)
                }}
                Start-Sleep -Milliseconds 100
                [WindowHelper]::SetForegroundWindow($hwnd)
                """,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _launch_pulse_gui(bring_to_foreground: bool = False) -> bool:  # pragma: no cover
    """
    Launch the Pulse GUI client if not already running.

    Args:
        bring_to_foreground: If True and GUI is already running, bring it to foreground

    Returns:
        True if GUI is running (was already running or successfully launched), False otherwise.
    """
    if not PULSE_GUI_PATH.exists():
        return False

    # Check if already running
    hwnd = _get_pulse_window_handle()
    if hwnd:
        if bring_to_foreground:
            _bring_window_to_foreground(hwnd)
        return True

    # Launch the GUI
    try:
        subprocess.Popen([str(PULSE_GUI_PATH)], start_new_session=True)
        # Wait for window to appear
        for _ in range(10):  # Wait up to 5 seconds
            time.sleep(0.5)
            if _get_pulse_window_handle():
                return True
    except Exception:
        pass

    return False


def _click_connect_button_via_ui_automation() -> Tuple[bool, str]:  # pragma: no cover
    """
    Use Windows UI Automation to click the Connect button in Pulse GUI.

    This function:
    1. Ensures Pulse GUI is running (launches if needed)
    2. Uses UI Automation to find the "Connect" element
    3. Clicks it using mouse simulation (since InvokePattern isn't supported)

    Returns:
        Tuple of (success, message)
    """
    # Ensure GUI is running
    if not _launch_pulse_gui():
        return False, "Failed to launch Pulse GUI"

    # Use PowerShell for UI Automation - it's cleaner than trying to load .NET assemblies in Python
    ps_script = """
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    Add-Type -AssemblyName System.Windows.Forms

    # Add mouse click, window finding, and window visibility capability
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Text;
    public class WinHelper {
        [DllImport("user32.dll")]
        public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
        public const int MOUSEEVENTF_LEFTDOWN = 0x02;
        public const int MOUSEEVENTF_LEFTUP = 0x04;

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        [DllImport("user32.dll")]
        private static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);

        public const int SW_RESTORE = 9;
        public const int SW_SHOW = 5;
        public const int SW_SHOWNORMAL = 1;

        public static IntPtr FindJamShadowWindow(int processId) {
            IntPtr found = IntPtr.Zero;
            EnumWindows((hWnd, lParam) => {
                int pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (pid == processId) {
                    var className = new StringBuilder(256);
                    GetClassName(hWnd, className, 256);
                    if (className.ToString() == "JamShadowClass") {
                        found = hWnd;
                        return false;
                    }
                }
                return true;
            }, IntPtr.Zero);
            return found;
        }

        public static bool EnsureWindowVisible(IntPtr hWnd) {
            if (!IsWindowVisible(hWnd)) {
                ShowWindow(hWnd, SW_RESTORE);
                System.Threading.Thread.Sleep(500);
            }
            ShowWindow(hWnd, SW_SHOWNORMAL);
            SetForegroundWindow(hWnd);
            System.Threading.Thread.Sleep(500);
            return IsWindowVisible(hWnd);
        }
    }
"@

    $pulse = Get-Process -Name "Pulse" -ErrorAction SilentlyContinue
    if (-not $pulse) {
        Write-Output "ERROR:Pulse process not found"
        exit 1
    }

    # Find the JamShadowClass window (the actual GUI), not MainWindowHandle
    $hwnd = [WinHelper]::FindJamShadowWindow($pulse.Id)
    if ($hwnd -eq [IntPtr]::Zero) {
        Write-Output "ERROR:Pulse GUI window (JamShadowClass) not found"
        exit 1
    }

    # Ensure the window is visible and in foreground before trying UI automation
    $visible = [WinHelper]::EnsureWindowVisible($hwnd)
    if (-not $visible) {
        Write-Output "ERROR:Could not make Pulse window visible"
        exit 1
    }

    # Additional wait for UI Automation to enumerate elements after window becomes visible
    Start-Sleep -Milliseconds 500

    # Get the automation element for the window
    $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$hwnd)
    if (-not $root) {
        Write-Output "ERROR:Could not get automation element"
        exit 1
    }

    # Find the Connect button by name
    $nameCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "Connect"
    )
    $connectElement = $root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $nameCondition
    )

    if (-not $connectElement) {
        # Maybe it says "Disconnect" because already connected?
        $disconnectCondition = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty,
            "Disconnect"
        )
        $disconnectElement = $root.FindFirst(
            [System.Windows.Automation.TreeScope]::Descendants,
            $disconnectCondition
        )
        if ($disconnectElement) {
            Write-Output "ALREADY_CONNECTED"
            exit 0
        }
        Write-Output "ERROR:Connect button not found"
        exit 1
    }

    # Get bounding rectangle and click
    $rect = $connectElement.Current.BoundingRectangle
    if ($rect.Width -le 0 -or $rect.Height -le 0) {
        Write-Output "ERROR:Connect button has invalid bounds"
        exit 1
    }

    # Calculate center of button
    $clickX = [int]($rect.X + $rect.Width / 2)
    $clickY = [int]($rect.Y + $rect.Height / 2)

    # Move mouse and click
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($clickX, $clickY)
    Start-Sleep -Milliseconds 100
    [WinHelper]::mouse_event([WinHelper]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 50
    [WinHelper]::mouse_event([WinHelper]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    Write-Output "SUCCESS"
    """

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip()

        if "SUCCESS" in output:
            return True, "Connect button clicked via UI automation"
        elif "ALREADY_CONNECTED" in output:
            return True, "VPN appears to already be connected"
        elif "ERROR:" in output:
            error_msg = output.split("ERROR:")[-1].strip()
            return False, f"UI automation failed: {error_msg}"
        else:
            return False, f"UI automation returned unexpected output: {output}"

    except subprocess.TimeoutExpired:
        return False, "UI automation timed out"
    except Exception as e:
        return False, f"UI automation error: {e}"


def _run_pulse_command(args: list[str], timeout: int = VPN_OPERATION_TIMEOUT_SECONDS) -> Tuple[bool, str, int]:
    """
    Run a pulselauncher command.

    Args:
        args: Command arguments to pass to pulselauncher.exe
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, output_or_error, return_code)
        Return codes:
        - 0: Command succeeded
        - 999: No suspended session to resume (used by -resume when VPN is fully disconnected)
    """
    if not is_pulse_secure_installed():
        return False, "Pulse Secure/Ivanti not installed", -1

    try:
        result = subprocess.run(
            [str(PULSE_LAUNCHER_PATH)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        # pulselauncher often returns 0 even on errors, check output
        return result.returncode == 0, output.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s", -1
    except Exception as e:
        return False, str(e), -1


def is_vpn_connected() -> bool:
    """
    Check if VPN is currently connected.

    Uses multiple methods:
    1. Check if Junos Pulse virtual network adapter exists and is up
    2. Try to detect VPN by checking routing table for VPN-like routes
    3. Check if pulselauncher reports a connection

    Returns:
        True if VPN appears to be connected, False otherwise.
    """
    # Method 1: Check for Junos Pulse adapter via PowerShell
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-NetAdapter | Where-Object { "
                "$_.InterfaceDescription -like '*Junos*' -or "
                "$_.InterfaceDescription -like '*Pulse*' -or "
                "$_.InterfaceDescription -like '*Juniper*' "
                "} | Where-Object { $_.Status -eq 'Up' } | "
                "Measure-Object | Select-Object -ExpandProperty Count",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            count = result.stdout.strip()
            if count and int(count) > 0:
                return True
    except (subprocess.TimeoutExpired, ValueError, Exception):
        pass

    # Method 2: Check if internal corporate resources are reachable
    # This is a heuristic - if we can reach Azure DevOps, VPN might not be blocking
    # But some VPNs route everything, so this is not definitive
    # For now, we rely on Method 1 (network adapter check) as the authoritative source

    return False


def is_on_corporate_network(timeout_seconds: int = 3) -> bool:
    """
    Check if we're on the corporate network (in office or via VPN).

    Tests by trying to reach an internal-only host (dragonfly.swica.ch).
    - If we get 200/302 (success or redirect): ON corporate network
    - If we get 403 Forbidden: NOT on corporate network (external WAF blocking)
    - If unreachable/timeout: NOT on corporate network

    Args:
        timeout_seconds: Timeout for the connectivity check

    Returns:
        True if on corporate network, False otherwise.
    """
    try:
        # Use PowerShell to make a quick web request to internal host
        # We need to distinguish between:
        # - 403 Forbidden = external WAF blocking us = NOT on corporate network
        # - 200/302/etc = can access the app = ON corporate network
        # - Timeout/unreachable = NOT on corporate network
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                f"""
                try {{
                    $response = Invoke-WebRequest -Uri 'https://{CORPORATE_NETWORK_TEST_HOST}' `
                        -TimeoutSec {timeout_seconds} -UseBasicParsing -MaximumRedirection 0 `
                        -ErrorAction Stop
                    # Got 2xx response = on corporate network
                    'corporate'
                }} catch {{
                    if ($_.Exception.Response) {{
                        $statusCode = [int]$_.Exception.Response.StatusCode
                        if ($statusCode -eq 403) {{
                            # 403 Forbidden = external WAF blocking = NOT on corporate network
                            'external'
                        }} else {{
                            # Other HTTP errors (401, 500, etc.) = likely on corporate network
                            'corporate'
                        }}
                    }} else {{
                        # No response at all (timeout, DNS failure) = not on corporate network
                        'external'
                    }}
                }}
                """,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5,  # Add buffer for PowerShell startup
        )
        return "corporate" in result.stdout.lower()
    except (subprocess.TimeoutExpired, Exception):
        return False


def check_network_status(verbose: bool = False) -> Tuple[NetworkStatus, str]:
    """
    Check network status for external access (npm registry, Azure DevOps logs, etc.).

    This function checks VPN and corporate network status FIRST, avoiding
    slow timeout waits when we already know external access will be blocked.

    Returns:
        Tuple of (NetworkStatus, human-readable message)
    """
    # Check 1: Is VPN connected? (fast check via network adapter)
    if is_vpn_connected():
        msg = "VPN is connected - external access blocked (can be temporarily disconnected)"
        if verbose:
            print(f"  🔌 {msg}")
        return NetworkStatus.VPN_CONNECTED, msg

    # Check 2: Are we on corporate network without VPN? (in the office)
    if is_on_corporate_network():
        msg = (
            "On corporate network (in office) without VPN - external access blocked.\n"
            "  Unlike VPN, this cannot be toggled automatically.\n"
            "  Please connect to a different network (e.g., mobile hotspot) for external access."
        )
        if verbose:  # pragma: no cover
            print(f"  🏢 {msg}")
        return NetworkStatus.CORPORATE_NETWORK_NO_VPN, msg

    # If not on VPN and not on corporate network, external access should work
    if verbose:  # pragma: no cover
        print("  ✅ Not on VPN or corporate network - external access should work")
    return NetworkStatus.EXTERNAL_ACCESS_OK, "External access available"


def disconnect_vpn(
    url: str = DEFAULT_VPN_URL,
    max_wait_seconds: int = 15,
    check_interval: float = 1.0,
) -> Tuple[bool, str]:
    """
    Disconnect from VPN using suspend command.

    Waits for VPN to fully disconnect before returning.

    Args:
        url: VPN portal URL
        max_wait_seconds: Maximum time to wait for VPN to disconnect
        check_interval: Seconds between connection checks

    Returns:
        Tuple of (success, message)
    """
    if not is_pulse_secure_installed():
        return False, "Pulse Secure/Ivanti not installed"

    print(f"  ⏸️  Suspending VPN connection to {url}...")
    success, output, _ = _run_pulse_command(["-suspend", "-url", url])

    if not success:
        return False, f"Failed to suspend VPN: {output}"

    # Wait for VPN to fully disconnect
    print("  ⏳ Waiting for VPN to fully disconnect...")
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        time.sleep(check_interval)
        elapsed += check_interval
        if not is_vpn_connected():
            print(f"  ✅ VPN disconnected after {elapsed:.1f}s")
            return True, "VPN suspended and verified disconnected"
        print(f"  ... still connected ({elapsed:.1f}s)")

    # Timed out but command succeeded - proceed anyway
    print(  # pragma: no cover
        f"  ⚠️  VPN suspend command sent but adapter still shows connected after {max_wait_seconds}s"
    )
    return True, "VPN suspend sent (connection status unclear)"  # pragma: no cover


def reconnect_vpn(
    url: str = DEFAULT_VPN_URL,
    max_wait_seconds: int = 20,
    check_interval: float = 2.0,
) -> Tuple[bool, str]:
    """
    Reconnect to VPN using resume command.

    Waits for VPN to fully reconnect before returning.

    Args:
        url: VPN portal URL
        max_wait_seconds: Maximum time to wait for VPN to reconnect
        check_interval: Seconds between connection checks

    Returns:
        Tuple of (success, message)
    """
    if not is_pulse_secure_installed():
        return False, "Pulse Secure/Ivanti not installed"

    print(f"  ▶️  Resuming VPN connection to {url}...")
    success, output, _ = _run_pulse_command(["-resume", "-url", url])

    if not success:
        return False, f"Failed to resume VPN: {output}"

    # Wait for VPN to fully reconnect
    print("  ⏳ Waiting for VPN to reconnect...")
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        time.sleep(check_interval)
        elapsed += check_interval
        if is_vpn_connected():
            print(f"  ✅ VPN reconnected after {elapsed:.1f}s")
            return True, "VPN resumed and verified connected"
        print(f"  ... waiting for connection ({elapsed:.1f}s)")

    # Timed out but command succeeded - VPN may still be connecting
    print(  # pragma: no cover
        f"  ⚠️  VPN resume command sent but adapter not showing connected after {max_wait_seconds}s"
    )
    return True, "VPN resume sent (may still be connecting)"  # pragma: no cover


def connect_vpn(
    url: str = DEFAULT_VPN_URL,
    max_wait_seconds: int = 30,
    check_interval: float = 2.0,
) -> Tuple[bool, str]:
    """
    Connect to VPN when fully disconnected (not just suspended).

    Uses UI automation to click the Connect button in the Pulse GUI,
    which triggers the saved connection profile. Falls back to manual
    connection if UI automation fails.

    Args:
        url: VPN portal URL (shown for reference)
        max_wait_seconds: Maximum time to wait for VPN to connect
        check_interval: Seconds between connection checks

    Returns:
        Tuple of (success, message)
    """
    if not is_pulse_secure_installed():
        return False, "Pulse Secure/Ivanti not installed"

    print("  🔌 VPN fully disconnected - attempting automatic connection...")

    # Try UI automation first
    ui_success, ui_msg = _click_connect_button_via_ui_automation()

    if ui_success:
        if "already" in ui_msg.lower():
            # Already connected
            return True, "VPN already connected"

        print(f"  ✅ {ui_msg}")
        print("  ⏳ Waiting for VPN connection to establish...")

        # Wait for connection to establish
        elapsed = 0.0
        while elapsed < max_wait_seconds:
            time.sleep(check_interval)
            elapsed += check_interval
            if is_vpn_connected():
                print(f"  ✅ VPN connected after {elapsed:.1f}s")
                return True, "VPN connected via UI automation"
            print(f"  ... waiting for connection ({elapsed:.1f}s / {max_wait_seconds}s)")

        # Connection may still be establishing (auth, etc.)
        print(f"  ⚠️  VPN connect initiated but not confirmed after {max_wait_seconds}s")
        print("     Connection may still be in progress...")
        return True, "VPN connect initiated (may still be authenticating)"

    # UI automation failed - fall back to manual
    print(f"  ⚠️  UI automation failed: {ui_msg}")
    print("  📺 Opening VPN client for manual connection...")
    print(f"     Target URL: {url}")
    print("     ⏳ Please connect in the VPN client window...")

    # Ensure GUI is open and bring to foreground
    if not PULSE_GUI_PATH.exists():
        return False, "Pulse Secure GUI not found - please connect manually"

    # First try to bring existing window to foreground
    hwnd = _get_pulse_window_handle()
    if hwnd:
        _bring_window_to_foreground(hwnd)  # pragma: no cover
    else:  # pragma: no cover
        # Launch the GUI if not running
        try:
            subprocess.Popen([str(PULSE_GUI_PATH)], start_new_session=True)
            # Wait for window to appear and bring to foreground
            for _ in range(10):
                time.sleep(0.5)
                hwnd = _get_pulse_window_handle()
                if hwnd:
                    _bring_window_to_foreground(hwnd)
                    break
        except Exception as e:
            return False, f"Failed to open VPN client: {e}"

    # Wait for user to complete connection
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        time.sleep(check_interval)
        elapsed += check_interval
        if is_vpn_connected():
            print(f"  ✅ VPN connected after {elapsed:.1f}s")
            return True, "VPN connected successfully"
        print(f"  ... waiting for manual connection ({elapsed:.1f}s / {max_wait_seconds}s)")

    # Timed out
    print(f"  ⚠️  Timed out waiting for VPN connection after {max_wait_seconds}s")
    print("     Please complete connection in the VPN client window manually")
    return False, "Timed out waiting for manual VPN connection"


# Pulselauncher return codes indicating no suspended session to resume
# 999 = "No suspended session" (connect.swica.ch)
# 25 = "Invalid operation for current connection state" (portal.swica.ch/pulse)
# -1 = "Pulse is not running" (GUI/service not started)
PULSE_RETURN_CODES_NO_SUSPENDED_SESSION = {25, 999, -1}


def smart_connect_vpn(
    url: str = DEFAULT_VPN_URL,
    max_wait_seconds: int = 30,
    check_interval: float = 2.0,
) -> Tuple[bool, str]:
    """
    Smart VPN connection - detects state and routes to appropriate command.

    Uses pulselauncher return codes to determine VPN state:
    - Return codes -1, 25 or 999 from -resume mean no active/suspended session → use UI automation
    - Return code 0 from -resume means VPN was suspended → wait for resume to complete

    This avoids unnecessary waits by checking state first rather than
    blindly trying resume and waiting for timeout.

    Args:
        url: VPN portal URL
        max_wait_seconds: Maximum time to wait for VPN to connect
        check_interval: Seconds between connection checks

    Returns:
        Tuple of (success, message)
    """
    if not is_pulse_secure_installed():
        return False, "Pulse Secure/Ivanti not installed"

    # Check if VPN is already connected
    if is_vpn_connected():
        print("  ✅ VPN is already connected")
        return True, "VPN already connected"

    # Try resume to detect state - the return code tells us if there's a suspended session
    print("  🔍 Checking VPN state...")
    success, output, return_code = _run_pulse_command(["-resume", "-url", url], timeout=5)

    if return_code in PULSE_RETURN_CODES_NO_SUSPENDED_SESSION:
        # No suspended session or Pulse not running - need full connect via UI automation
        reason = "Pulse not running" if return_code == -1 else f"no suspended session (code {return_code})"
        print(f"  ℹ️  {reason} - starting full connection...")
        return connect_vpn(url, max_wait_seconds, check_interval)

    if return_code == 0:
        # Resume command was accepted - wait for connection
        print("  ▶️  Resuming suspended VPN session...")
        print("  ⏳ Waiting for VPN to reconnect...")
        elapsed = 0.0
        while elapsed < max_wait_seconds:
            time.sleep(check_interval)
            elapsed += check_interval
            if is_vpn_connected():
                print(f"  ✅ VPN resumed and connected after {elapsed:.1f}s")
                return True, "VPN resumed successfully"
            print(f"  ... waiting for connection ({elapsed:.1f}s)")  # pragma: no cover

        # Timed out - resume was accepted but connection not confirmed
        print(f"  ⚠️  VPN resume sent but not connected after {max_wait_seconds}s")  # pragma: no cover
        return True, "VPN resume sent (may still be connecting)"  # pragma: no cover

    # Unexpected return code - try full connect as fallback
    print(f"  ⚠️  Unexpected return code {return_code}, trying full connect...")
    return connect_vpn(url, max_wait_seconds, check_interval)


class VpnToggleContext:
    """
    Context manager for temporarily disconnecting VPN.

    Usage:
        with VpnToggleContext(auto_toggle=True) as vpn:
            # VPN is disconnected here if it was connected
            do_network_operation()
        # VPN is reconnected here if it was connected before

    The context manager tracks whether VPN was connected before
    and only reconnects if it was previously connected.
    """

    def __init__(
        self,
        auto_toggle: bool = False,
        vpn_url: str = DEFAULT_VPN_URL,
        verbose: bool = True,
    ):
        """
        Initialize VPN toggle context.

        Args:
            auto_toggle: If True, automatically disconnect/reconnect VPN.
                        If False, this context manager is a no-op.
            vpn_url: VPN portal URL for disconnect/reconnect commands.
            verbose: If True, print status messages.
        """
        self.auto_toggle = auto_toggle
        self.vpn_url = vpn_url
        self.verbose = verbose
        self.was_connected = False
        self.disconnected = False

    def __enter__(self) -> "VpnToggleContext":
        """Enter context - disconnect VPN if enabled and connected."""
        if not self.auto_toggle:
            return self

        if not is_pulse_secure_installed():
            if self.verbose:
                print("  ℹ️  Pulse Secure/Ivanti not installed, skipping VPN toggle")
            return self

        # Check if VPN is connected
        self.was_connected = is_vpn_connected()

        if self.was_connected:
            if self.verbose:  # pragma: no cover
                print("  🔌 VPN detected as connected, will temporarily disconnect...")
            success, msg = disconnect_vpn(self.vpn_url)
            if success:
                self.disconnected = True
                if self.verbose:  # pragma: no cover
                    print(f"  ✅ {msg}")
            else:
                if self.verbose:  # pragma: no cover
                    print(f"  ⚠️  {msg}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context - reconnect VPN if it was connected before."""
        if not self.auto_toggle:
            return False

        if self.disconnected:
            if self.verbose:  # pragma: no cover
                print("  🔌 Reconnecting VPN...")
            success, msg = reconnect_vpn(self.vpn_url)
            if self.verbose:  # pragma: no cover
                if success:
                    print(f"  ✅ {msg}")
                else:
                    print(f"  ⚠️  {msg}")

        # Don't suppress exceptions
        return False


def get_vpn_url_from_state() -> str:
    """Get VPN URL from state or use default."""
    try:
        from ...state import get_value

        url = get_value("vpn_url")
        return url if url else DEFAULT_VPN_URL
    except ImportError:  # pragma: no cover
        return DEFAULT_VPN_URL


class JiraVpnContext:
    """
    Context manager for ensuring VPN is connected during Jira API calls.

    This context manager:
    1. Checks if on corporate network (in office) - if so, no VPN action needed
    2. If at home with VPN off/suspended, connects VPN before Jira operations
    3. After Jira operations complete, suspends VPN if it was off before

    Usage:
        with JiraVpnContext() as vpn:
            # VPN is now connected (or on corporate network)
            make_jira_api_call()
        # VPN is suspended if it was off before

    This enables seamless Jira API access when working from home while
    minimizing the time spent with VPN active (which blocks external access).
    """

    def __init__(self, vpn_url: str = DEFAULT_VPN_URL, verbose: bool = True):
        """
        Initialize Jira VPN context.

        Args:
            vpn_url: VPN portal URL for connect/disconnect commands.
            verbose: If True, print status messages.
        """
        self.vpn_url = vpn_url
        self.verbose = verbose
        self.on_corporate_network = False
        self.vpn_was_off = False
        self.connected_vpn = False

    def __enter__(self) -> "JiraVpnContext":
        """Enter context - ensure VPN is connected or on corporate network."""
        # Check if on corporate network first (in office)
        if is_on_corporate_network():
            self.on_corporate_network = True
            if self.verbose:
                print("🏢 On corporate network (in office) - VPN not needed for Jira access")
            return self

        # Check if Pulse Secure is installed (needed for VPN operations at home)
        if not is_pulse_secure_installed():
            if self.verbose:
                print("⚠️  Pulse Secure/Ivanti not installed - proceeding without VPN management")
            return self

        # Check if VPN is already connected
        if is_vpn_connected():
            if self.verbose:
                print("🔌 VPN already connected - Jira access available")
            return self

        # VPN is off - need to connect for Jira access
        self.vpn_was_off = True
        if self.verbose:
            print("🔌 VPN is off - connecting for Jira API access...")

        success, msg = smart_connect_vpn(self.vpn_url)
        if success:
            self.connected_vpn = True
            if self.verbose:
                print(f"✅ {msg}")
        else:
            if self.verbose:
                print(f"⚠️  {msg}")
                print("   Jira API calls may fail without VPN connection")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context - suspend VPN if it was off before."""
        # If on corporate network, no VPN action needed
        if self.on_corporate_network:
            return False

        # If we connected VPN (it was off before), suspend it now
        if self.connected_vpn and self.vpn_was_off:
            if self.verbose:
                print("🔌 Suspending VPN (was off before Jira operations)...")
            success, msg = disconnect_vpn(self.vpn_url)
            if self.verbose:
                if success:
                    print(f"✅ {msg}")
                else:
                    print(f"⚠️  {msg}")  # pragma: no cover

        # Don't suppress exceptions
        return False


def ensure_jira_vpn_access(func):
    """
    Decorator to wrap a function with automatic VPN management for Jira API access.

    When applied to a function that makes Jira API calls, this decorator:
    1. Ensures VPN is connected (or on corporate network) before the function runs
    2. Restores VPN to its previous state after the function completes

    Usage:
        @ensure_jira_vpn_access
        def my_jira_function():
            # VPN is guaranteed to be available here
            make_jira_api_call()

    This decorator is safe to use even when:
    - Already on corporate network (no-op)
    - VPN is already connected (no-op)
    - Pulse Secure is not installed (proceeds without VPN management)
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        vpn_url = get_vpn_url_from_state()
        with JiraVpnContext(vpn_url=vpn_url, verbose=True):
            return func(*args, **kwargs)

    return wrapper


# CLI entry points for VPN toggle commands


def vpn_off_cmd() -> None:
    """
    CLI command to disconnect VPN.

    Usage:
        agdt-vpn-off

    Disconnects from VPN using the Pulse Secure/Ivanti suspend command.
    Waits for VPN to fully disconnect before returning.

    If on corporate network (physically in office) WITHOUT VPN, skips VPN adjustment
    since corporate network already provides internal resource access.
    """
    if not is_pulse_secure_installed():
        print("❌ Pulse Secure/Ivanti not installed")
        return

    # Check VPN FIRST - if VPN is connected, we should disconnect it
    # (regardless of whether corporate resources are reachable via VPN)
    if not is_vpn_connected():
        # VPN not connected - check if we're physically in the office
        if is_on_corporate_network():
            print("🏢 On corporate network (in office) - VPN adjustment not needed")
            print("   Internal resources are accessible via office network")
            return
        print("ℹ️  VPN is not currently connected")
        return

    vpn_url = get_vpn_url_from_state()
    success, msg = disconnect_vpn(vpn_url)

    if success:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")  # pragma: no cover


def vpn_on_cmd() -> None:
    """
    CLI command to connect VPN.

    Usage:
        agdt-vpn-on

    Connects to VPN using a smart approach:
    - First tries to resume (if VPN was suspended)
    - Falls back to full connect (if VPN was fully disconnected)

    Waits for VPN to fully connect before returning.

    If on corporate network (physically in office), skips VPN connection
    since corporate network already provides internal resource access.
    """
    # Check if on corporate network first (in office)
    if is_on_corporate_network():
        print("🏢 On corporate network (in office) - VPN not needed")
        print("   Internal resources are accessible via office network")
        return

    if not is_pulse_secure_installed():
        print("❌ Pulse Secure/Ivanti not installed")
        return

    if is_vpn_connected():
        print("ℹ️  VPN is already connected")
        return

    vpn_url = get_vpn_url_from_state()
    success, msg = smart_connect_vpn(vpn_url)

    if success:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")  # pragma: no cover


def vpn_status_cmd() -> None:
    """
    CLI command to check VPN and network status.

    Usage:
        agdt-vpn-status

    Reports current VPN connection status and network accessibility.
    """
    if not is_pulse_secure_installed():
        print("ℹ️  Pulse Secure/Ivanti not installed")
        print("   VPN toggle commands are not available")
        return

    status, msg = check_network_status(verbose=False)

    if status == NetworkStatus.VPN_CONNECTED:
        print("🔌 VPN is CONNECTED")
        print("   External access (npm, Azure DevOps logs) may be blocked")
        print("   Use 'agdt-vpn-off' to temporarily disconnect")
    elif status == NetworkStatus.CORPORATE_NETWORK_NO_VPN:
        print("🏢 On corporate network (in office) without VPN")
        print("   External access is blocked and cannot be toggled automatically")
        print("   Connect to a different network for external access")
    elif status == NetworkStatus.EXTERNAL_ACCESS_OK:
        print("✅ VPN is DISCONNECTED")
        print("   External access should be available")
        print("   Use 'agdt-vpn-on' to reconnect when done")
    else:
        print(f"❓ Network status: {status.value}")
        print(f"   {msg}")


# =============================================================================
# Async VPN Commands (Background Tasks)
# =============================================================================

# Module path for the sync VPN functions
_VPN_MODULE = "agentic_devtools.cli.azure_devops.vpn_toggle"


def vpn_off_async() -> None:
    """
    Disconnect VPN asynchronously in the background.

    Usage:
        agdt-vpn-off
        agdt-task-wait

    Disconnects from VPN using the Pulse Secure/Ivanti suspend command.
    The task runs in the background - use agdt-task-wait to wait for completion.

    If on corporate network (physically in office) WITHOUT VPN, skips VPN adjustment
    since corporate network already provides internal resource access.
    """
    from agentic_devtools.background_tasks import run_function_in_background
    from agentic_devtools.task_state import print_task_tracking_info

    task = run_function_in_background(
        _VPN_MODULE,
        "vpn_off_cmd",
        command_display_name="agdt-vpn-off",
    )
    print_task_tracking_info(task, "Disconnecting VPN")


def vpn_on_async() -> None:
    """
    Connect VPN asynchronously in the background.

    Usage:
        agdt-vpn-on
        agdt-task-wait

    Connects to VPN using a smart approach:
    - First tries to resume (if VPN was suspended)
    - Falls back to full connect (if VPN was fully disconnected)

    The task runs in the background - use agdt-task-wait to wait for completion.

    If on corporate network (physically in office), skips VPN connection
    since corporate network already provides internal resource access.
    """
    from agentic_devtools.background_tasks import run_function_in_background
    from agentic_devtools.task_state import print_task_tracking_info

    task = run_function_in_background(
        _VPN_MODULE,
        "vpn_on_cmd",
        command_display_name="agdt-vpn-on",
    )
    print_task_tracking_info(task, "Connecting VPN")


def vpn_status_async() -> None:
    """
    Check VPN and network status asynchronously in the background.

    Usage:
        agdt-vpn-status
        agdt-task-wait

    Reports current VPN connection status and network accessibility.
    The task runs in the background - use agdt-task-wait to wait for completion.
    """
    from agentic_devtools.background_tasks import run_function_in_background
    from agentic_devtools.task_state import print_task_tracking_info

    task = run_function_in_background(
        _VPN_MODULE,
        "vpn_status_cmd",
        command_display_name="agdt-vpn-status",
    )
    print_task_tracking_info(task, "Checking VPN status")
