#!/usr/bin/env python3
"""
Verification and integrity checking tools for photo sorter.

This script provides tools to verify the state of processing,
check for inconsistencies, and diagnose issues.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from visualalbumsorter.core import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrityChecker:
    """Check integrity of processing state and data."""
    
    def __init__(self, config_path: Path = None):
        """Initialize integrity checker.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all integrity checks.
        
        Returns:
            Dictionary with check results
        """
        logger.info("=" * 60)
        logger.info("RUNNING INTEGRITY CHECKS")
        logger.info("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.task.name,
            'checks': {}
        }
        
        # Check state file
        logger.info("\n1. Checking state file...")
        results['checks']['state_file'] = self._check_state_file()
        
        # Check done file
        logger.info("\n2. Checking done file...")
        results['checks']['done_file'] = self._check_done_file()
        
        # Check for orphaned temp files
        logger.info("\n3. Checking for orphaned temp files...")
        results['checks']['temp_files'] = self._check_temp_files()
        
        # Check for state consistency
        logger.info("\n4. Checking state consistency...")
        results['checks']['consistency'] = self._check_consistency()
        
        # Check Photos library access
        logger.info("\n5. Checking Photos library access...")
        results['checks']['photos_library'] = self._check_photos_library()
        
        # Check album state
        logger.info("\n6. Checking album state...")
        results['checks']['album'] = self._check_album()
        
        # Generate summary
        results['summary'] = self._generate_summary()
        
        return results
    
    def _check_state_file(self) -> Dict[str, Any]:
        """Check state file integrity."""
        state_path = self.config.get_state_path()
        result = {'path': str(state_path), 'exists': False, 'valid': False}
        
        if not state_path.exists():
            self.warnings.append("State file does not exist (fresh start)")
            logger.warning("  ⚠ State file not found")
            return result
        
        result['exists'] = True
        
        try:
            with open(state_path) as f:
                state = json.load(f)
            
            result['valid'] = True
            result['data'] = {
                'last_index': state.get('last_index', 0),
                'batch_processed': state.get('batch_processed', 0),
                'matches_count': len(state.get('matches', [])),
                'errors': state.get('errors', 0)
            }
            
            logger.info(f"  ✓ State file valid")
            logger.info(f"    Last index: {result['data']['last_index']}")
            logger.info(f"    Batches processed: {result['data']['batch_processed']}")
            logger.info(f"    Matches found: {result['data']['matches_count']}")
            
            self.stats['state'] = result['data']
            
        except json.JSONDecodeError as e:
            self.issues.append(f"State file corrupted: {e}")
            logger.error(f"  ✗ State file corrupted: {e}")
            result['error'] = str(e)
        except Exception as e:
            self.issues.append(f"Error reading state file: {e}")
            logger.error(f"  ✗ Error reading state file: {e}")
            result['error'] = str(e)
        
        return result
    
    def _check_done_file(self) -> Dict[str, Any]:
        """Check done file integrity."""
        done_path = self.config.get_done_path()
        result = {'path': str(done_path), 'exists': False, 'valid': False}
        
        if not done_path.exists():
            self.warnings.append("Done file does not exist (no photos processed yet)")
            logger.warning("  ⚠ Done file not found")
            return result
        
        result['exists'] = True
        
        try:
            done_uuids = set()
            duplicates = []
            invalid_lines = []
            
            with open(done_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for valid UUID format (basic check)
                    if len(line) == 36 and line.count('-') == 4:
                        if line in done_uuids:
                            duplicates.append(line)
                        done_uuids.add(line)
                    else:
                        invalid_lines.append((line_num, line))
            
            result['valid'] = True
            result['data'] = {
                'total_uuids': len(done_uuids),
                'duplicates': len(duplicates),
                'invalid_lines': len(invalid_lines)
            }
            
            logger.info(f"  ✓ Done file valid")
            logger.info(f"    Total UUIDs: {len(done_uuids)}")
            
            if duplicates:
                self.warnings.append(f"Found {len(duplicates)} duplicate UUIDs in done file")
                logger.warning(f"    ⚠ Duplicates found: {len(duplicates)}")
            
            if invalid_lines:
                self.issues.append(f"Found {len(invalid_lines)} invalid lines in done file")
                logger.error(f"    ✗ Invalid lines: {len(invalid_lines)}")
                result['invalid_lines'] = invalid_lines[:10]  # Show first 10
            
            self.stats['done_uuids'] = done_uuids
            
        except Exception as e:
            self.issues.append(f"Error reading done file: {e}")
            logger.error(f"  ✗ Error reading done file: {e}")
            result['error'] = str(e)
        
        return result
    
    def _check_temp_files(self) -> Dict[str, Any]:
        """Check for orphaned temporary files."""
        temp_dir = self.config.storage.temp_dir
        result = {'path': str(temp_dir), 'exists': False}
        
        if not temp_dir.exists():
            logger.info("  ✓ No temp directory (clean state)")
            return result
        
        result['exists'] = True
        
        try:
            temp_files = list(temp_dir.glob("temp_*.jpg"))
            result['orphaned_files'] = len(temp_files)
            
            if temp_files:
                self.warnings.append(f"Found {len(temp_files)} orphaned temp files")
                logger.warning(f"  ⚠ Found {len(temp_files)} orphaned temp files")
                
                # Calculate total size
                total_size = sum(f.stat().st_size for f in temp_files)
                result['total_size_mb'] = total_size / (1024 * 1024)
                logger.warning(f"    Total size: {result['total_size_mb']:.1f} MB")
                
                # Show some examples
                result['examples'] = [f.name for f in temp_files[:5]]
            else:
                logger.info("  ✓ No orphaned temp files")
            
        except Exception as e:
            self.issues.append(f"Error checking temp files: {e}")
            logger.error(f"  ✗ Error checking temp files: {e}")
            result['error'] = str(e)
        
        return result
    
    def _check_consistency(self) -> Dict[str, Any]:
        """Check consistency between state and done files."""
        result = {'consistent': False}
        
        if 'state' not in self.stats or 'done_uuids' not in self.stats:
            logger.warning("  ⚠ Cannot check consistency (missing data)")
            return result
        
        state_data = self.stats['state']
        done_count = len(self.stats['done_uuids'])
        
        # Check if counts make sense
        expected_processed = state_data['last_index']
        
        if done_count < expected_processed:
            diff = expected_processed - done_count
            self.warnings.append(
                f"Done file has {done_count} UUIDs but state indicates "
                f"{expected_processed} photos processed (missing {diff})"
            )
            logger.warning(f"  ⚠ Possible missing entries in done file: {diff}")
            result['missing_entries'] = diff
        elif done_count > expected_processed:
            diff = done_count - expected_processed
            self.warnings.append(
                f"Done file has {done_count} UUIDs but state indicates "
                f"only {expected_processed} photos processed (extra {diff})"
            )
            logger.warning(f"  ⚠ Extra entries in done file: {diff}")
            result['extra_entries'] = diff
        else:
            logger.info("  ✓ State and done files are consistent")
            result['consistent'] = True
        
        return result
    
    def _check_photos_library(self) -> Dict[str, Any]:
        """Check Photos library accessibility."""
        result = {'accessible': False}
        
        try:
            import osxphotos
            db = osxphotos.PhotosDB()
            
            photo_count = len(db.photos())
            result['accessible'] = True
            result['photo_count'] = photo_count
            
            logger.info(f"  ✓ Photos library accessible")
            logger.info(f"    Total photos: {photo_count}")
            
            # Check processing progress
            if 'done_uuids' in self.stats:
                processed = len(self.stats['done_uuids'])
                remaining = photo_count - processed
                progress = (processed / photo_count * 100) if photo_count > 0 else 0
                
                result['progress'] = {
                    'processed': processed,
                    'remaining': remaining,
                    'percentage': f"{progress:.1f}%"
                }
                
                logger.info(f"    Progress: {progress:.1f}% ({processed}/{photo_count})")
                
                if remaining > 0:
                    logger.info(f"    Remaining: {remaining} photos")
            
        except ImportError:
            self.issues.append("osxphotos not installed")
            logger.error("  ✗ osxphotos not installed")
            result['error'] = "osxphotos not installed"
        except Exception as e:
            self.issues.append(f"Cannot access Photos library: {e}")
            logger.error(f"  ✗ Cannot access Photos library: {e}")
            result['error'] = str(e)
        
        return result
    
    def _check_album(self) -> Dict[str, Any]:
        """Check album state."""
        result = {'exists': False}
        album_name = self.config.album.name
        
        try:
            from photoscript import PhotosLibrary
            photos_lib = PhotosLibrary()
            
            for album in photos_lib.albums:
                if album.name == album_name:
                    result['exists'] = True
                    result['name'] = album_name
                    result['photo_count'] = len(album.photos())
                    
                    logger.info(f"  ✓ Album '{album_name}' exists")
                    logger.info(f"    Photos in album: {result['photo_count']}")
                    
                    # Compare with state file
                    if 'state' in self.stats:
                        expected_matches = self.stats['state']['matches_count']
                        if result['photo_count'] != expected_matches:
                            self.warnings.append(
                                f"Album has {result['photo_count']} photos but "
                                f"state indicates {expected_matches} matches"
                            )
                            logger.warning(
                                f"    ⚠ Mismatch: state shows {expected_matches} matches"
                            )
                    break
            else:
                logger.info(f"  ℹ Album '{album_name}' does not exist yet")
                
        except ImportError:
            self.issues.append("photoscript not installed")
            logger.error("  ✗ photoscript not installed")
            result['error'] = "photoscript not installed"
        except Exception as e:
            self.issues.append(f"Cannot check album: {e}")
            logger.error(f"  ✗ Cannot check album: {e}")
            result['error'] = str(e)
        
        return result
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of all checks."""
        logger.info("\n" + "=" * 60)
        logger.info("INTEGRITY CHECK SUMMARY")
        logger.info("=" * 60)
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'issues_count': len(self.issues),
            'warnings_count': len(self.warnings),
            'issues': self.issues,
            'warnings': self.warnings
        }
        
        if self.issues:
            logger.error(f"\n❌ Found {len(self.issues)} issues:")
            for issue in self.issues:
                logger.error(f"  - {issue}")
        else:
            logger.info("\n✓ No critical issues found")
        
        if self.warnings:
            logger.warning(f"\n⚠ Found {len(self.warnings)} warnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        logger.info("\n" + "=" * 60)
        
        return summary


def repair_state(config_path: Path = None, fix_duplicates: bool = False, 
                 clean_temp: bool = False):
    """Repair common state issues.
    
    Args:
        config_path: Path to configuration file
        fix_duplicates: Remove duplicate entries from done file
        clean_temp: Remove orphaned temp files
    """
    config = load_config(config_path)
    
    logger.info("=" * 60)
    logger.info("RUNNING STATE REPAIR")
    logger.info("=" * 60)
    
    if fix_duplicates:
        logger.info("\nRemoving duplicates from done file...")
        done_path = config.get_done_path()
        
        if done_path.exists():
            uuids = []
            seen = set()
            
            with open(done_path) as f:
                for line in f:
                    line = line.strip()
                    if line and line not in seen:
                        uuids.append(line)
                        seen.add(line)
            
            with open(done_path, 'w') as f:
                for uuid in uuids:
                    f.write(f"{uuid}\n")
            
            logger.info(f"  ✓ Removed {len(seen) - len(uuids)} duplicates")
    
    if clean_temp:
        logger.info("\nCleaning orphaned temp files...")
        temp_dir = config.storage.temp_dir
        
        if temp_dir.exists():
            temp_files = list(temp_dir.glob("temp_*.jpg"))
            
            for f in temp_files:
                f.unlink()
            
            logger.info(f"  ✓ Removed {len(temp_files)} temp files")
    
    logger.info("\n" + "=" * 60)
    logger.info("Repair complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify integrity of photo sorter state and data'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--repair',
        action='store_true',
        help='Attempt to repair common issues'
    )
    
    parser.add_argument(
        '--fix-duplicates',
        action='store_true',
        help='Remove duplicate entries from done file'
    )
    
    parser.add_argument(
        '--clean-temp',
        action='store_true',
        help='Remove orphaned temp files'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Save results to JSON file'
    )
    
    args = parser.parse_args()
    
    if args.repair or args.fix_duplicates or args.clean_temp:
        repair_state(
            args.config,
            fix_duplicates=args.fix_duplicates or args.repair,
            clean_temp=args.clean_temp or args.repair
        )
    
    # Run integrity checks
    checker = IntegrityChecker(args.config)
    results = checker.run_all_checks()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nResults saved to: {args.output}")
    
    # Return non-zero if issues found
    return len(results['summary']['issues'])


if __name__ == "__main__":
    sys.exit(main())