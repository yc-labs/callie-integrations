"""
Script to clean up old workflows from Firestore.
"""
import os
import sys
from google.cloud import firestore

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def cleanup_old_workflows():
    """Delete old and duplicate workflows from Firestore."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
    db = firestore.Client(project=project_id)
    
    # List of workflow IDs to keep
    workflows_to_keep = [
        "shipstation-to-infiplex-inventory-sync-v4",  # The final working version
    ]
    
    # List of workflow IDs to delete (old, failed, or duplicate workflows)
    workflows_to_delete = [
        "shipstation-to-infiplex-fixed-v3",
        "shipstation-to-infiplex-simple-v2", # Old simplified multi-warehouse sync
        "debug-shipstation-read",
        "shipstation-to-infiplex-configurable",  # Old failing workflow
        "shipstation-to-infiplex-enhanced",
        "shipstation-to-infiplex-final-sync",
        "shipstation-to-infiplex-inventory-sync",
        "shipstation-to-infiplex-multi-warehouse-fixed",
        "shipstation-to-infiplex-multiwarehouse-v2"  # Failed to create earlier
    ]
    
    print("=== CLEANING UP OLD WORKFLOWS ===\n")
    
    deleted_count = 0
    for workflow_id in workflows_to_delete:
        try:
            doc_ref = db.collection("workflows").document(workflow_id)
            doc = doc_ref.get()
            
            if doc.exists:
                workflow_data = doc.to_dict()
                print(f"Deleting: {workflow_id}")
                print(f"  Name: {workflow_data.get('name', 'N/A')}")
                print(f"  Active: {workflow_data.get('active', False)}")
                
                # Delete the workflow
                doc_ref.delete()
                deleted_count += 1
                print("  ✓ Deleted successfully\n")
            else:
                print(f"Workflow {workflow_id} not found (already deleted?)\n")
                
        except Exception as e:
            print(f"Error deleting {workflow_id}: {e}\n")
    
    print(f"\nTotal workflows deleted: {deleted_count}")
    
    # List remaining workflows
    print("\n=== REMAINING WORKFLOWS ===\n")
    remaining = db.collection("workflows").get()
    
    for doc in remaining:
        workflow = doc.to_dict()
        status = "✓ KEEP" if doc.id in workflows_to_keep else "⚠️  UNKNOWN"
        print(f"{status} {doc.id}")
        print(f"     Name: {workflow.get('name', 'N/A')}")
        print(f"     Active: {workflow.get('active', False)}")
        print(f"     Schedule: {workflow.get('schedule', 'None')}\n")

if __name__ == "__main__":
    cleanup_old_workflows()