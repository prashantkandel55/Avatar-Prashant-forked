#!/usr/bin/env python3
"""
Avatar Project - Automated Rollback Procedure
Safely rolls back repository to specified commit with comprehensive safety checks
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

class RollbackProcedure:
    """Automated rollback procedure with safety checks and logging"""
    
    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.log_dir = self.repo_path / "Avatar/rebase/logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
    
    def run_command(self, command, check=True, capture_output=True):
        """Run git command with error handling"""
        try:
            self.log(f"Executing: {command}")
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=self.repo_path,
                check=check,
                capture_output=capture_output,
                text=True
            )
            if result.stdout:
                self.log(f"Output: {result.stdout.strip()}")
            if result.stderr:
                self.log(f"Error: {result.stderr.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}")
            return None
    
    def check_prerequisites(self):
        """Check if rollback prerequisites are met"""
        self.log("Checking prerequisites...")
        
        # Check if we're in a git repository
        result = self.run_command("git status")
        if not result or "not a git repository" in result.stderr:
            self.log("ERROR: Not in a git repository")
            return False
        
        # Check for uncommitted changes
        result = self.run_command("git status --porcelain")
        if result and result.stdout.strip():
            self.log("WARNING: Uncommitted changes detected")
            self.log("Please commit or stash changes before rollback")
            return False
        
        # Check current branch
        result = self.run_command("git branch --show-current")
        if result:
            current_branch = result.stdout.strip()
            self.log(f"Current branch: {current_branch}")
            
            # Check if branch is protected
            result = self.run_command(f"git config branch.{current_branch}.protected")
            if result and result.stdout.strip() == "true":
                self.log("WARNING: Current branch is protected")
                self.log("You may need temporary branch for rollback")
        
        return True
    
    def create_backup(self):
        """Create comprehensive backup before rollback"""
        self.log("Creating repository backup...")
        
        backup_dir = self.repo_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        
        # Backup current state
        commands = [
            f"git log --oneline -50 > {backup_dir}/git_history.txt",
            f"git branch -a > {backup_dir}/branches.txt",
            f"git remote -v > {backup_dir}/remotes.txt",
            f"cp -r .git {backup_dir}/.git_backup"
        ]
        
        for cmd in commands:
            result = self.run_command(cmd)
            if not result:
                self.log(f"Backup command failed: {cmd}")
                return False
        
        self.log(f"Backup created at: {backup_dir}")
        return True
    
    def get_commit_history(self, limit=20):
        """Get recent commit history for selection"""
        self.log("Getting commit history...")
        result = self.run_command(f"git log --oneline --graph -{limit}")
        if result:
            self.log("Recent commits:")
            self.log(result.stdout)
            return result.stdout
        return None
    
    def validate_target_commit(self, commit_hash):
        """Validate target commit exists and is accessible"""
        self.log(f"Validating target commit: {commit_hash}")
        
        # Check if commit exists
        result = self.run_command(f"git cat-file -t {commit_hash}")
        if not result:
            self.log(f"ERROR: Commit {commit_hash} not found")
            return False
        
        # Get commit details
        result = self.run_command(f"git show --stat {commit_hash}")
        if result:
            self.log("Target commit details:")
            self.log(result.stdout)
        
        return True
    
    def perform_rollback(self, target_commit, branch="main"):
        """Perform the actual rollback operation"""
        self.log(f"Starting rollback to commit {target_commit} on branch {branch}")
        
        # Checkout the target branch
        result = self.run_command(f"git checkout {branch}")
        if not result:
            self.log("ERROR: Failed to checkout target branch")
            return False
        
        # Perform hard reset
        self.log(f"Performing hard reset to {target_commit}")
        result = self.run_command(f"git reset --hard {target_commit}")
        if not result:
            self.log("ERROR: Failed to perform hard reset")
            return False
        
        self.log("Hard reset completed successfully")
        return True
    
    def force_push_with_lease(self, branch="main"):
        """Force push with lease for safety"""
        self.log(f"Force pushing with lease to {branch}")
        
        # First, try to get lease
        result = self.run_command(f"git ls-remote origin {branch}")
        if not result:
            self.log("WARNING: Could not get remote branch info")
        
        # Force push with lease
        result = self.run_command(f"git push --force-with-lease origin {branch}")
        if not result:
            self.log("ERROR: Force push failed")
            return False
        
        self.log("Force push with lease completed successfully")
        return True
    
    def notify_team(self, action, commit_hash, branch):
        """Generate team notification message"""
        notification = f"""
🚨 AVATAR PROJECT REPOSITORY ROLLBACK NOTIFICATION 🚨

Action: {action}
Target Commit: {commit_hash}
Branch: {branch}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

What happened:
- Repository history has been rewritten
- Remote branch updated with force push
- All collaborators MUST update their local repos

Required Actions:
1. git fetch origin
2. git reset --hard origin/{branch}
3. DO NOT push to {branch} until further notice
4. Contact maintainers if you have questions

Reason for rollback:
[Add specific reason here]

Contact: @3C-SCSU
Emergency: [Add emergency contact here]
"""
        
        notification_file = self.log_dir / "TEAM_NOTIFICATION.md"
        with open(notification_file, 'w') as f:
            f.write(notification)
        
        self.log(f"Team notification created: {notification_file}")
        return notification_file
    
    def interactive_rollback(self):
        """Interactive rollback procedure"""
        print("=" * 60)
        print("Avatar Project - Interactive Rollback Procedure")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            self.log("Prerequisites not met. Aborting.")
            return False
        
        # Show commit history
        history = self.get_commit_history()
        if not history:
            self.log("Could not get commit history")
            return False
        
        # Get target commit
        print("\n" + "=" * 60)
        print("Select target commit for rollback:")
        print("Enter commit hash (first 7-8 characters) or 'q' to quit:")
        print("=" * 60)
        
        target_commit = input("Target commit: ").strip()
        if target_commit.lower() == 'q':
            self.log("Rollback cancelled by user")
            return False
        
        if len(target_commit) < 7:
            self.log("ERROR: Commit hash too short")
            return False
        
        # Validate commit
        if not self.validate_target_commit(target_commit):
            return False
        
        # Confirm operation
        print("\n" + "=" * 60)
        print("ROLLBACK CONFIRMATION")
        print("=" * 60)
        print(f"Target commit: {target_commit}")
        print("This will:")
        print("1. Create backup of current state")
        print("2. Reset branch to target commit")
        print("3. Force push to remote")
        print("4. Require all collaborators to update")
        print("\nType 'CONFIRM' to proceed or 'CANCEL' to abort:")
        
        confirmation = input("Confirm: ").strip().upper()
        if confirmation != 'CONFIRM':
            self.log("Rollback cancelled by user")
            return False
        
        # Create backup
        if not self.create_backup():
            self.log("Backup failed. Aborting rollback.")
            return False
        
        # Perform rollback
        if not self.perform_rollback(target_commit):
            self.log("Rollback failed")
            return False
        
        # Force push
        if not self.force_push_with_lease():
            self.log("Force push failed")
            return False
        
        # Generate team notification
        notification = self.notify_team("ROLLBACK COMPLETED", target_commit, "main")
        
        print("\n" + "=" * 60)
        print("ROLLBACK COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Target commit: {target_commit}")
        print(f"Backup location: Created")
        print(f"Team notification: {notification}")
        print("\nIMPORTANT: Notify all team members immediately!")
        
        return True
    
    def emergency_restore(self, backup_path):
        """Emergency restore from backup"""
        self.log(f"Emergency restore from backup: {backup_path}")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            self.log("ERROR: Backup directory not found")
            return False
        
        # Restore git history
        if (backup_dir / ".git_backup").exists():
            self.log("Restoring .git directory...")
            result = self.run_command(f"rm -rf .git && cp -r {backup_dir}/.git_backup .git")
            if not result:
                self.log("ERROR: Failed to restore .git directory")
                return False
        
        self.log("Emergency restore completed")
        return True

def main():
    """Main rollback procedure"""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        rollback = RollbackProcedure(repo_path)
    else:
        rollback = RollbackProcedure()
    
    try:
        success = rollback.interactive_rollback()
        if success:
            print("\n✅ Rollback procedure completed successfully")
        else:
            print("\n❌ Rollback procedure failed or cancelled")
            sys.exit(1)
    except KeyboardInterrupt:
        rollback.log("\nRollback procedure interrupted by user")
        sys.exit(1)
    except Exception as e:
        rollback.log(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
