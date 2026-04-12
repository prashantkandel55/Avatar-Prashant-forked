#!/usr/bin/env python3
"""
Avatar Project - Pre-Rollback/Rebase Safety Checks
Comprehensive validation before dangerous Git operations
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

class SafetyChecks:
    """Pre-operation safety validation for Git operations"""
    
    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.issues = []
        self.warnings = []
        self.blockers = []
        
    def add_issue(self, severity, message, suggestion=None):
        """Add safety issue"""
        issue = {
            'severity': severity,
            'message': message,
            'suggestion': suggestion,
            'timestamp': datetime.now().isoformat()
        }
        
        if severity == 'blocker':
            self.blockers.append(issue)
        elif severity == 'warning':
            self.warnings.append(issue)
        else:
            self.issues.append(issue)
    
    def check_repository_state(self):
        """Check repository state and health"""
        print("🔍 Checking repository state...")
        
        # Check if we're in a git repository
        if not (self.repo_path / ".git").exists():
            self.add_issue('blocker', "Not in a Git repository", 
                        "Initialize with 'git init' or navigate to correct directory")
            return False
        
        # Check for uncommitted changes
        result = self.run_command("git status --porcelain")
        if result and result.stdout.strip():
            uncommitted = len(result.stdout.strip().split('\n'))
            self.add_issue('warning', f"{uncommitted} uncommitted changes detected",
                        "Commit or stash changes before proceeding")
        
        # Check for stashed changes
        result = self.run_command("git stash list")
        if result and result.stdout.strip():
            stash_count = len([line for line in result.stdout.strip().split('\n') if line.strip()])
            if stash_count > 0:
                self.add_issue('info', f"{stash_count} stashed changes found",
                            "Consider if these should be applied")
        
        # Check current branch
        result = self.run_command("git branch --show-current")
        if result:
            current_branch = result.stdout.strip()
            self.add_issue('info', f"Current branch: {current_branch}")
            
            # Check if branch is protected
            result = self.run_command(f"git config branch.{current_branch}.protected")
            if result and result.stdout.strip() == "true":
                self.add_issue('warning', f"Branch '{current_branch}' is protected",
                            "Use temporary branch for operations")
        
        return True
    
    def check_remote_state(self):
        """Check remote repository state"""
        print("🌐 Checking remote repository state...")
        
        # Check remote connection
        result = self.run_command("git remote -v")
        if not result:
            self.add_issue('blocker', "No remote repository configured",
                        "Add remote with 'git remote add origin <url>'")
            return False
        
        # Check if remote is reachable
        result = self.run_command("git ls-remote origin")
        if not result:
            self.add_issue('warning', "Remote repository not reachable",
                        "Check network connection and remote URL")
        else:
            self.add_issue('info', "Remote repository reachable")
        
        # Check for unpushed commits
        result = self.run_command("git log --oneline origin/HEAD..HEAD")
        if result and result.stdout.strip():
            unpushed = len(result.stdout.strip().split('\n'))
            self.add_issue('warning', f"{unpushed} commits not pushed to remote",
                        "Push or consider these in your plan")
        
        return True
    
    def check_branch_protection(self):
        """Check branch protection and permissions"""
        print("🛡️ Checking branch protection...")
        
        # Get current branch
        result = self.run_command("git branch --show-current")
        if not result:
            self.add_issue('error', "Could not determine current branch")
            return False
        
        current_branch = result.stdout.strip()
        
        # Check if force push is allowed
        result = self.run_command(f"git config branch.{current_branch}.protected")
        if result and result.stdout.strip() == "true":
            self.add_issue('blocker', f"Branch '{current_branch}' is protected",
                        "Use temporary branch or disable protection temporarily")
        
        # Check for required status checks
        result = self.run_command(f"git config branch.{current_branch}.requiredStatusChecks")
        if result and result.stdout.strip():
            checks = result.stdout.strip().split(',')
            self.add_issue('warning', f"Branch has required status checks: {', '.join(checks)}",
                        "Ensure your changes will pass these checks")
        
        return True
    
    def check_collaborator_activity(self):
        """Check for recent collaborator activity"""
        print("👥 Checking collaborator activity...")
        
        # Get recent commits from all authors
        result = self.run_command("git log --since='1 week ago' --pretty=format:'%an' | sort | uniq -c")
        if result:
            authors = result.stdout.strip().split('\n')
            if len(authors) > 1:
                self.add_issue('warning', f"Multiple active collaborators: {len(authors)}",
                            "Coordinate with team before history rewrite")
            
            # Check for recent commits from others
            result = self.run_command("git log --since='2 days ago' --pretty=format:'%an|%H' --author=!$(git config user.name)")
            if result and result.stdout.strip():
                self.add_issue('blocker', "Recent commits from other collaborators detected",
                            "Wait for them to push or coordinate carefully")
        
        return True
    
    def check_ci_cd_status(self):
        """Check CI/CD pipeline status"""
        print("🔄 Checking CI/CD status...")
        
        # Check for GitHub Actions or other CI files
        ci_files = [
            ".github/workflows/",
            ".gitlab-ci.yml",
            ".travis.yml",
            "Jenkinsfile",
            "azure-pipelines.yml"
        ]
        
        ci_found = False
        for ci_file in ci_files:
            if (self.repo_path / ci_file).exists():
                self.add_issue('info', f"CI/CD configuration found: {ci_file}")
                ci_found = True
        
        if not ci_found:
            self.add_issue('info', "No CI/CD configuration detected")
        
        # Check for recent CI runs (if GitHub)
        if (self.repo_path / ".github" / "workflows").exists():
            self.add_issue('info', "GitHub Actions detected - check recent runs in repository")
        
        return True
    
    def check_disk_space(self):
        """Check available disk space"""
        print("💾 Checking disk space...")
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.repo_path)
            free_gb = free // (1024**3)
            total_gb = total // (1024**3)
            free_percent = (free / total) * 100
            
            self.add_issue('info', f"Disk space: {free_gb:.1f}GB free ({free_percent:.1f}%)")
            
            if free_gb < 1:  # Less than 1GB free
                self.add_issue('warning', "Low disk space available",
                            "Free up space before proceeding")
            
        except Exception as e:
            self.add_issue('error', f"Could not check disk space: {e}")
        
        return True
    
    def check_git_configuration(self):
        """Check Git configuration"""
        print("⚙️ Checking Git configuration...")
        
        # Check user identity
        result = self.run_command("git config user.name")
        if not result or not result.stdout.strip():
            self.add_issue('warning', "Git user.name not configured",
                        "Set with 'git config user.name \"Your Name\"'")
        else:
            self.add_issue('info', f"Git user: {result.stdout.strip()}")
        
        result = self.run_command("git config user.email")
        if not result or not result.stdout.strip():
            self.add_issue('warning', "Git user.email not configured",
                        "Set with 'git config user.email \"your@email.com\"'")
        
        # Check for dangerous settings
        result = self.run_command("git config --get core.autocrlf")
        if result and result.stdout.strip() == "false":
            self.add_issue('info', "core.autocrlf is false - line ending issues possible")
        
        # Check for force push settings
        result = self.run_command("git config --get receive.denyNonFastForwards")
        if result and result.stdout.strip() == "false":
            self.add_issue('warning', "Non-fast-forward pushes allowed - history rewrite possible")
        
        return True
    
    def run_command(self, command):
        """Run git command safely"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result
        except Exception as e:
            print(f"Command failed: {e}")
            return None
    
    def generate_safety_report(self):
        """Generate comprehensive safety report"""
        print("\n" + "=" * 80)
        print("SAFETY CHECK REPORT")
        print("=" * 80)
        
        # Run all checks
        self.check_repository_state()
        self.check_remote_state()
        self.check_branch_protection()
        self.check_collaborator_activity()
        self.check_ci_cd_status()
        self.check_disk_space()
        self.check_git_configuration()
        
        # Display results
        if self.blockers:
            print("\n🚨 BLOCKERS (Must resolve before proceeding):")
            for issue in self.blockers:
                print(f"  ❌ {issue['message']}")
                if issue.get('suggestion'):
                    print(f"     💡 {issue['suggestion']}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS (Proceed with caution):")
            for issue in self.warnings:
                print(f"  ⚠️ {issue['message']}")
                if issue.get('suggestion'):
                    print(f"     💡 {issue['suggestion']}")
        
        if self.issues:
            print("\nℹ️ INFORMATION:")
            for issue in self.issues:
                print(f"  ℹ️ {issue['message']}")
                if issue.get('suggestion'):
                    print(f"     💡 {issue['suggestion']}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  Blockers: {len(self.blockers)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Info: {len(self.issues)}")
        
        # Recommendation
        if self.blockers:
            print(f"\n🛑 RECOMMENDATION: DO NOT PROCEED")
            print("   Resolve all blockers before continuing with rollback/rebase")
            return False
        elif self.warnings:
            print(f"\n⚠️ RECOMMENDATION: PROCEED WITH CAUTION")
            print("   Address warnings and have backup plan ready")
            return True
        else:
            print(f"\n✅ RECOMMENDATION: SAFE TO PROCEED")
            print("   Repository appears ready for rollback/rebase operations")
            return True
    
    def save_report(self, proceed):
        """Save safety report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.repo_path / "Avatar/rebase/logs" / f"safety_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'proceed_recommended': proceed,
            'blockers': self.blockers,
            'warnings': self.warnings,
            'issues': self.issues,
            'repository_path': str(self.repo_path)
        }
        
        # Ensure logs directory exists
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Safety report saved: {report_file}")
        return report_file

def main():
    """Main safety check procedure"""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        safety = SafetyChecks(repo_path)
    else:
        safety = SafetyChecks()
    
    print("=" * 80)
    print("Avatar Project - Pre-Rollback/Rebase Safety Checks")
    print("=" * 80)
    
    proceed = safety.generate_safety_report()
    
    if not proceed:
        print("\n❌ Safety checks failed - aborting operation")
        sys.exit(1)
    else:
        print("\n✅ Safety checks passed - operation can proceed")
        sys.exit(0)

if __name__ == "__main__":
    main()
