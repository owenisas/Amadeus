import sys, platform


def detect_os():
    # Try the descriptive name first
    name = platform.system()
    if name in ("Windows", "Linux", "Darwin"):
        return name

    # Fallback to sys.platform
    plat = sys.platform
    if plat.startswith("win"):
        return "Windows"
    elif plat.startswith("linux"):
        return "Linux"
    elif plat.startswith("darwin"):
        return "macOS"
    return f"Unknown ({plat})"


print("Host OS is:", detect_os())
