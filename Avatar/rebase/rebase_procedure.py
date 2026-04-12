#!/usr/bin/env python3
"""
Avatar Project - Automated Rebase Procedure
Advanced Git rebase operations with interactive commit selection
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

class RebaseProcedure:
    """Automated rebase procedure with interactive commit management"""
    
    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.log_dir = self.repo_path / "Avatar/rebase/logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"rebase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
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
    
    def check_rebase_prerequisites(self):
        """Check if rebase prerequisites are met"""
        self.log("Checking rebase prerequisites...")
        
        # Check if we're in a git repository
        result = self.run_command("git status")
        if not result or "not a git repository" in result.stderr:
            self.log("ERROR: Not in a git repository")
            return False
        
        # Check for clean working directory
        result = self.run_command("git status --porcelain")
        if result and result.stdout.strip():
            self.log("WARNING: Uncommitted changes detected")
            response = input("Stash changes before rebase? (y/n): ").strip().lower()
            if response == 'y':
                self.run_command("git stash push -m 'Rebase backup stash'")
            else:
                self.log("Please commit or stash changes before rebase")
                return False
        
        # Check current branch
        result = self.run_command("git branch --show-current")
        if result:
            current_branch = result.stdout.strip()
            self.log(f"Current branch: {current_branch}")
        
        return True
    
    def get_commit_list(self, branch="main", limit=30):
        """Get list of commits for interactive selection"""
        self.log(f"Getting commit list for branch {branch}...")
        
        # Get detailed commit information
        result = self.run_command(
            f"git log --oneline --graph --decorate --pretty=format:'%h|%s|%an|%ad' --date=short -{limit} {branch}"
        )
        
        if not result:
            self.log("Could not get commit list")
            return []
        
        commits = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if line.strip():
                # Parse commit line
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        commit_hash = parts[0].split()[0]  # Get hash from first part
                        commit_message = parts[1]
                        commit_author = parts[2]
                        
                        commits.append({
                            'hash': commit_hash,
                            'message': commit_message,
                            'author': commit_author
                        })
        
        return commits
    
    def interactive_commit_selection(self, commits):
        """Interactive commit selection for rebase"""
        print("\n" + "=" * 80)
        print("SELECT COMMITS FOR REBASE")
        print("=" * 80)
        print("Format: [Index] Hash | Message | Author")
        print("-" * 80)
        
        for i, commit in enumerate(commits, 1):
            hash_short = commit['hash'][:8]
            message_short = commit['message'][:50] + ('...' if len(commit['message']) > 50 else '')
            print(f"[{i:2d}] {hash_short} | {message_short} | {commit['author']}")
        
        print("\nSelect commits to:")
        print("  - Enter comma-separated indices (e.g., 1,3,5-8)")
        print("  - Enter 'all' to rebase entire branch")
        print("  - Enter 'none' to cancel")
        print("  - Enter 'drop' to drop commits (inverse selection)")
        
        selection = input("\nSelection: ").strip().lower()
        
        if selection == 'none':
            return None
        elif selection == 'all':
            return list(range(len(commits)))
        elif selection == 'drop':
            # Get indices to keep (inverse of drop)
            drop_input = input("Enter commit indices to DROP: ").strip()
            return self.parse_selection(drop_input, len(commits), invert=True)
        else:
            return self.parse_selection(selection, len(commits))
    
    def parse_selection(self, selection_str, total_commits, invert=False):
        """Parse selection string into list of indices"""
        indices = set()
        
        if not selection_str:
            return indices
        
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range selection (e.g., 3-8)
                start, end = map(int, part.split('-'))
                for i in range(start, min(end + 1, total_commits + 1)):
                    indices.add(i)
            else:
                # Single selection
                try:
                    idx = int(part)
                    if 1 <= idx <= total_commits:
                        indices.add(idx)
                except ValueError:
                    continue
        
        if invert:
            # Return indices to keep (inverse of selection)
            all_indices = set(range(1, total_commits + 1))
            indices = all_indices - indices
        
        return sorted(list(indices))
    
    def create_rebase_plan(self, selected_indices, commits):
        """Create rebase plan with commit details"""
        plan = []
        for idx in selected_indices:
            if 1 <= idx <= len(commits):
                commit = commits[idx - 1]
                plan.append({
                    'index': idx,
                    'hash': commit['hash'],
                    'message': commit['message'],
                    'action': 'KEEP'
                })
        
        return plan
    
    def interactive_rebase(self, base_commit, selected_commits):
        """Perform interactive rebase with selected commits"""
        self.log(f"Starting interactive rebase from {base_commit}")
        
        # Create temporary branch for safety
        temp_branch = f"rebase_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.run_command(f"git checkout -b {temp_branch}")
        
        # Start interactive rebase
        self.log("Starting interactive rebase...")
        
        # Create rebase instructions file
        rebase_todo = self.repo_path / ".git" / "rebase-merge" / "msg"
        rebase_todo_dir = self.repo_path / ".git" / "rebase-merge"
        rebase_todo_dir.mkdir(exist_ok=True)
        
        # For each selected commit, create rebase instruction
        for i, commit_info in enumerate(selected_commits):
            action = "pick"
            commit_hash = commit_info['hash']
            
            # You could make this interactive:
            print(f"\nCommit {i+1}/{len(selected_commits)}: {commit_info['message'][:40]}")
            print("Actions: pick, edit, squash, fixup, drop")
            action_input = input("Action (default: pick): ").strip() or "pick"
            
            if action_input in ['pick', 'edit', 'squash', 'fixup', 'drop']:
                action = action_input
            
            # Add to rebase todo
            todo_line = f"{action} {commit_hash} {commit_info['message']}\n"
            with open(rebase_todo / "todo", 'a') as f:
                f.write(todo_line)
        
        # Execute rebase
        result = self.run_command(f"git rebase -i {base_commit}")
        if not result:
            self.log("ERROR: Interactive rebase failed")
            return False
        
        self.log("Interactive rebase completed successfully")
        return True
    
    def force_push_rebased_branch(self, target_branch="main"):
        """Force push rebased branch with lease"""
        self.log(f"Force pushing rebased branch to {target_branch}")
        
        result = self.run_command(f"git push --force-with-lease origin {temp_branch}:{target_branch}")
        if not result:
            self.log("ERROR: Force push failed")
            return False
        
        self.log("Force push completed successfully")
        return True
    
    def cleanup_rebase(self, temp_branch):
        """Clean up temporary rebase branch"""
        self.log(f"Cleaning up temporary branch: {temp_branch}")
        
        # Switch back to main branch
        self.run_command("git checkout main")
        
        # Delete temporary branch
        self.run_command(f"git branch -D {temp_branch}")
        
        self.log("Rebase cleanup completed")
    
    def generate_rebase_report(self, selected_commits, base_commit, target_branch):
        """Generate detailed rebase report"""
        report = f"""
# Avatar Project - Rebase Report

## Rebase Summary
- **Base Commit**: {base_commit}
- **Target Branch**: {target_branch}
- **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Commits Processed**: {len(selected_commits)}

## Commits Processed
"""
        
        for i, commit in enumerate(selected_commits, 1):
            report += f"""
### {i}. {commit['hash']}
- **Message**: {commit['message']}
- **Status**: Processed
"""
        
        report += f"""
## Post-Rebase Actions
1. ✅ Interactive rebase completed
2. ✅ Force push with lease completed
3. ✅ Temporary branch cleaned up
4. 🔄 Team notification required

## Team Notification Required
All collaborators must run:
```bash
git fetch origin
git reset --hard origin/{target_branch}
```

## Emergency Recovery
If issues arise, use backup procedures in `/Avatar/rebase/backup_procedure.py`

---
*Generated by Avatar Project Rebase Procedure*
*Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        report_file = self.log_dir / "rebase_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.log(f"Rebase report generated: {report_file}")
        return report_file
    
    def interactive_rebase_workflow(self):
        """Complete interactive rebase workflow"""
        print("=" * 80)
        print("Avatar Project - Interactive Rebase Procedure")
        print("=" * 80)
        
        # Check prerequisites
        if not self.check_rebase_prerequisites():
            self.log("Prerequisites not met. Aborting.")
            return False
        
        # Get commit list
        commits = self.get_commit_list()
        if not commits:
            self.log("Could not get commit list")
            return False
        
        # Interactive commit selection
        selected_indices = self.interactive_commit_selection(commits)
        if selected_indices is None:
            self.log("Rebase cancelled by user")
            return False
        
        # Create rebase plan
        selected_commits = [commits[i-1] for i in selected_indices if 1 <= i <= len(commits)]
        
        if not selected_commits:
            self.log("No valid commits selected")
            return False
        
        plan = self.create_rebase_plan(selected_indices, commits)
        
        # Show rebase plan
        print("\n" + "=" * 80)
        print("REBASE PLAN")
        print("=" * 80)
        for item in plan:
            print(f"[{item['index']:2d}] {item['action']:6s} {item['hash']} {item['message']}")
        
        # Confirm rebase
        print("\n" + "=" * 80)
        print("REBASE CONFIRMATION")
        print("=" * 80)
        print("This will:")
        print("1. Create temporary branch for safety")
        print("2. Perform interactive rebase with selected commits")
        print("3. Force push to target branch")
        print("4. Require all collaborators to update")
        print("\nType 'CONFIRM' to proceed or 'CANCEL' to abort:")
        
        confirmation = input("Confirm: ").strip().upper()
        if confirmation != 'CONFIRM':
            self.log("Rebase cancelled by user")
            return False
        
        # Get base commit (commit before first selected)
        base_index = min(selected_indices) - 2
        if base_index >= 0:
            base_commit = commits[base_index]['hash']
        else:
            base_commit = "HEAD~" + str(len(commits) - min(selected_indices) + 1)
        
        # Perform rebase
        temp_branch = f"rebase_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not self.interactive_rebase(base_commit, selected_commits):
            self.log("Rebase failed")
            return False
        
        # Force push
        if not self.force_push_rebased_branch():
            self.log("Force push failed")
            return False
        
        # Cleanup
        self.cleanup_rebase(temp_branch)
        
        # Generate report
        report = self.generate_rebase_report(selected_commits, base_commit, "main")
        
        print("\n" + "=" * 80)
        print("REBASE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Commits processed: {len(selected_commits)}")
        print(f"Report generated: {report}")
        print("\nIMPORTANT: Notify all team members immediately!")
        
        return True

def main():
    """Main rebase procedure"""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        rebase = RebaseProcedure(repo_path)
    else:
        rebase = RebaseProcedure()
    
    try:
        success = rebase.interactive_rebase_workflow()
        if success:
            print("\n✅ Rebase procedure completed successfully")
        else:
            print("\n❌ Rebase procedure failed or cancelled")
            sys.exit(1)
    except KeyboardInterrupt:
        rebase.log("\nRebase procedure interrupted by user")
        sys.exit(1)
    except Exception as e:
        rebase.log(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
