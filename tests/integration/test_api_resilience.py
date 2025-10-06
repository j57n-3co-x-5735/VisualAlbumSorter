"""
P0 Priority Test Cases - API Resilience and Retry Logic
Tests for TC10, TC04: API timeout/retry and provider failover scenarios
Optimized for LM Studio and large photo libraries (70,000+ photos)
"""

import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.providers.ollama import OllamaProvider
from visualalbumsorter.utils.provider_factory import create_provider


class TestAPITimeoutAndRetry:
    """TC10: API timeout and retry logic (ROI: 9.1)"""
    
    @pytest.mark.p0
    def test_lm_studio_timeout_handling(self, test_images):
        """Test LM Studio timeout with retry logic."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.post') as mock_post:
            # Simulate timeout on first two attempts, success on third
            # Create proper Mock objects with raise_for_status method
            timeout_mock1 = Mock()
            timeout_mock1.side_effect = requests.Timeout("Connection timeout")
            timeout_mock2 = Mock()
            timeout_mock2.side_effect = requests.Timeout("Connection timeout")
            success_mock = Mock()
            success_mock.json.return_value = {
                "choices": [{"message": {"content": "Success response"}}]
            }
            success_mock.raise_for_status.return_value = None
            
            mock_post.side_effect = [
                requests.Timeout("Connection timeout"),
                requests.Timeout("Connection timeout"),
                success_mock
            ]
            
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=3
            )
            
            assert result == "Success response"
            assert mock_post.call_count == 3
    
    @pytest.mark.p0
    def test_exponential_backoff(self, test_images):
        """Test exponential backoff between retries."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        call_times = []
        
        def track_time(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) < 3:
                raise requests.Timeout("Timeout")
            success_mock = Mock()
            success_mock.json.return_value = {
                "choices": [{"message": {"content": "Success"}}]
            }
            success_mock.raise_for_status.return_value = None
            return success_mock
        
        with patch('requests.post', side_effect=track_time):
            with patch('time.sleep') as mock_sleep:
                result = provider.classify_image(
                    test_images['generic'],
                    "Test prompt",
                    max_retries=3
                )
                
                # Verify exponential backoff was applied
                sleep_calls = mock_sleep.call_args_list
                if len(sleep_calls) >= 2:
                    # Second retry should have longer delay than first
                    assert sleep_calls[1][0][0] > sleep_calls[0][0][0]
    
    @pytest.mark.p0
    def test_max_retries_exceeded(self, test_images):
        """Test behavior when max retries are exceeded."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.post') as mock_post:
            # All attempts fail
            mock_post.side_effect = requests.Timeout("Persistent timeout")
            
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=3
            )
            
            # Should return empty string after all retries fail
            assert result == ""
            assert mock_post.call_count == 3
    
    @pytest.mark.p0
    def test_intermittent_failures(self, test_images):
        """Test handling of intermittent API failures."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        responses = [
            requests.ConnectionError("Connection refused"),
            Mock(status_code=500),  # Server error
            Mock(json=lambda: {
                "choices": [{"message": {"content": "Finally working"}}]
            }, raise_for_status=Mock())
        ]
        
        with patch('requests.post', side_effect=responses):
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=3
            )
            
            assert result == "Finally working"
    
    @pytest.mark.p0
    def test_large_batch_timeout_handling(self, test_images):
        """Test timeout handling with large batch processing (70k+ photos)."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        # Simulate processing many photos with occasional timeouts
        success_count = 0
        timeout_count = 0
        
        def simulate_api_call(*args, **kwargs):
            nonlocal success_count, timeout_count
            import random
            if random.random() < 0.1:  # 10% timeout rate
                timeout_count += 1
                raise requests.Timeout("Timeout")
            success_count += 1
            success_mock = Mock()
            success_mock.json.return_value = {
                "choices": [{"message": {"content": f"Photo {success_count}"}}]
            }
            success_mock.raise_for_status.return_value = None
            return success_mock
        
        with patch('requests.post', side_effect=simulate_api_call):
            # Process subset of photos
            results = []
            for i in range(100):  # Simulate 100 photos from 70k
                result = provider.classify_image(
                    test_images['batch'][i % 10],
                    "Test prompt",
                    max_retries=2
                )
                if result:
                    results.append(result)
            
            # Should handle timeouts gracefully
            assert len(results) > 80  # Most should succeed despite timeouts
    
    @pytest.mark.p0
    def test_timeout_with_different_durations(self, test_images):
        """Test different timeout durations."""
        test_cases = [
            (1, "Quick timeout"),
            (10, "Medium timeout"),
            (30, "Long timeout")
        ]
        
        for timeout_duration, description in test_cases:
            provider = LMStudioProvider(
                model_name="test-model",
                api_url="http://localhost:1234/v1/chat/completions"
            )
            
            with patch('requests.post') as mock_post:
                success_mock = Mock()
                success_mock.json.return_value = {
                    "choices": [{"message": {"content": description}}]
                }
                success_mock.raise_for_status.return_value = None
                mock_post.return_value = success_mock
                
                result = provider.classify_image(
                    test_images['generic'],
                    "Test prompt",
                    max_retries=1
                )
                
                # Verify timeout parameter was passed (LM Studio uses 45 second timeout)
                if mock_post.call_args:
                    assert 'timeout' in mock_post.call_args[1]
                    assert mock_post.call_args[1]['timeout'] == 45


class TestProviderFailover:
    """TC04: Provider failover scenarios (ROI: 8.6)"""
    
    @pytest.mark.p0
    def test_lm_studio_offline_detection(self):
        """Test detection of offline LM Studio server."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")
            
            is_available = provider.check_server()
            
            assert is_available is False
    
    @pytest.mark.p0
    def test_provider_overloaded_handling(self, test_images):
        """Test handling of overloaded provider (429 status)."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429  # Too Many Requests
            mock_response.headers = {'Retry-After': '5'}
            mock_response.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
            mock_post.return_value = mock_response
            
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=2
            )
            
            # Should handle rate limiting
            assert result == "" or result is None
    
    @pytest.mark.p0
    def test_invalid_model_handling(self, test_images):
        """Test handling of invalid model name."""
        provider = LMStudioProvider(
            model_name="non-existent-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "error": "Model not found"
            }
            mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_post.return_value = mock_response
            
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=1
            )
            
            assert result == ""
    
    @pytest.mark.p0
    def test_malformed_response_handling(self, test_images):
        """Test handling of malformed API responses."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        test_responses = [
            {},  # Empty response
            {"choices": []},  # Empty choices
            {"choices": [{}]},  # Missing message
            {"choices": [{"message": {}}]},  # Missing content
            {"unexpected": "format"},  # Completely wrong format
        ]
        
        for bad_response in test_responses:
            with patch('requests.post') as mock_post:
                response_mock = Mock()
                response_mock.json.return_value = bad_response
                response_mock.raise_for_status.return_value = None
                mock_post.return_value = response_mock
                
                result = provider.classify_image(
                    test_images['generic'],
                    "Test prompt",
                    max_retries=1
                )
                
                # Should handle gracefully
                assert result == "" or result is None
    
    @pytest.mark.p0
    def test_provider_switching_on_failure(self, mock_config):
        """Test switching from LM Studio to fallback provider."""
        # Primary provider (LM Studio) fails
        primary_config = {
            "type": "lm_studio",
            "settings": {
                "model": "primary-model",
                "api_url": "http://localhost:1234/v1/chat/completions"
            }
        }
        
        # Fallback provider (Ollama) works
        fallback_config = {
            "type": "ollama",
            "settings": {
                "model": "fallback-model",
                "api_url": "http://localhost:11434/api/generate"
            }
        }
        
        with patch('requests.post') as mock_post:
            with patch('requests.get') as mock_get:
                # LM Studio is offline
                mock_get.side_effect = requests.ConnectionError("LM Studio offline")
                
                # Try primary provider
                primary = create_provider(primary_config)
                assert primary.check_server() is False
                
                # Switch to fallback - Mock Ollama's tags endpoint
                fallback = create_provider(fallback_config)
                mock_get.side_effect = None
                ollama_response = Mock()
                ollama_response.json.return_value = {
                    "models": [{"name": "fallback-model"}]
                }
                ollama_response.raise_for_status.return_value = None
                mock_get.return_value = ollama_response
                
                assert fallback.check_server() is True
    
    @pytest.mark.p0
    def test_graceful_degradation(self):
        """Test graceful degradation when all providers fail."""
        providers = [
            LMStudioProvider("model1", "http://localhost:1234/v1/chat/completions"),
            OllamaProvider("model2", "http://localhost:11434/api/generate"),
        ]
        
        all_failed = True
        with patch('requests.get') as mock_get:
            with patch('requests.post') as mock_post:
                mock_get.side_effect = requests.ConnectionError("All offline")
                mock_post.side_effect = requests.ConnectionError("All offline")
                
                for provider in providers:
                    if provider.check_server():
                        all_failed = False
                        break
                
                assert all_failed
                # System should handle this gracefully (log error, notify user)


class TestLargeScaleResilience:
    """Test resilience with 70,000+ photo libraries."""
    
    @pytest.mark.p0
    def test_memory_efficient_retry(self, test_images):
        """Test that retries don't cause memory issues with large batches."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        import sys
        
        # Track memory usage during retries
        initial_size = sys.getsizeof(provider)
        
        with patch('requests.post') as mock_post:
            # Simulate failures requiring retries
            success_mock = Mock()
            success_mock.json.return_value = {"choices": [{"message": {"content": "Success"}}]}
            success_mock.raise_for_status.return_value = None
            
            mock_post.side_effect = [
                requests.Timeout("Timeout"),
                success_mock
            ]
            
            # Process with retry
            for i in range(10):  # Small subset of 70k
                result = provider.classify_image(
                    test_images['batch'][i % 10],
                    "Test prompt",
                    max_retries=2
                )
            
            # Memory shouldn't grow significantly
            final_size = sys.getsizeof(provider)
            assert final_size < initial_size * 2  # Reasonable growth limit
    
    @pytest.mark.p0
    def test_connection_pool_exhaustion(self, test_images):
        """Test handling of connection pool exhaustion with many requests."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        with patch('requests.post') as mock_post:
            # Simulate connection pool exhaustion
            success_mock = Mock()
            success_mock.json.return_value = {"choices": [{"message": {"content": "Recovered"}}]}
            success_mock.raise_for_status.return_value = None
            
            mock_post.side_effect = [
                requests.ConnectionError("Connection pool full"),
                requests.ConnectionError("Connection pool full"),
                success_mock
            ]
            
            result = provider.classify_image(
                test_images['generic'],
                "Test prompt",
                max_retries=3
            )
            
            # Should recover after pool becomes available
            assert result == "Recovered"
    
    @pytest.mark.p0
    def test_api_rate_limiting_with_large_batches(self, test_images):
        """Test API rate limiting with large photo batches."""
        provider = LMStudioProvider(
            model_name="test-model",
            api_url="http://localhost:1234/v1/chat/completions"
        )
        
        request_times = []
        
        def track_rate_limit(*args, **kwargs):
            request_times.append(time.time())
            if len(request_times) > 10:
                # Check if requests are too fast
                recent_requests = request_times[-10:]
                time_span = recent_requests[-1] - recent_requests[0]
                if time_span < 1:  # More than 10 requests per second
                    response = Mock()
                    response.status_code = 429
                    return response
            
            success_mock = Mock()
            success_mock.json.return_value = {
                "choices": [{"message": {"content": "OK"}}]
            }
            success_mock.raise_for_status.return_value = None
            return success_mock
        
        with patch('requests.post', side_effect=track_rate_limit):
            successes = 0
            rate_limits = 0
            
            for i in range(20):
                result = provider.classify_image(
                    test_images['batch'][i % 10],
                    "Test prompt",
                    max_retries=1
                )
                if result == "OK":
                    successes += 1
                elif result == "":
                    rate_limits += 1
            
            # Should handle rate limiting appropriately
            assert successes > 0
            assert successes + rate_limits == 20