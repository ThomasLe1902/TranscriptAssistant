"""
Quota Manager - Quản lý quota và rate limiting cho Gemini API
"""

import time
import asyncio
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class QuotaManager:
    """Quản lý quota và rate limiting"""
    
    def __init__(self):
        self.quota_reset_time = None
        self.request_count = 0
        self.max_requests_per_minute = 15  # Free tier limit
        self.last_request_time = None
        
    def parse_quota_error(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Parse error message để lấy thông tin quota"""
        error_lower = error_message.lower()
        
        # Extract retry delay
        retry_delay = None
        if 'retry in' in error_lower:
            try:
                retry_match = re.search(r'retry in ([\d.]+)s', error_lower)
                if retry_match:
                    retry_delay = float(retry_match.group(1))
            except:
                pass
        
        # Extract quota limit
        quota_limit = None
        if 'limit:' in error_lower:
            try:
                limit_match = re.search(r'limit: (\d+)', error_lower)
                if limit_match:
                    quota_limit = int(limit_match.group(1))
            except:
                pass
        
        return {
            'retry_delay': retry_delay,
            'quota_limit': quota_limit,
            'is_quota_error': any(keyword in error_lower for keyword in ['quota', 'rate', 'limit', 'exceeded', '429'])
        }
    
    def should_wait(self) -> bool:
        """Kiểm tra xem có nên đợi không"""
        if self.quota_reset_time and datetime.now() < self.quota_reset_time:
            return True
        
        # Check if we've hit the rate limit
        if self.request_count >= self.max_requests_per_minute:
            return True
            
        return False
    
    def get_wait_time(self) -> float:
        """Lấy thời gian cần đợi (seconds)"""
        if self.quota_reset_time and datetime.now() < self.quota_reset_time:
            return (self.quota_reset_time - datetime.now()).total_seconds()
        
        if self.request_count >= self.max_requests_per_minute:
            # Reset counter after 1 minute
            return 60.0
            
        return 0.0
    
    def record_request(self):
        """Ghi nhận một request"""
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        # Reset counter after 1 minute
        if self.last_request_time:
            self.quota_reset_time = self.last_request_time + timedelta(minutes=1)
    
    def handle_quota_error(self, error_message: str) -> float:
        """Xử lý quota error và trả về thời gian cần đợi"""
        quota_info = self.parse_quota_error(error_message)
        
        if not quota_info['is_quota_error']:
            return 0.0
        
        # Use retry delay from error message if available
        if quota_info['retry_delay']:
            wait_time = quota_info['retry_delay'] + 5  # Add 5 seconds buffer
            self.quota_reset_time = datetime.now() + timedelta(seconds=wait_time)
            return wait_time
        
        # Use quota limit if available
        if quota_info['quota_limit']:
            self.max_requests_per_minute = quota_info['quota_limit']
        
        # Default wait time
        wait_time = 60.0  # Wait 1 minute
        self.quota_reset_time = datetime.now() + timedelta(seconds=wait_time)
        return wait_time
    
    async def wait_if_needed(self):
        """Đợi nếu cần thiết"""
        if self.should_wait():
            wait_time = self.get_wait_time()
            if wait_time > 0:
                print(f"⏳ Waiting {wait_time:.1f}s for quota reset...")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.quota_reset_time = None
    
    def wait_if_needed_sync(self):
        """Đợi nếu cần thiết (sync version)"""
        if self.should_wait():
            wait_time = self.get_wait_time()
            if wait_time > 0:
                print(f"⏳ Waiting {wait_time:.1f}s for quota reset...")
                time.sleep(wait_time)
                self.request_count = 0
                self.quota_reset_time = None
    
    def get_status(self) -> Dict[str, Any]:
        """Lấy trạng thái quota hiện tại"""
        return {
            'request_count': self.request_count,
            'max_requests_per_minute': self.max_requests_per_minute,
            'quota_reset_time': self.quota_reset_time,
            'should_wait': self.should_wait(),
            'wait_time': self.get_wait_time()
        }

# Global quota manager instance
quota_manager = QuotaManager()

def get_quota_manager() -> QuotaManager:
    """Lấy global quota manager instance"""
    return quota_manager

