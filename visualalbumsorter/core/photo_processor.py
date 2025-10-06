"""Photo processing and album management."""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from datetime import datetime

from .export_utils import export_heic_as_jpeg

logger = logging.getLogger(__name__)


class PhotoProcessor:
    """Handles photo library processing and album management."""
    
    def __init__(self, config: 'Config', classifier: 'ImageClassifier'):
        """Initialize photo processor.
        
        Args:
            config: Application configuration
            classifier: Image classifier instance
        """
        self.config = config
        self.classifier = classifier
        self.state = self._load_state()
        self.done_uuids = self._load_done_uuids()
        
        # Import Photos libraries
        self._init_photo_libraries()
        
        # Statistics
        self.stats = {
            'processed': 0,
            'matches': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': datetime.now()
        }
    
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
    
    def process_library(self):
        """Process the entire photo library."""
        logger.info(f"Starting photo processing for task: {self.config.task.name}")
        
        # Open photo libraries
        db = self.osxphotos.PhotosDB()
        photos_lib = self.PhotosLibrary()
        
        # Get or create album
        album = self._get_or_create_album(photos_lib)
        
        # Get all photos
        all_photos = db.photos()
        total_photos = len(all_photos)
        logger.info(f"Found {total_photos} photos in library")
        
        # Process in batches
        batch_size = self.config.processing.batch_size
        
        for batch_start in range(self.state.get('last_index', 0), total_photos, batch_size):
            batch_end = min(batch_start + batch_size, total_photos)
            batch = all_photos[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}: "
                       f"photos {batch_start+1}-{batch_end} of {total_photos}")
            
            batch_matches = self._process_batch(batch, album, photos_lib)
            
            # Update state
            self.state['last_index'] = batch_end
            self.state['matches'].extend(batch_matches)
            self.state['batch_processed'] += 1
            self._save_state()
            
            # Check debug mode limit
            if self._should_stop_debug():
                logger.info("Debug mode: Stopping after match limit")
                break
            
            # Add small delay between batches
            time.sleep(0.5)
        
        # Final album update (re-resolves album inside)
        if self.state['matches']:
            self._add_to_album(album, self.state['matches'], photos_lib)
        
        self._print_summary()
    
    def _process_batch(self, photos: List, album, photos_lib) -> List[str]:
        """Process a batch of photos.
        
        Args:
            photos: List of photo objects from osxphotos
            album: PhotoScript album object
            photos_lib: PhotoScript library object
            
        Returns:
            List of UUIDs for matching photos
        """
        batch_matches = []
        
        for i, photo in enumerate(photos):
            # Skip if already processed
            if photo.uuid in self.done_uuids:
                logger.debug(f"Skipping already processed: {photo.uuid}")
                self.stats['skipped'] += 1
                continue
            
            # Skip based on type
            if self._should_skip_photo(photo):
                self.stats['skipped'] += 1
                self._mark_done(photo.uuid)
                continue
            
            # Export and classify
            result = self._classify_photo(photo)
            
            if result == "yes":
                logger.info(f"✓ Match found: {photo.original_filename}")
                batch_matches.append(photo.uuid)
                self.stats['matches'] += 1
            elif result == "error":
                self.stats['errors'] += 1
            
            self.stats['processed'] += 1
            self._mark_done(photo.uuid)
            
            # Update album periodically (re-resolves album inside)
            if len(batch_matches) >= self.config.processing.album_update_frequency:
                self._add_to_album(album, batch_matches, photos_lib)
                batch_matches = []
            
            # Check debug limit
            if self._should_stop_debug():
                break
        
        return batch_matches
    
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
            logger.error(f"Error processing {photo.original_filename}: {e}")
            return "error"
    
    def _should_skip_photo(self, photo) -> bool:
        """Check if photo should be skipped.
        
        Args:
            photo: osxphotos photo object
            
        Returns:
            True if photo should be skipped
        """
        # Skip videos if configured
        if self.config.processing.skip_videos and photo.ismovie:
            logger.debug(f"Skipping video: {photo.original_filename}")
            return True
        
        # Skip specific file types
        if photo.path:
            ext = Path(photo.path).suffix.upper().lstrip('.')
            if ext in self.config.processing.skip_types:
                logger.debug(f"Skipping {ext} file: {photo.original_filename}")
                return True
        
        # Skip photos without path
        if not photo.path or not Path(photo.path).exists():
            logger.debug(f"Skipping photo without accessible file: {photo.uuid}")
            return True
        
        return False
    
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
            for album in photos_lib.albums:
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

            try:
                photos_to_add = list(photos_lib.photos(uuid=uuids))
            except TypeError:
                photos_to_add = []

            if not photos_to_add:
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
    
    def _should_stop_debug(self) -> bool:
        """Check if should stop due to debug mode limits.
        
        Returns:
            True if should stop processing
        """
        if not self.config.processing.debug_mode:
            return False
        
        return self.stats['matches'] >= self.config.processing.debug_limit
    
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
                logger.info(f"Resumed from batch {state.get('batch_processed', 0)}")
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
    
    def _print_summary(self):
        """Print processing summary."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        logger.info("=" * 50)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Task: {self.config.task.name}")
        logger.info(f"Processed: {self.stats['processed']} photos")
        logger.info(f"Matches: {self.stats['matches']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        logger.info(f"Duration: {duration:.1f} seconds")
        
        if self.stats['processed'] > 0:
            match_rate = (self.stats['matches'] / self.stats['processed']) * 100
            logger.info(f"Match rate: {match_rate:.1f}%")
        
        logger.info("=" * 50)
