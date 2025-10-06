"""Diagnostics and debugging utilities for photo sorter."""

import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class PhotoStats:
    """Statistics for photo processing."""
    total_in_library: int = 0
    previously_processed: int = 0
    to_process: int = 0
    processed_this_session: int = 0
    matched_this_session: int = 0
    errors_this_session: int = 0
    skipped_this_session: int = 0
    
    # Detailed breakdowns
    skipped_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    processing_times: List[float] = field(default_factory=list)
    
    def get_average_processing_time(self) -> float:
        """Get average processing time per photo."""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def get_completion_percentage(self) -> float:
        """Get overall completion percentage.

        Includes both processed and skipped items this session to reflect
        total library coverage, not just classification attempts.
        """
        if self.total_in_library == 0:
            return 100.0
        covered_now = self.processed_this_session + self.skipped_this_session
        total_covered = self.previously_processed + covered_now
        return (total_covered / self.total_in_library) * 100
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary statistics."""
        return {
            'photos_in_library': self.total_in_library,
            'previously_processed': self.previously_processed,
            'needed_processing': self.to_process,
            'processed_this_session': self.processed_this_session,
            'matched_this_session': self.matched_this_session,
            'errors_this_session': self.errors_this_session,
            'skipped_this_session': self.skipped_this_session,
            'completion_percentage': f"{self.get_completion_percentage():.1f}%",
            'average_time_per_photo': f"{self.get_average_processing_time():.2f}s"
        }


@dataclass
class ProcessingEvent:
    """Single processing event for detailed tracking."""
    timestamp: datetime
    event_type: str  # 'start', 'photo_processed', 'batch_complete', 'error', 'complete'
    photo_uuid: Optional[str] = None
    batch_number: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


class DiagnosticsTracker:
    """Comprehensive diagnostics and progress tracking."""
    
    def __init__(self, config: 'Config', log_dir: Optional[Path] = None):
        """Initialize diagnostics tracker.
        
        Args:
            config: Application configuration
            log_dir: Directory for diagnostic logs
        """
        self.config = config
        self.stats = PhotoStats()
        self.events: List[ProcessingEvent] = []
        self.start_time = None
        self.end_time = None
        
        # Setup diagnostic log directory
        if log_dir:
            self.log_dir = log_dir
        else:
            self.log_dir = config.storage.temp_dir / "diagnostics"
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Diagnostic log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.diagnostic_file = self.log_dir / f"diagnostic_{timestamp}.json"
        
        logger.info(f"Diagnostics tracker initialized. Logging to: {self.diagnostic_file}")
    
    def start_processing(self, total_photos: int, already_processed: Set[str]):
        """Record processing start.
        
        Args:
            total_photos: Total photos in library
            already_processed: UUIDs of already processed photos
        """
        self.start_time = datetime.now()
        self.stats.total_in_library = total_photos
        self.stats.previously_processed = len(already_processed)
        self.stats.to_process = total_photos - len(already_processed)
        
        event = ProcessingEvent(
            timestamp=self.start_time,
            event_type='start',
            details={
                'total_photos': total_photos,
                'previously_processed': len(already_processed),
                'to_process': self.stats.to_process
            }
        )
        self.events.append(event)
        
        logger.info("=" * 60)
        logger.info("PROCESSING STARTED - DIAGNOSTIC INFO")
        logger.info("-" * 60)
        logger.info(f"Total photos in library: {total_photos}")
        logger.info(f"Previously processed: {len(already_processed)}")
        logger.info(f"Photos to process: {self.stats.to_process}")
        logger.info(f"Start time: {self.start_time}")
        logger.info("=" * 60)
        
        self._save_diagnostic_snapshot()
    
    def record_photo_processed(self, photo_uuid: str, result: str, 
                              processing_time: float, batch_num: Optional[int] = None):
        """Record a photo processing event.
        
        Args:
            photo_uuid: UUID of processed photo
            result: Processing result ('yes', 'no', 'error', 'skipped')
            processing_time: Time taken to process
            batch_num: Batch number if applicable
        """
        self.stats.processed_this_session += 1
        self.stats.processing_times.append(processing_time)
        
        if result == 'yes':
            self.stats.matched_this_session += 1
        elif result == 'error':
            self.stats.errors_this_session += 1
        elif result == 'skipped':
            self.stats.skipped_this_session += 1
        
        event = ProcessingEvent(
            timestamp=datetime.now(),
            event_type='photo_processed',
            photo_uuid=photo_uuid,
            batch_number=batch_num,
            details={
                'result': result,
                'processing_time': processing_time,
                'session_progress': f"{self.stats.processed_this_session}/{self.stats.to_process}"
            }
        )
        self.events.append(event)
        
        # Log progress every 10 photos
        if self.stats.processed_this_session % 10 == 0:
            self._log_progress()
    
    def record_skip(self, photo_uuid: str, reason: str):
        """Record a skipped photo.
        
        Args:
            photo_uuid: UUID of skipped photo
            reason: Reason for skipping
        """
        self.stats.skipped_this_session += 1
        
        if reason not in self.stats.skipped_by_type:
            self.stats.skipped_by_type[reason] = 0
        self.stats.skipped_by_type[reason] += 1
        
        event = ProcessingEvent(
            timestamp=datetime.now(),
            event_type='photo_skipped',
            photo_uuid=photo_uuid,
            details={'reason': reason}
        )
        self.events.append(event)
    
    def record_error(self, photo_uuid: Optional[str], error_type: str, error_msg: str):
        """Record an error event.
        
        Args:
            photo_uuid: UUID of photo that caused error (if applicable)
            error_type: Type of error
            error_msg: Error message
        """
        self.stats.errors_this_session += 1
        
        if error_type not in self.stats.errors_by_type:
            self.stats.errors_by_type[error_type] = 0
        self.stats.errors_by_type[error_type] += 1
        
        event = ProcessingEvent(
            timestamp=datetime.now(),
            event_type='error',
            photo_uuid=photo_uuid,
            details={
                'error_type': error_type,
                'error_message': error_msg
            }
        )
        self.events.append(event)
        
        logger.error(f"Error recorded: {error_type} - {error_msg}")
    
    def record_batch_complete(self, batch_num: int, batch_size: int, matches: List[str]):
        """Record batch completion.
        
        Args:
            batch_num: Batch number
            batch_size: Size of batch
            matches: List of matched photo UUIDs
        """
        event = ProcessingEvent(
            timestamp=datetime.now(),
            event_type='batch_complete',
            batch_number=batch_num,
            details={
                'batch_size': batch_size,
                'matches_in_batch': len(matches),
                'total_session_matches': self.stats.matched_this_session
            }
        )
        self.events.append(event)
        
        logger.info(f"Batch {batch_num} complete: {batch_size} photos, {len(matches)} matches")
        self._save_diagnostic_snapshot()
    
    def complete_processing(self):
        """Mark processing as complete and generate final report."""
        self.end_time = datetime.now()
        
        event = ProcessingEvent(
            timestamp=self.end_time,
            event_type='complete',
            details=self.stats.get_session_summary()
        )
        self.events.append(event)
        
        self._generate_final_report()
        self._save_diagnostic_snapshot()
    
    def _log_progress(self):
        """Log current progress."""
        if self.stats.to_process > 0:
            session_advanced = self.stats.processed_this_session + self.stats.skipped_this_session
            session_progress = (session_advanced / self.stats.to_process) * 100
        else:
            session_progress = 100.0
        
        overall_progress = self.stats.get_completion_percentage()
        
        logger.info(f"Progress: Session {session_progress:.1f}% "
                   f"({self.stats.processed_this_session + self.stats.skipped_this_session}/"
                   f"{self.stats.to_process}) | "
                   f"Overall {overall_progress:.1f}% "
                   f"({self.stats.previously_processed + self.stats.processed_this_session + self.stats.skipped_this_session}/"
                   f"{self.stats.total_in_library})")
    
    def _generate_final_report(self):
        """Generate and log final processing report."""
        if not self.start_time or not self.end_time:
            return
        
        duration = self.end_time - self.start_time
        
        # Determine remaining count up front to select header wording
        remaining_count = self.stats.total_in_library - (
            self.stats.previously_processed +
            self.stats.processed_this_session +
            self.stats.skipped_this_session
        )

        header = (
            "ALL PHOTOS COVERED - FINAL DIAGNOSTIC REPORT"
            if remaining_count <= 0
            else "SESSION COMPLETE - REVIEW REQUIRED - FINAL DIAGNOSTIC REPORT"
        )

        logger.info("=" * 70)
        logger.info(header)
        logger.info("=" * 70)
        
        # Library Status
        logger.info("\n📚 LIBRARY STATUS:")
        logger.info(f"  Total photos in library:     {self.stats.total_in_library:,}")
        logger.info(f"  Previously processed:         {self.stats.previously_processed:,}")
        logger.info(f"  Needed processing:            {self.stats.to_process:,}")
        
        # Session Results
        logger.info("\n📊 SESSION RESULTS:")
        logger.info(f"  Processed this session:       {self.stats.processed_this_session:,}")
        logger.info(f"  Matches found:                {self.stats.matched_this_session:,}")
        logger.info(f"  Errors encountered:           {self.stats.errors_this_session:,}")
        logger.info(f"  Photos skipped:               {self.stats.skipped_this_session:,}")
        
        # Performance Metrics
        logger.info("\n⚡ PERFORMANCE:")
        logger.info(f"  Total duration:               {duration}")
        if self.stats.processing_times:
            avg_time = self.stats.get_average_processing_time()
            logger.info(f"  Average time per photo:       {avg_time:.2f} seconds")
            logger.info(f"  Photos per minute:            {60/avg_time:.1f}")
        
        # Completion Status
        logger.info("\n✅ COMPLETION STATUS:")
        completion = self.stats.get_completion_percentage()
        logger.info(f"  Overall completion:           {completion:.1f}%")
        
        # Remaining should account for items skipped (advanced) this session
        remaining = remaining_count
        if remaining > 0:
            logger.info(f"  Photos remaining:             {remaining:,}")
            if self.stats.processing_times:
                est_time = remaining * self.stats.get_average_processing_time()
                logger.info(f"  Estimated time to complete:   {timedelta(seconds=int(est_time))}")
        else:
            logger.info("  ✓ All photos have been processed!")
        
        # Skip Reasons
        if self.stats.skipped_by_type:
            logger.info("\n⏭️  SKIP REASONS:")
            for reason, count in self.stats.skipped_by_type.items():
                logger.info(f"  {reason:30} {count:,}")
        
        # Error Summary
        if self.stats.errors_by_type:
            logger.info("\n❌ ERROR SUMMARY:")
            for error_type, count in self.stats.errors_by_type.items():
                logger.info(f"  {error_type:30} {count:,}")
        
        logger.info("\n" + "=" * 70)
        logger.info(f"Diagnostic log saved to: {self.diagnostic_file}")
        logger.info("=" * 70)
    
    def _save_diagnostic_snapshot(self):
        """Save current diagnostic state to file."""
        try:
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'stats': asdict(self.stats),
                'events': [
                    {
                        'timestamp': e.timestamp.isoformat(),
                        'event_type': e.event_type,
                        'photo_uuid': e.photo_uuid,
                        'batch_number': e.batch_number,
                        'details': e.details
                    }
                    for e in self.events
                ]
            }
            
            with open(self.diagnostic_file, 'w') as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save diagnostic snapshot: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current processing status for display.
        
        Returns:
            Dictionary with current status information
        """
        status = {
            'is_processing': self.start_time is not None and self.end_time is None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'current_stats': self.stats.get_session_summary()
        }
        
        if self.start_time and not self.end_time:
            elapsed = datetime.now() - self.start_time
            status['elapsed_time'] = str(elapsed).split('.')[0]
            
            if self.stats.to_process > 0:
                progress = (self.stats.processed_this_session / self.stats.to_process) * 100
                status['session_progress'] = f"{progress:.1f}%"
        
        return status
