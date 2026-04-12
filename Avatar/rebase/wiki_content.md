# GitHub Roll Back and Rebase Procedure

## Overview

This guide provides comprehensive procedures for safely rolling back and rebasing the Avatar project repository. These are advanced Git operations that rewrite history and require careful coordination.

## 🚨 IMPORTANT WARNINGS

### History Rewrite Risks
- **Permanent data loss** if not properly backed up
- **Collaborator conflicts** if not properly coordinated
- **CI/CD pipeline failures** due to changed commit hashes
- **Deployment issues** from history divergence
- **Irreversible changes** once pushed to remote

### When to Use These Procedures
- **Emergency rollbacks** after problematic merges
- **Feature branch cleanup** before major releases
- **History organization** for maintenance
- **Accidental commits** that need removal
- **Branch restructuring** for better workflow

## 📋 Prerequisites Checklist

### Before Any Operation
- [ ] **Team notification sent** via GitHub issues, Slack, or email
- [ ] **Full repository backup** created and verified
- [ ] **Local changes committed** or stashed
- [ ] **Branch protection status** verified
- [ ] **CI/CD pipeline status** checked
- [ ] **Collaborator activity** reviewed
- [ ] **Disk space** verified (minimum 2GB free)
- [ ] **Git configuration** validated
- [ ] **Remote connectivity** confirmed
- [ ] **Rollback plan** documented and approved

### Required Tools
- **Git 2.30+** (for `--force-with-lease` support)
- **Python 3.8+** (for automation scripts)
- **GitHub CLI** (for enhanced operations)
- **Repository admin access**
- **Stable internet connection**

## 🔄 Procedure Selection Guide

### 1. Complete Rollback (git reset --hard)
**Use when:**
- Need to remove entire week's worth of changes
- Starting fresh from specific commit
- Complete history rewrite required
- Major formatting or structural issues

**Risks:** High - Complete history rewrite
**Impact:** All collaborators must update local repos

### 2. Selective Revert (git revert)
**Use when:**
- Need to undo specific merge commits
- Want to preserve history
- Less disruptive approach needed
- Audit trail required

**Risks:** Medium - Creates "revert" commits
**Impact:** Minimal - History preserved

### 3. Interactive Rebase (git rebase -i)
**Use when:**
- Selectively removing specific commits
- Complex history manipulation needed
- Preserving some changes while removing others
- Advanced history editing required

**Risks:** High - Complex history manipulation
**Impact:** High - All collaborators must update

### 4. Branch Recreation
**Use when:**
- Current branch is corrupted
- Need fresh start from specific point
- Branch protection issues
- Emergency recovery

**Risks:** Medium - New branch history
**Impact:** Medium - Requires branch updates

## 🛡️ Safety Procedures

### Pre-Operation Safety Checks
Run safety checks before any operation:

```bash
cd /path/to/avatar
python Avatar/rebase/safety_checks.py
```

**Expected Output:**
- Repository state validation
- Remote connectivity check
- Branch protection status
- Collaborator activity review
- Disk space verification
- Git configuration validation

### Backup Creation
Create comprehensive backup:

```bash
cd /path/to/avatar
python Avatar/rebase/backup_procedure.py
```

**Backup Types:**
1. **Full backup** - Complete repository snapshot
2. **Bare Git backup** - Git repository only
3. **Incremental backup** - Changes since last backup

### Team Communication Template

```markdown
🚨 **EMERGENCY REPOSITORY OPERATIONS** 🚨

**Operation:** [Rollback/Rebase]
**Target:** [Commit hash/branch]
**Timeline:** [Start time] - [End time]
**Reason:** [Detailed explanation]

**Required Actions:**
1. **STOP** all work immediately
2. **DO NOT PUSH** to main branch
3. **FETCH** latest changes: `git fetch origin`
4. **RESET** local repository: `git reset --hard origin/main`
5. **CONTACT** maintainers if issues occur

**Contact:**
- **Primary:** GitHub Issues @3C-SCSU
- **Emergency:** [Direct contact info]
- **Status Updates:** [Team channel]

**Backup Location:** [Backup path]
**Recovery Instructions:** [Recovery steps]
```

## 📝 Step-by-Step Procedures

### Procedure 1: Complete Rollback

#### Step 1: Preparation
```bash
# Navigate to repository
cd /path/to/avatar

# Create safety backup
python Avatar/rebase/backup_procedure.py

# Run safety checks
python Avatar/rebase/safety_checks.py
```

#### Step 2: Identify Target Commit
```bash
# View commit history
git log --oneline --graph -20

# Find commit before unwanted changes
# Note the commit hash (first 7-8 characters)
```

#### Step 3: Perform Rollback
```bash
# Checkout target branch
git checkout main

# Hard reset to target commit
git reset --hard <target-commit-hash>

# Verify reset
git log --oneline -5
```

#### Step 4: Force Push with Lease
```bash
# Force push with safety lease
git push --force-with-lease origin main
```

#### Step 5: Team Notification
- Post notification in GitHub issues
- Send team email/Slack message
- Update project documentation
- Monitor for collaborator issues

### Procedure 2: Selective Revert

#### Step 1: Identify Merge Commits
```bash
# Find merge commits to revert
git log --oneline --grep="Merge"
git log --oneline --merges
```

#### Step 2: Revert Each Merge
```bash
# Revert merge commit (keep main branch parent)
git revert -m 1 <merge-commit-hash>

# Review revert commit
git show HEAD
```

#### Step 3: Push Reverts
```bash
# Push revert commits
git push origin main
```

### Procedure 3: Interactive Rebase

#### Step 1: Preparation
```bash
# Create backup
python Avatar/rebase/backup_procedure.py

# Safety checks
python Avatar/rebase/safety_checks.py

# Update remote
git fetch origin
```

#### Step 2: Start Interactive Rebase
```bash
# Run interactive rebase script
python Avatar/rebase/rebase_procedure.py

# Or manual interactive rebase
git rebase -i <base-commit>
```

#### Step 3: Handle Conflicts
If conflicts occur:
```bash
# Check status
git status

# Resolve conflicts
# [Edit conflicted files]

# Mark as resolved
git add <conflicted-files>

# Continue rebase
git rebase --continue
```

#### Step 4: Complete Rebase
```bash
# Force push rebased branch
git push --force-with-lease origin main
```

## 🚨 Emergency Recovery

### If Rollback Fails
```bash
# Stop all operations
# Identify failure point
# Restore from backup
python Avatar/rebase/backup_procedure.py restore <backup-path>

# Contact maintainers immediately
# Document failure for post-mortem
```

### If Collaborators Have Issues
```bash
# Collaborators should run:
git fetch origin
git reset --hard origin/main

# If still issues:
git clean -fd
git checkout main
git pull origin main --force
```

## 📊 Post-Operation Verification

### Verification Checklist
- [ ] **Repository state** matches expected
- [ ] **No merge conflicts** remaining
- [ ] **CI/CD pipeline** runs successfully
- [ ] **All collaborators** can pull changes
- [ ] **Deployment** works correctly
- [ ] **Documentation** updated
- [ ] **Backup verified** as restorable

### Health Monitoring
Monitor for 24 hours after operation:
- **Pull request activity**
- **CI/CD pipeline status**
- **Collaborator feedback**
- **Deployment logs**
- **Error rates and performance**

## 📞 Support and Escalation

### Primary Contact
- **GitHub Issues:** @3C-SCSU
- **Repository:** Avatar-Prashant-forked
- **Documentation:** This Wiki page

### Emergency Contacts
- **Maintainer 1:** [Contact info]
- **Maintainer 2:** [Contact info]
- **Team Channel:** [Slack/Discord]

### Additional Resources
- **Git Documentation:** https://git-scm.com/docs
- **GitHub Support:** https://support.github.com
- **Advanced Git:** https://git-scm.com/book/en/v2

## 🔄 Continuous Improvement

### Procedure Enhancement
- Document lessons learned from each operation
- Update automation scripts based on feedback
- Improve safety checks and validation
- Enhance team communication templates
- Optimize backup and recovery procedures

### Training and Knowledge Sharing
- Regular team training on Git operations
- Knowledge sharing sessions
- Documentation reviews and updates
- Best practice development and sharing

---

**Last Updated:** April 12, 2026  
**Maintained by:** 3C-SCSU Team  
**Version:** 1.0  
**Repository:** Avatar Project
