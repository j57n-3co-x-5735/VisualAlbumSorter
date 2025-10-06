#!/usr/bin/env python3
"""
Provider management utilities for AI photo sorter.

This script provides utilities for managing AI providers like Ollama,
including installation checks and cleanup operations.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def run_command(command, check=False):
    """Execute a shell command.
    
    Args:
        command: Command to execute
        check: Whether to check for errors
        
    Returns:
        Command result
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            capture_output=True, 
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error executing command: {e}")
        return None


def check_provider_status(provider_type):
    """Check status of a provider.
    
    Args:
        provider_type: Type of provider to check
    """
    print(f"\nChecking {provider_type} status...")
    print("-" * 40)
    
    if provider_type == "ollama":
        # Check if Ollama is installed
        ollama_app = Path("/Applications/Ollama.app")
        ollama_cli = Path("/usr/local/bin/ollama")
        
        if ollama_app.exists():
            print("✓ Ollama.app found")
        else:
            print("✗ Ollama.app not found")
        
        if ollama_cli.exists():
            print("✓ Ollama CLI found")
            
            # Check if server is running
            result = run_command("curl -s http://127.0.0.1:11434/api/tags")
            if result and result.returncode == 0:
                print("✓ Ollama server is running")
                
                # List models
                try:
                    import json
                    models = json.loads(result.stdout).get("models", [])
                    if models:
                        print(f"✓ Models available: {', '.join(m['name'] for m in models)}")
                    else:
                        print("✗ No models installed")
                except:
                    pass
            else:
                print("✗ Ollama server not running (start with: ollama serve)")
        else:
            print("✗ Ollama CLI not found")
    
    elif provider_type == "lm_studio":
        # Check if LM Studio is installed
        lm_studio_app = Path("/Applications/LM Studio.app")
        
        if lm_studio_app.exists():
            print("✓ LM Studio.app found")
        else:
            print("✗ LM Studio.app not found")
        
        # Check if server is running
        result = run_command("curl -s http://localhost:1234/v1/models")
        if result and result.returncode == 0:
            print("✓ LM Studio server is running")
        else:
            print("✗ LM Studio server not running")
    
    elif provider_type == "mlx_vlm":
        # Check if MLX VLM is installed
        result = run_command("pip show mlx-vlm", check=False)
        if result and result.returncode == 0:
            print("✓ MLX VLM package installed")
        else:
            print("✗ MLX VLM package not installed")
        
        # Check if server is running
        result = run_command("curl -s http://127.0.0.1:8000")
        if result and result.returncode == 0:
            print("✓ MLX VLM server is running")
        else:
            print("✗ MLX VLM server not running")


def uninstall_ollama():
    """Complete uninstallation of Ollama from macOS."""
    print("\nStarting complete uninstallation of Ollama...")
    print("=" * 50)
    
    # Check for root privileges
    if os.geteuid() != 0:
        print("⚠ Warning: This operation needs sudo privileges.")
        print("Please run: sudo python3 manage_providers.py --uninstall-ollama")
        return 1
    
    # Stop Ollama processes
    print("\n[1/4] Stopping Ollama processes...")
    run_command("pkill -f 'ollama'")
    print("  ✓ Stopped all Ollama processes")
    
    # Define paths to remove
    user_home = Path.home()
    paths_to_remove = [
        Path("/Applications/Ollama.app"),
        Path("/usr/local/bin/ollama"),
        user_home / ".ollama",
        user_home / "Library/Application Support/Ollama",
        user_home / "Library/Caches/com.ollama",
        user_home / "Library/Preferences/com.ollama.plist",
    ]
    
    # Remove files and directories
    print("\n[2/4] Removing Ollama files and directories...")
    for path in paths_to_remove:
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"  ✓ Removed directory: {path}")
                else:
                    path.unlink()
                    print(f"  ✓ Removed file: {path}")
            except Exception as e:
                print(f"  ✗ Error removing {path}: {e}")
    
    # Remove LaunchAgents and LaunchDaemons
    print("\n[3/4] Removing LaunchAgents and LaunchDaemons...")
    launch_dirs = [
        user_home / "Library/LaunchAgents",
        Path("/Library/LaunchAgents"),
        Path("/Library/LaunchDaemons"),
    ]
    
    for directory in launch_dirs:
        if directory.exists():
            for file in directory.glob("*ollama*"):
                try:
                    file.unlink()
                    print(f"  ✓ Removed: {file}")
                except Exception as e:
                    print(f"  ✗ Error removing {file}: {e}")
    
    # Verify uninstallation
    print("\n[4/4] Verifying uninstallation...")
    if not Path("/usr/local/bin/ollama").exists() and not Path("/Applications/Ollama.app").exists():
        print("  ✓ Ollama successfully uninstalled")
    else:
        print("  ⚠ Some Ollama components may still exist")
    
    print("\n" + "=" * 50)
    print("Uninstallation complete.")
    print("Please restart your Mac to clear 'Allow in background' entries.")
    
    return 0


def install_instructions(provider_type):
    """Show installation instructions for a provider.
    
    Args:
        provider_type: Type of provider
    """
    print(f"\nInstallation instructions for {provider_type}:")
    print("=" * 50)
    
    if provider_type == "ollama":
        print("""
1. Download Ollama:
   Visit: https://ollama.ai/download
   
2. Install the application:
   Open the downloaded .dmg file and drag to Applications
   
3. Start Ollama:
   Launch Ollama.app from Applications
   
4. Install a vision model:
   ollama pull qwen2.5vl:3b
   
5. Verify installation:
   ollama list
        """)
    
    elif provider_type == "lm_studio":
        print("""
1. Download LM Studio:
   Visit: https://lmstudio.ai
   
2. Install the application:
   Open the downloaded .dmg file and drag to Applications
   
3. Launch LM Studio and download a vision model:
   - Open LM Studio.app
   - Search for "qwen2.5-omni" or another vision model
   - Download the model
   
4. Start the server:
   - Go to the "Server" tab in LM Studio
   - Load your model
   - Click "Start Server"
        """)
    
    elif provider_type == "mlx_vlm":
        print("""
1. Install MLX VLM (requires Apple Silicon):
   pip install mlx-vlm
   
2. Start the server with a model:
   mlx_vlm.server --model mlx-community/Phi-3-vision-128k-instruct-4bit
   
3. The server will start on http://127.0.0.1:8000
        """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Provider management utilities for AI photo sorter'
    )
    
    parser.add_argument(
        '--check',
        choices=['ollama', 'lm_studio', 'mlx_vlm', 'all'],
        help='Check status of specified provider'
    )
    
    parser.add_argument(
        '--install-help',
        choices=['ollama', 'lm_studio', 'mlx_vlm'],
        help='Show installation instructions for provider'
    )
    
    parser.add_argument(
        '--uninstall-ollama',
        action='store_true',
        help='Completely uninstall Ollama (requires sudo)'
    )
    
    args = parser.parse_args()
    
    if not any([args.check, args.install_help, args.uninstall_ollama]):
        parser.print_help()
        return 1
    
    if args.check:
        if args.check == 'all':
            for provider in ['ollama', 'lm_studio', 'mlx_vlm']:
                check_provider_status(provider)
        else:
            check_provider_status(args.check)
    
    if args.install_help:
        install_instructions(args.install_help)
    
    if args.uninstall_ollama:
        return uninstall_ollama()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())