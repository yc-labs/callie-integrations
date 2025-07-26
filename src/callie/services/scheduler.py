"""
Cloud Scheduler service for managing scheduled sync jobs.
"""

import logging
from typing import Dict, List, Any, Optional
try:
    from google.cloud import scheduler_v1
    CloudSchedulerClient = scheduler_v1.CloudSchedulerClient
    HttpMethod = scheduler_v1.HttpMethod
except ImportError:
    # Fallback for testing without scheduler dependency
    CloudSchedulerClient = None
    HttpMethod = None
from google.auth import default

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for managing Cloud Scheduler jobs for sync configurations.
    """
    
    def __init__(self, project_id: Optional[str] = None, region: str = "us-central1"):
        """
        Initialize Cloud Scheduler service.
        
        Args:
            project_id: Google Cloud project ID. If None, uses default from environment.
            region: Cloud Scheduler location
        """
        try:
            if CloudSchedulerClient is None:
                raise ImportError("google-cloud-scheduler is not installed")
                
            if project_id:
                self.client = CloudSchedulerClient()
                self.project_id = project_id
            else:
                # Use application default credentials
                credentials, project = default()
                self.client = CloudSchedulerClient(credentials=credentials)
                self.project_id = project
            
            self.region = region
            self.parent = f"projects/{self.project_id}/locations/{self.region}"
            
            logger.info(f"Scheduler service initialized for project: {self.project_id}, region: {self.region}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Scheduler: {e}")
            raise
    
    def create_schedule(
        self, 
        config_id: str, 
        schedule: str, 
        service_url: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Cloud Scheduler job for a sync configuration.
        
        Args:
            config_id: Sync configuration ID
            schedule: Cron expression
            service_url: URL of the sync service to call
            description: Optional description
            
        Returns:
            Dictionary with scheduler job details
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            # Delete existing job if it exists
            try:
                self.client.delete_job(name=job_path)
                logger.info(f"Deleted existing scheduler job: {job_name}")
            except Exception:
                pass  # Job doesn't exist, which is fine
            
            # Create HTTP job
            job = {
                "name": job_path,
                "description": description or f"Sync job for configuration {config_id}",
                "schedule": schedule,
                "time_zone": "UTC",
                "http_target": {
                    "uri": f"{service_url}/api/v1/configs/{config_id}/sync",
                    "http_method": HttpMethod.POST,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": b'{"triggered_by": "scheduler"}',
                    "oidc_token": {
                        "service_account_email": f"callie-sync-sa@{self.project_id}.iam.gserviceaccount.com"
                    }
                }
            }
            
            # Create the job
            response = self.client.create_job(parent=self.parent, job=job)
            
            logger.info(f"Created scheduler job: {job_name} with schedule: {schedule}")
            
            return {
                "job_name": job_name,
                "job_path": response.name,
                "schedule": schedule,
                "status": "ENABLED",
                "uri": job["http_target"]["uri"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create schedule for config {config_id}: {e}")
            raise
    
    def update_schedule(
        self, 
        config_id: str, 
        schedule: str,
        service_url: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing Cloud Scheduler job.
        
        Args:
            config_id: Sync configuration ID
            schedule: New cron expression
            service_url: URL of the sync service to call
            description: Optional description
            
        Returns:
            Dictionary with updated scheduler job details
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            # Get existing job
            try:
                existing_job = self.client.get_job(name=job_path)
            except Exception:
                # Job doesn't exist, create it
                return self.create_schedule(config_id, schedule, service_url, description)
            
            # Update job
            job = {
                "name": job_path,
                "description": description or f"Sync job for configuration {config_id}",
                "schedule": schedule,
                "time_zone": "UTC",
                "http_target": {
                    "uri": f"{service_url}/api/v1/configs/{config_id}/sync",
                    "http_method": HttpMethod.POST,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": b'{"triggered_by": "scheduler"}',
                    "oidc_token": {
                        "service_account_email": f"callie-sync-sa@{self.project_id}.iam.gserviceaccount.com"
                    }
                }
            }
            
            # Update the job
            response = self.client.update_job(job=job)
            
            logger.info(f"Updated scheduler job: {job_name} with schedule: {schedule}")
            
            return {
                "job_name": job_name,
                "job_path": response.name,
                "schedule": schedule,
                "status": "ENABLED",
                "uri": job["http_target"]["uri"]
            }
            
        except Exception as e:
            logger.error(f"Failed to update schedule for config {config_id}: {e}")
            raise
    
    def delete_schedule(self, config_id: str) -> bool:
        """
        Delete a Cloud Scheduler job for a sync configuration.
        
        Args:
            config_id: Sync configuration ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            self.client.delete_job(name=job_path)
            logger.info(f"Deleted scheduler job: {job_name}")
            return True
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(f"Scheduler job not found: {job_name}")
                return False
            logger.error(f"Failed to delete schedule for config {config_id}: {e}")
            raise
    
    def get_schedule(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Cloud Scheduler job details for a sync configuration.
        
        Args:
            config_id: Sync configuration ID
            
        Returns:
            Dictionary with scheduler job details, None if not found
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            job = self.client.get_job(name=job_path)
            
            return {
                "job_name": job_name,
                "job_path": job.name,
                "schedule": job.schedule,
                "time_zone": job.time_zone,
                "status": job.state.name,
                "uri": job.http_target.uri if job.http_target else None,
                "description": job.description,
                "last_attempt_time": job.last_attempt_time.isoformat() if job.last_attempt_time else None,
                "next_schedule_time": job.schedule_time.isoformat() if job.schedule_time else None
            }
            
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            logger.error(f"Failed to get schedule for config {config_id}: {e}")
            raise
    
    def list_schedules(self) -> List[Dict[str, Any]]:
        """
        List all Cloud Scheduler jobs for sync configurations.
        
        Returns:
            List of scheduler job details
        """
        try:
            jobs = []
            
            for job in self.client.list_jobs(parent=self.parent):
                # Only include sync jobs (jobs that start with "sync-")
                job_name = job.name.split("/")[-1]
                if job_name.startswith("sync-"):
                    config_id = job_name.replace("sync-", "")
                    
                    jobs.append({
                        "config_id": config_id,
                        "job_name": job_name,
                        "job_path": job.name,
                        "schedule": job.schedule,
                        "time_zone": job.time_zone,
                        "status": job.state.name,
                        "uri": job.http_target.uri if job.http_target else None,
                        "description": job.description,
                        "last_attempt_time": job.last_attempt_time.isoformat() if job.last_attempt_time else None,
                        "next_schedule_time": job.schedule_time.isoformat() if job.schedule_time else None
                    })
            
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to list schedules: {e}")
            raise
    
    def pause_schedule(self, config_id: str) -> bool:
        """
        Pause a Cloud Scheduler job.
        
        Args:
            config_id: Sync configuration ID
            
        Returns:
            True if paused, False if not found
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            self.client.pause_job(name=job_path)
            logger.info(f"Paused scheduler job: {job_name}")
            return True
            
        except Exception as e:
            if "not found" in str(e).lower():
                return False
            logger.error(f"Failed to pause schedule for config {config_id}: {e}")
            raise
    
    def resume_schedule(self, config_id: str) -> bool:
        """
        Resume a paused Cloud Scheduler job.
        
        Args:
            config_id: Sync configuration ID
            
        Returns:
            True if resumed, False if not found
        """
        try:
            job_name = f"sync-{config_id}"
            job_path = f"{self.parent}/jobs/{job_name}"
            
            self.client.resume_job(name=job_path)
            logger.info(f"Resumed scheduler job: {job_name}")
            return True
            
        except Exception as e:
            if "not found" in str(e).lower():
                return False
            logger.error(f"Failed to resume schedule for config {config_id}: {e}")
            raise 