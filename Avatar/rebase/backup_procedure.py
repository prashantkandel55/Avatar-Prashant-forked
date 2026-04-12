#!/usr/bin/env python3
"""
Avatar Project - Repository Backup Procedure
Comprehensive backup system for rollback/rebase safety
"""

import os
import sys
import subprocess
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

class BackupProcedure:
    """Comprehensive backup procedure for repository safety"""
    
    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.backup_dir = self.repo_path / "Avatar/rebase/backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
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
    
    def create_full_backup(self):
        """Create complete repository backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"avatar_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        self.log(f"Creating full backup: {backup_path}")
        
        try:
            # Create backup directory
            backup_path.mkdir(exist_ok=True)
            
            # Backup Git repository
            git_backup = backup_path / ".git"
            if (self.repo_path / ".git").exists():
                self.log("Backing up Git repository...")
                shutil.copytree(self.repo_path / ".git", git_backup, ignore=shutil.ignore_patterns('.DS_Store'))
            
            # Backup source code (excluding .git and large files)
            self.log("Backing up source code...")
            
            # Create source backup excluding certain directories
            source_backup = backup_path / "source"
            source_backup.mkdir(exist_ok=True)
            
            # Copy important files and directories
            important_items = [
                "*.qml", "*.py", "*.js", "*.css", "*.md",
                "GUI5.py", "main.qml", "README.md",
                "Avatar/", "UI/", "NAO6/", "Nao.mesh/"
            ]
            
            for item in important_items:
                src = self.repo_path / item
                if src.exists():
                    if src.is_file():
                        shutil.copy2(src, source_backup / src.name)
                    elif src.is_dir():
                        shutil.copytree(src, source_backup / src.name, 
                                       ignore=shutil.ignore_patterns('.DS_Store', '__pycache__', '.git', 'venv'))
            
            # Backup configuration files
            self.log("Backing up configuration...")
            config_files = [
                ".gitignore", "requirements.txt", "package.json",
                "*.project", "*.pro", "CMakeLists.txt"
            ]
            
            for pattern in config_files:
                for file_path in self.repo_path.glob(pattern):
                    shutil.copy2(file_path, backup_path / file_path.name)
            
            # Create backup metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'type': 'full_backup',
                'repo_path': str(self.repo_path),
                'git_status': self.get_git_status(),
                'current_branch': self.get_current_branch(),
                'last_commit': self.get_last_commit(),
                'backup_size': self.calculate_backup_size(backup_path)
            }
            
            with open(backup_path / "backup_metadata.json", 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            # Create compressed archive
            self.log("Creating compressed archive...")
            archive_path = self.backup_dir / f"{backup_name}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_name)
            
            # Remove uncompressed backup
            shutil.rmtree(backup_path)
            
            self.log(f"Full backup completed: {archive_path}")
            self.log(f"Backup size: {metadata['backup_size']}")
            
            return archive_path
            
        except Exception as e:
            self.log(f"Backup failed: {e}")
            return None
    
    def create_git_bare_backup(self):
        """Create bare Git backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"avatar_git_bare_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        self.log(f"Creating bare Git backup: {backup_path}")
        
        try:
            # Create bare clone
            result = self.run_command(f"git clone --bare . {backup_path}")
            if not result:
                self.log("Bare clone failed")
                return None
            
            # Create backup metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'type': 'git_bare_backup',
                'repo_path': str(self.repo_path),
                'current_branch': self.get_current_branch(),
                'last_commit': self.get_last_commit()
            }
            
            with open(backup_path / "backup_metadata.json", 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            self.log(f"Bare Git backup completed: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.log(f"Bare backup failed: {e}")
            return None
    
    def create_incremental_backup(self):
        """Create incremental backup (changes since last backup)"""
        self.log("Creating incremental backup...")
        
        # Find last backup
        last_backup = self.find_last_backup()
        if not last_backup:
            self.log("No previous backup found, creating full backup")
            return self.create_full_backup()
        
        # Get changes since last backup
        last_commit = self.get_backup_last_commit(last_backup)
        if not last_commit:
            self.log("Could not determine last backup commit, creating full backup")
            return self.create_full_backup()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"avatar_incremental_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            backup_path.mkdir(exist_ok=True)
            
            # Get changed files since last backup
            result = self.run_command(f"git diff --name-only {last_commit} HEAD")
            if not result:
                self.log("No changes since last backup")
                return None
            
            changed_files = result.stdout.strip().split('\n')
            self.log(f"Found {len(changed_files)} changed files")
            
            # Copy changed files
            for file_path in changed_files:
                if file_path.strip():
                    src = self.repo_path / file_path
                    if src.exists():
                        dst = backup_path / file_path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
            
            # Create incremental backup metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'type': 'incremental_backup',
                'base_commit': last_commit,
                'changed_files': changed_files,
                'repo_path': str(self.repo_path)
            }
            
            with open(backup_path / "backup_metadata.json", 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            self.log(f"Incremental backup completed: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.log(f"Incremental backup failed: {e}")
            return None
    
    def get_git_status(self):
        """Get current Git status"""
        result = self.run_command("git status --porcelain")
        if result:
            return result.stdout.strip()
        return ""
    
    def get_current_branch(self):
        """Get current Git branch"""
        result = self.run_command("git branch --show-current")
        if result:
            return result.stdout.strip()
        return ""
    
    def get_last_commit(self):
        """Get last commit hash and message"""
        result = self.run_command("git log -1 --pretty=format:'%H|%s'")
        if result:
            parts = result.stdout.strip().split('|')
            if len(parts) >= 2:
                return {'hash': parts[0], 'message': parts[1]}
        return {}
    
    def find_last_backup(self):
        """Find the most recent backup"""
        backups = list(self.backup_dir.glob("avatar_*"))
        if not backups:
            return None
        
        return max(backups, key=lambda x: x.stat().st_mtime)
    
    def get_backup_last_commit(self, backup_path):
        """Get commit hash from backup metadata"""
        metadata_file = backup_path / "backup_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    import json
                    metadata = json.load(f)
                    if 'last_commit' in metadata:
                        if isinstance(metadata['last_commit'], dict):
                            return metadata['last_commit'].get('hash', '')
                        return metadata['last_commit']
            except:
                pass
        return ""
    
    def calculate_backup_size(self, backup_path):
        """Calculate backup size in human readable format"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(backup_path):
            for filename in filenames + dirnames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):
                    total_size += os.path.getsize(filepath)
        
        # Convert to human readable
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.2f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.2f} TB"
    
    def list_backups(self):
        """List all available backups"""
        self.log("Listing available backups...")
        
        backups = []
        for backup_path in self.backup_dir.glob("avatar_*"):
            if backup_path.is_dir() or backup_path.suffix in ['.tar.gz']:
                metadata_file = backup_path / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            import json
                            metadata = json.load(f)
                            backups.append({
                                'path': backup_path,
                                'metadata': metadata
                            })
                    except:
                        pass
        
        # Sort by timestamp
        backups.sort(key=lambda x: x['metadata'].get('timestamp', ''), reverse=True)
        
        print("\n" + "=" * 80)
        print("AVAILABLE BACKUPS")
        print("=" * 80)
        
        for i, backup in enumerate(backups, 1):
            metadata = backup['metadata']
            print(f"\n{i}. {backup['path'].name}")
            print(f"   Type: {metadata.get('type', 'Unknown')}")
            print(f"   Date: {metadata.get('timestamp', 'Unknown')}")
            print(f"   Size: {metadata.get('backup_size', 'Unknown')}")
            if 'last_commit' in metadata:
                commit = metadata['last_commit']
                if isinstance(commit, dict):
                    print(f"   Commit: {commit.get('hash', 'Unknown')[:8]} - {commit.get('message', 'Unknown')[:30]}")
                else:
                    print(f"   Commit: {commit[:8]}")
        
        return backups
    
    def restore_backup(self, backup_path):
        """Restore from backup"""
        self.log(f"Restoring from backup: {backup_path}")
        
        if not backup_path.exists():
            self.log("ERROR: Backup not found")
            return False
        
        try:
            # If it's a compressed archive, extract first
            if backup_path.suffix == '.gz':
                extract_path = self.backup_dir / backup_path.stem
                self.log(f"Extracting archive to: {extract_path}")
                
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(extract_path)
                
                backup_path = extract_path
            
            # Verify backup metadata
            metadata_file = backup_path / "backup_metadata.json"
            if not metadata_file.exists():
                self.log("WARNING: No backup metadata found")
            
            # Create safety backup of current state
            self.log("Creating safety backup of current state...")
            safety_backup = self.create_full_backup()
            
            # Restore Git repository
            git_backup = backup_path / ".git"
            if git_backup.exists():
                self.log("Restoring Git repository...")
                if (self.repo_path / ".git").exists():
                    shutil.rmtree(self.repo_path / ".git")
                shutil.copytree(git_backup, self.repo_path / ".git")
            
            # Restore source files
            source_backup = backup_path / "source"
            if source_backup.exists():
                self.log("Restoring source files...")
                for item in source_backup.glob('*'):
                    if item.is_file():
                        shutil.copy2(item, self.repo_path / item.name)
                    elif item.is_dir():
                        dst = self.repo_path / item.name
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(item, dst)
            
            self.log("Restore completed successfully")
            return True
            
        except Exception as e:
            self.log(f"Restore failed: {e}")
            return False

def main():
    """Main backup procedure"""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        backup = BackupProcedure(repo_path)
    else:
        backup = BackupProcedure()
    
    print("=" * 80)
    print("Avatar Project - Repository Backup Procedure")
    print("=" * 80)
    
    if len(sys.argv) > 2:
        action = sys.argv[2].lower()
        
        if action == "list":
            backup.list_backups()
        elif action == "restore" and len(sys.argv) > 3:
            backup_path = Path(sys.argv[3])
            backup.restore_backup(backup_path)
        else:
            print("Usage:")
            print("  python backup_procedure.py [repo_path] [action] [backup_path]")
            print("")
            print("Actions:")
            print("  list     - List available backups")
            print("  restore  - Restore from backup path")
            print("")
            print("Examples:")
            print("  python backup_procedure.py . list")
            print("  python backup_procedure.py . restore /path/to/backup")
    else:
        # Interactive backup creation
        print("Select backup type:")
        print("1. Full backup (complete repository)")
        print("2. Bare Git backup (Git repository only)")
        print("3. Incremental backup (changes since last backup)")
        print("4. List available backups")
        print("5. Restore from backup")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            backup.create_full_backup()
        elif choice == "2":
            backup.create_git_bare_backup()
        elif choice == "3":
            backup.create_incremental_backup()
        elif choice == "4":
            backup.list_backups()
        elif choice == "5":
            backup_path = input("Enter backup path: ").strip()
            backup.restore_backup(Path(backup_path))
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
