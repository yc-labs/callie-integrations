"""
Script to check current workflows and their status.
"""
import os
import sys
from google.cloud import firestore
from datetime import datetime, timezone, timedelta
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_workflows():
    """Check all workflows and their recent executions."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
    db = firestore.Client(project=project_id)
    
    print("=== CURRENT WORKFLOWS ===\n")
    
    # Get all workflows
    workflows = db.collection("workflows").get()
    
    for workflow_doc in workflows:
        workflow = workflow_doc.to_dict()
        print(f"ID: {workflow_doc.id}")
        print(f"Name: {workflow.get('name', 'N/A')}")
        print(f"Active: {workflow.get('active', False)}")
        print(f"Schedule: {workflow.get('schedule', 'N/A')}")
        print(f"Source: {workflow.get('source', {}).get('type', 'N/A')}")
        print(f"Target: {workflow.get('target', {}).get('type', 'N/A')}")
        
        # Check recent executions (simplified query)
        print("\n  Recent Executions:")
        try:
            # Try to get recent executions - this might fail if index doesn't exist
            executions = (db.collection("workflow_executions")
                         .where("workflow_id", "==", workflow_doc.id)
                         .limit(10)
                         .get())
        except Exception as e:
            print(f"    Error fetching executions: {e}")
            executions = []
        
        if not executions:
            print("    No executions found")
        else:
            for exec_doc in executions:
                execution = exec_doc.to_dict()
                start_time = execution.get('start_time')
                if start_time:
                    # Format timestamp
                    if hasattr(start_time, 'strftime'):
                        time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        time_str = str(start_time)
                else:
                    time_str = "N/A"
                    
                status = execution.get('status', 'unknown')
                result = execution.get('result', {})
                print(f"    - {time_str}: {status}")
                if status == 'completed' and result:
                    print(f"      Success: {result.get('success', 0)}, Failed: {result.get('failed', 0)}")
                elif status == 'failed':
                    print(f"      Error: {execution.get('error', 'Unknown error')}")
        
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    check_workflows()