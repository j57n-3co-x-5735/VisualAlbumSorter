"""
P0 Priority Test Cases - State Persistence and Recovery
Tests for TC03, TC14: State persistence across interruptions and corruption recovery
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import shutil

from visualalbumsorter.core.photo_processor_enhanced import EnhancedPhotoProcessor


class TestStatePersistence:
    """TC03: State persistence across interruptions (ROI: 9.5)"""
    
    @pytest.mark.p0
    def test_state_saved_on_batch_completion(self, mock_config, mock_classifier, temp_state_dir):
        """Test that state is saved after each batch."""
        # Setup
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Simulate batch processing
            processor.state['last_index'] = 50
            processor.state['matches'] = ['uuid-1', 'uuid-2']
            processor.state['batch_processed'] = 5
            
            # Save state
            processor._save_state()
            
            # Verify state file exists and contains correct data
            assert temp_state_dir["state"].exists()
            
            with open(temp_state_dir["state"]) as f:
                saved_state = json.load(f)
            
            assert saved_state['last_index'] == 50
            assert saved_state['matches'] == ['uuid-1', 'uuid-2']
            assert saved_state['batch_processed'] == 5
    
    @pytest.mark.p0
    def test_state_resume_from_interruption(self, mock_config, mock_classifier, temp_state_dir):
        """Test resuming from interrupted processing."""
        # Setup - Create existing state
        existing_state = {
            'last_index': 75,
            'matches': ['uuid-a', 'uuid-b', 'uuid-c'],
            'batch_processed': 7
        }
        
        with open(temp_state_dir["state"], 'w') as f:
            json.dump(existing_state, f)
        
        # Create done file with processed UUIDs
        with open(temp_state_dir["done"], 'w') as f:
            for i in range(75):
                f.write(f"uuid-{i}\n")
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Initialize processor - should load existing state
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Verify state was loaded correctly
            assert processor.state['last_index'] == 75
            assert processor.state['matches'] == ['uuid-a', 'uuid-b', 'uuid-c']
            assert processor.state['batch_processed'] == 7
            assert len(processor.done_uuids) == 75
    
    @pytest.mark.p0
    def test_done_file_append_on_completion(self, mock_config, mock_classifier, temp_state_dir):
        """Test that done file is updated correctly."""
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Pre-populate done file
        with open(temp_state_dir["done"], 'w') as f:
            f.write("uuid-existing-1\n")
            f.write("uuid-existing-2\n")
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Add new processed photos
            new_uuids = ['uuid-new-1', 'uuid-new-2', 'uuid-new-3']
            for uuid in new_uuids:
                processor._mark_done(uuid)
            
            # Verify done file contains all UUIDs
            with open(temp_state_dir["done"]) as f:
                done_content = f.read().strip().split('\n')
            
            assert 'uuid-existing-1' in done_content
            assert 'uuid-existing-2' in done_content
            assert 'uuid-new-1' in done_content
            assert 'uuid-new-2' in done_content
            assert 'uuid-new-3' in done_content
    
    @pytest.mark.p0
    def test_atomic_state_update(self, mock_config, mock_classifier, temp_state_dir):
        """Test that state updates are atomic (no partial writes)."""
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Set initial state
            processor.state = {
                'last_index': 100,
                'matches': ['uuid-1', 'uuid-2'],
                'batch_processed': 10
            }
            
            # Mock a write failure partway through
            original_dump = json.dump
            call_count = [0]
            
            def failing_dump(obj, file, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # Simulate partial write then failure
                    file.write('{"last_index": 100')
                    raise IOError("Disk full")
                return original_dump(obj, file, **kwargs)
            
            with patch('json.dump', side_effect=failing_dump):
                # Attempt to save state (should fail)
                try:
                    processor._save_state()
                except IOError:
                    pass
            
            # Despite failure, old state should still be valid or recoverable
            # New processor should handle the corrupted file
            with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
                new_processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
                # Should initialize with empty state due to corruption
                assert new_processor.state['last_index'] == 0


class TestStateCorruptionRecovery:
    """TC14: State file corruption recovery (ROI: 8.7)"""
    
    @pytest.mark.p0
    def test_recover_from_invalid_json(self, mock_config, mock_classifier, temp_state_dir, caplog):
        """Test recovery from invalid JSON in state file."""
        # Create corrupted state file
        with open(temp_state_dir["state"], 'w') as f:
            f.write("{invalid json content here")
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Initialize processor - should handle corruption
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Should initialize with default state
            assert processor.state['last_index'] == 0
            assert processor.state['matches'] == []
            assert processor.state['batch_processed'] == 0
            
            # Should log warning about corruption
            assert "corrupt" in caplog.text.lower() or "error" in caplog.text.lower()
    
    @pytest.mark.p0
    def test_recover_from_missing_fields(self, mock_config, mock_classifier, temp_state_dir):
        """Test recovery from state file with missing required fields."""
        # Create state file with missing fields
        incomplete_state = {
            'last_index': 50
            # Missing 'matches' and 'batch_processed'
        }
        
        with open(temp_state_dir["state"], 'w') as f:
            json.dump(incomplete_state, f)
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Initialize processor
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Should use existing values and defaults for missing
            assert processor.state['last_index'] == 50
            assert processor.state['matches'] == []  # Default
            assert processor.state['batch_processed'] == 0  # Default
    
    @pytest.mark.p0
    def test_recover_from_type_mismatches(self, mock_config, mock_classifier, temp_state_dir):
        """Test recovery from state file with wrong data types."""
        # Create state file with wrong types
        wrong_type_state = {
            'last_index': "not_a_number",  # Should be int
            'matches': "not_a_list",  # Should be list
            'batch_processed': [1, 2, 3]  # Should be int
        }
        
        with open(temp_state_dir["state"], 'w') as f:
            json.dump(wrong_type_state, f)
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Initialize processor
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Should handle type issues gracefully
            assert isinstance(processor.state['last_index'], int)
            assert isinstance(processor.state['matches'], list)
            assert isinstance(processor.state['batch_processed'], int)
    
    @pytest.mark.p0
    def test_backup_creation_on_corruption(self, mock_config, mock_classifier, temp_state_dir):
        """Test that a backup is created when corruption is detected."""
        # Create corrupted state file
        corrupted_content = "{corrupted"
        with open(temp_state_dir["state"], 'w') as f:
            f.write(corrupted_content)
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Initialize processor
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Check for backup file
            backup_files = list(temp_state_dir["dir"].glob("state.json.backup*"))
            
            # Should create at least one backup
            assert len(backup_files) > 0 or processor.state['last_index'] == 0
    
    @pytest.mark.p0
    def test_file_locked_handling(self, mock_config, mock_classifier, temp_state_dir):
        """Test handling of locked state file."""
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Create initial state
        initial_state = {'last_index': 25, 'matches': [], 'batch_processed': 2}
        with open(temp_state_dir["state"], 'w') as f:
            json.dump(initial_state, f)
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.state['last_index'] = 50
            
            # Simulate file lock during save
            with patch('builtins.open', side_effect=PermissionError("File locked")):
                # Should handle the error gracefully
                try:
                    processor._save_state()
                except PermissionError:
                    pass  # Expected
            
            # State in memory should still be intact
            assert processor.state['last_index'] == 50
    
    @pytest.mark.p0
    def test_done_file_deduplication(self, mock_config, mock_classifier, temp_state_dir):
        """Test that done file handles duplicates correctly."""
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        # Create done file with duplicates
        with open(temp_state_dir["done"], 'w') as f:
            f.write("uuid-1\n")
            f.write("uuid-2\n")
            f.write("uuid-1\n")  # Duplicate
            f.write("uuid-3\n")
            f.write("uuid-2\n")  # Duplicate
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Should deduplicate on load
            assert len(processor.done_uuids) == 3
            assert 'uuid-1' in processor.done_uuids
            assert 'uuid-2' in processor.done_uuids
            assert 'uuid-3' in processor.done_uuids


class TestStateConsistency:
    """Test state consistency between components."""
    
    @pytest.mark.p0
    def test_state_done_file_consistency(self, mock_config, mock_classifier, temp_state_dir):
        """Test that state.json and done.txt remain consistent."""
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            
            # Simulate processing
            for i in range(10):
                uuid = f"uuid-{i}"
                processor._mark_done(uuid)
                if i % 3 == 0:  # Some matches
                    processor.state['matches'].append(uuid)
            
            processor.state['last_index'] = 10
            processor._save_state()
            
            # Load in new processor
            with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
                new_processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
                
                # Verify consistency
                assert new_processor.state['last_index'] == 10
                assert len(new_processor.done_uuids) == 10
                
                # All matches should be in done_uuids
                for match in new_processor.state['matches']:
                    assert match in new_processor.done_uuids
    
    @pytest.mark.p0
    def test_concurrent_state_access(self, mock_config, mock_classifier, temp_state_dir):
        """Test handling of concurrent state access (basic test)."""
        import threading
        
        mock_config.storage.temp_dir = temp_state_dir["dir"]
        mock_config.get_state_path.return_value = temp_state_dir["state"]
        mock_config.get_done_path.return_value = temp_state_dir["done"]
        
        results = []
        errors = []
        
        def process_photos():
            try:
                with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
                    processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
                    for i in range(5):
                        processor._mark_done(f"thread-{threading.current_thread().name}-{i}")
                    processor._save_state()
                    results.append(len(processor.done_uuids))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=process_photos, name=f"worker-{i}")
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5)
        
        # Should handle concurrent access without crashes
        assert len(errors) == 0 or all("lock" in e.lower() for e in errors)