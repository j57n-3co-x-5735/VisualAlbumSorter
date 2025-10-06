"""Enhanced photo processor with comprehensive diagnostics and progress tracking."""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Tuple
from datetime import datetime

from .export_utils import export_heic_as_jpeg
from ..utils.diagnostics import DiagnosticsTracker, PhotoStats

logger = logging.getLogger(__name__)


class EnhancedPhotoProcessor:
    """Photo processor with integrated diagnostics and detailed progress tracking."""
    
    def __init__(self, config: 'Config', classifier: 'ImageClassifier', enable_diagnostics: bool = True):
        """Initialize enhanced photo processor.
        
        Args:
            config: Application configuration
            classifier: Image classifier instance
            enable_diagnostics: Whether to enable detailed diagnostics
        """
        self.config = config
        self.classifier = classifier
        self.enable_diagnostics = enable_diagnostics
        
        # Initialize state management
        self.state = self._load_state()
        self.done_uuids = self._load_done_uuids()
        
        # Initialize diagnostics
        if enable_diagnostics:
            self.diagnostics = DiagnosticsTracker(config)
        else:
            self.diagnostics = None
        
        # Import Photos libraries
        self._init_photo_libraries()
        
        # Processing state
        self.current_batch_num = 0
        self.session_start_time = None
        self.photos_lib = None
        self.album = None
    
    def _init_photo_libraries(self):
        """Initialize macOS Photos library connections."""
        try:
            import osxphotos
            self.osxphotos = osxphotos
            logger.info("osxphotos library loaded")
        except ImportError:
            logger.error("osxphotos not installed. Run: pip3 install osxphotos")
            raise
        
        try:
            from photoscript import PhotosLibrary
            self.PhotosLibrary = PhotosLibrary
            logger.info("photoscript library loaded")
        except ImportError:
            logger.error("photoscript not installed. Run: pip3 install photoscript")
            raise
    
    def process_library(self) -> Dict[str, Any]:
        """Process the entire photo library with comprehensive tracking.
        
        Returns:
            Processing summary dictionary
        """
        self.session_start_time = datetime.now()
        logger.info(f"Starting photo processing for task: {self.config.task.name}")
        
        try:
            # Open photo libraries
            db = self.osxphotos.PhotosDB()
            self.photos_lib = self.PhotosLibrary()
            
            # Get or create album
            self.album = self._get_or_create_album(self.photos_lib)
            
            # Get all photos and analyze current state
            all_photos = db.photos()
            total_photos = len(all_photos)
            
            # Calculate actual work needed
            photos_to_process, already_processed_count = self._analyze_work_needed(all_photos)
            
            # Start diagnostics tracking
            if self.diagnostics:
                self.diagnostics.start_processing(total_photos, self.done_uuids)
            
            # Check if there's any work to do
            if not photos_to_process:
                logger.info("=" * 60)
                logger.info("NO NEW PHOTOS TO PROCESS")
                logger.info(f"All {total_photos} photos have already been processed")
                logger.info("=" * 60)
                
                if self.diagnostics:
                    self.diagnostics.complete_processing()
                
                return {
                    'status': 'up_to_date',
                    'total_photos': total_photos,
                    'previously_processed': already_processed_count,
                    'processed_this_session': 0
                }
            
            # Process photos
            summary = self._process_photos(photos_to_process, all_photos)
            
            # Complete diagnostics
            if self.diagnostics:
                self.diagnostics.complete_processing()
            
            return summary
            
        except Exception as e:
            logger.error(f"Critical error during processing: {e}", exc_info=True)
            if self.diagnostics:
                self.diagnostics.record_error(None, 'critical', str(e))
                self.diagnostics.complete_processing()
            raise
    
    def _analyze_work_needed(self, all_photos: List) -> Tuple[List, int]:
        """Analyze which photos need processing.
        
        Args:
            all_photos: All photos from the library
            
        Returns:
            Tuple of (photos_to_process, already_processed_count)
        """
        logger.info("Analyzing library to determine work needed...")
        
        photos_to_process = []
        already_processed_count = 0
        
        # Start from last saved position if resuming
        start_index = self.state.get('last_index', 0)
        if start_index > 0:
            logger.info(f"Resuming from index {start_index}")
            already_processed_count = start_index
        
        # Check each photo
        for i, photo in enumerate(all_photos[start_index:], start=start_index):
            if photo.uuid in self.done_uuids:
                already_processed_count += 1
            else:
                photos_to_process.append((i, photo))
        
        logger.info(f"Analysis complete:")
        logger.info(f"  - Total photos: {len(all_photos)}")
        logger.info(f"  - Already processed: {already_processed_count}")
        logger.info(f"  - Need processing: {len(photos_to_process)}")
        
        return photos_to_process, already_processed_count
    
    def _process_photos(self, photos_to_process: List[Tuple[int, Any]], 
                       all_photos: List) -> Dict[str, Any]:
        """Process the photos that need processing.
        
        Args:
            photos_to_process: List of (index, photo) tuples to process
            all_photos: Complete list of all photos for reference
            
        Returns:
            Processing summary
        """
        batch_size = self.config.processing.batch_size
        total_to_process = len(photos_to_process)
        processed_count = 0
        match_count = 0
        error_count = 0
        skip_count = 0
        
        logger.info(f"Processing {total_to_process} photos in batches of {batch_size}")
        
        # Process in batches
        for batch_start in range(0, total_to_process, batch_size):
            batch_end = min(batch_start + batch_size, total_to_process)
            batch = photos_to_process[batch_start:batch_end]
            self.current_batch_num += 1
            
            logger.info(f"\nProcessing batch {self.current_batch_num}: "
                       f"photos {batch_start+1}-{batch_end} of {total_to_process}")
            
            batch_matches = []
            batch_start_time = time.time()
            
            for idx, (photo_index, photo) in enumerate(batch):
                photo_start_time = time.time()
                
                # Check if should skip
                skip_reason = self._get_skip_reason(photo)
                if skip_reason:
                    skip_count += 1
                    self._mark_done(photo.uuid)
                    
                    if self.diagnostics:
                        self.diagnostics.record_skip(photo.uuid, skip_reason)
                    continue
                
                # Process photo
                try:
                    result = self._classify_photo(photo)
                    processing_time = time.time() - photo_start_time
                    
                    if result == "yes":
                        logger.info(f"  ✓ Match found: {photo.original_filename}")
                        batch_matches.append(photo.uuid)
                        match_count += 1
                    elif result == "error":
                        error_count += 1
                    
                    processed_count += 1
                    self._mark_done(photo.uuid)
                    
                    if self.diagnostics:
                        self.diagnostics.record_photo_processed(
                            photo.uuid, result, processing_time, self.current_batch_num
                        )
                    
                except Exception as e:
                    logger.error(f"  ✗ Error processing {photo.original_filename}: {e}")
                    error_count += 1
                    processing_time = time.time() - photo_start_time
                    
                    if self.diagnostics:
                        self.diagnostics.record_error(photo.uuid, 'processing_error', str(e))
                
                # Update album periodically (re-resolves album inside)
                if len(batch_matches) >= self.config.processing.album_update_frequency:
                    self._add_to_album(self.album, batch_matches, self.photos_lib)
                    self.state['matches'].extend(batch_matches)
                    batch_matches = []
                
                # Check debug limit
                if self._should_stop_debug(match_count):
                    logger.info("Debug limit reached, stopping processing")
                    break
            
            # Add remaining matches to album (re-resolves album inside)
            if batch_matches:
                self._add_to_album(self.album, batch_matches, self.photos_lib)
                self.state['matches'].extend(batch_matches)
            
            # Update state after batch
            last_photo_index = batch[-1][0]
            self.state['last_index'] = last_photo_index + 1
            self.state['batch_processed'] = self.current_batch_num
            self._save_state()
            
            # Record batch completion
            if self.diagnostics:
                self.diagnostics.record_batch_complete(
                    self.current_batch_num, 
                    len(batch),
                    batch_matches
                )
            
            # Log batch summary
            batch_time = time.time() - batch_start_time
            logger.info(f"Batch {self.current_batch_num} complete in {batch_time:.1f}s")
            logger.info(f"  Processed: {len(batch)}, Matches: {len(batch_matches)}")
            
            # Check if should stop
            if self._should_stop_debug(match_count):
                break
            
            # Small delay between batches
            time.sleep(0.5)
        
        # Final summary
        return {
            'status': 'completed',
            'total_photos': len(all_photos),
            'processed_this_session': processed_count,
            'matches_this_session': match_count,
            'errors_this_session': error_count,
            'skipped_this_session': skip_count,
            'batches_processed': self.current_batch_num
        }
    
    def _get_skip_reason(self, photo) -> Optional[str]:
        """Determine if and why a photo should be skipped.
        
        Args:
            photo: Photo object to check
            
        Returns:
            Skip reason string or None if shouldn't skip
        """
        # Already processed check
        if photo.uuid in self.done_uuids:
            return "already_processed"
        
        # Skip videos if configured
        if self.config.processing.skip_videos and photo.ismovie:
            return "video_file"
        
        # Skip specific file types
        if photo.path:
            ext = Path(photo.path).suffix.upper().lstrip('.')
            if ext in self.config.processing.skip_types:
                return f"{ext}_file"
        
        # Skip photos without accessible path
        if not photo.path or not Path(photo.path).exists():
            return "no_accessible_file"
        
        return None
    
    def _classify_photo(self, photo) -> str:
        """Export and classify a photo.
        
        Args:
            photo: osxphotos photo object
            
        Returns:
            Classification result: "yes", "no", or "error"
        """
        try:
            # Export photo to temp directory
            if photo.original_filename and photo.original_filename.upper().endswith('.HEIC'):
                temp_path = export_heic_as_jpeg(
                    photo,
                    self.config.storage.temp_dir,
                    f"temp_{photo.uuid}.jpeg",
                    use_photos_export=True,
                )
            else:
                exported = photo.export(
                    str(self.config.storage.temp_dir),
                    f"temp_{photo.uuid}.jpg",
                    overwrite=True
                )
                temp_path = Path(exported[0]) if exported else None

            if not temp_path:
                logger.warning(f"Failed to export {photo.original_filename}")
                return "error"
            
            # Classify the image
            result = self.classifier.classify(temp_path)
            
            # Clean up temp file
            try:
                temp_path.unlink()
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying {photo.original_filename}: {e}")
            return "error"
    
    def _should_stop_debug(self, match_count: int) -> bool:
        """Check if should stop due to debug mode limits.
        
        Args:
            match_count: Current number of matches
            
        Returns:
            True if should stop processing
        """
        if not self.config.processing.debug_mode:
            return False
        
        return match_count >= self.config.processing.debug_limit
    
    def _get_or_create_album(self, photos_lib):
        """Get existing album or create new one.
        
        Args:
            photos_lib: PhotoScript library object
            
        Returns:
            Album object or None
        """
        album_name = self.config.album.name
        
        try:
            # Check if album exists
            for album in photos_lib.albums():
                if album.name == album_name:
                    logger.info(f"Using existing album: {album_name}")
                    return album
            
            # Create new album if configured
            if self.config.album.create_if_missing:
                album = photos_lib.create_album(album_name)
                logger.info(f"Created new album: {album_name}")
                return album
            else:
                logger.warning(f"Album {album_name} not found and create_if_missing is False")
                return None
                
        except Exception as e:
            logger.error(f"Error managing album: {e}")
            return None
    
    def _add_to_album(self, album, uuids: List[str], photos_lib):
        """Add photos to album.
        
        Args:
            album: PhotoScript album object
            uuids: List of photo UUIDs to add
            photos_lib: PhotoScript library object
        """
        if not uuids:
            return
        
        album_obj = album or self._get_or_create_album(photos_lib)
        if album_obj is None:
            logger.warning("Unable to resolve album; skipping album add")
            return
        
        try:
            logger.info(f"Adding {len(uuids)} photos to album")

            # Fetch photos in bulk when possible
            try:
                photos_to_add = list(photos_lib.photos(uuid=uuids))
            except TypeError:
                photos_to_add = []

            if not photos_to_add:
                # Fallback: fetch individually (older PhotoScript versions)
                for uuid in uuids:
                    try:
                        photo = photos_lib.photo(uuid=uuid)
                    except Exception:
                        photo = None
                    if photo:
                        photos_to_add.append(photo)

            if not photos_to_add:
                logger.warning("No matching Photos library items found for provided UUIDs; skipping album add")
                return

            add_photos_fn = getattr(album_obj, "add_photos", None)
            add_fn = getattr(album_obj, "add", None)

            if callable(add_photos_fn):
                try:
                    add_photos_fn(*photos_to_add)
                except TypeError:
                    add_photos_fn(photos_to_add)
            elif callable(add_fn):
                try:
                    add_fn(photos_to_add)
                except TypeError:
                    add_fn(*photos_to_add)
            else:
                logger.error("Album object exposes neither add() nor add_photos(); cannot add matches")
                return

            logger.info(f"Successfully added {len(photos_to_add)} photos to album")

        except Exception as e:
            logger.exception(f"Error adding photos to album: {e}")
    
    def _load_state(self) -> Dict[str, Any]:
        """Load processing state from file.
        
        Returns:
            State dictionary
        """
        state_path = self.config.get_state_path()
        
        if state_path.exists():
            try:
                with open(state_path) as f:
                    state = json.load(f)
                logger.info(f"Resumed from batch {state.get('batch_processed', 0)}, "
                          f"index {state.get('last_index', 0)}")
                return state
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
        
        return {
            'last_index': 0,
            'matches': [],
            'errors': 0,
            'batch_processed': 0
        }
    
    def _save_state(self):
        """Save processing state to file."""
        state_path = self.config.get_state_path()
        state_path.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            with open(state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state: {e}")
    
    def _load_done_uuids(self) -> Set[str]:
        """Load set of processed photo UUIDs.
        
        Returns:
            Set of UUID strings
        """
        done_path = self.config.get_done_path()
        
        if done_path.exists():
            try:
                return {line.strip() for line in done_path.read_text().splitlines() 
                       if line.strip()}
            except Exception as e:
                logger.warning(f"Could not load done UUIDs: {e}")
        
        return set()
    
    def _mark_done(self, uuid: str):
        """Mark a photo as processed.
        
        Args:
            uuid: Photo UUID
        """
        self.done_uuids.add(uuid)
        
        done_path = self.config.get_done_path()
        done_path.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            with open(done_path, 'a') as f:
                f.write(f"{uuid}\n")
        except Exception as e:
            logger.error(f"Could not mark {uuid} as done: {e}")
