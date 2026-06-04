# 🛠 FastAdmin CLI: User Creation Guide

A quick reference for creating users and administrators via the command line.

## 🚀 Quick Start

Run these commands from the `FastAdmin/api` directory.

### 1. Create a Superuser (Admin)
**Use this to create your first account to access the Admin Panel.**
```powershell
$env:PYTHONPATH = "."; python -m cli.create_user --username admin --email admin@admin.com --password admin --superuser --staff
```

### 2. Create a Regular User
```powershell
$env:PYTHONPATH = "."; python -m cli/create_user.py --username user --email user@user.com --password user
```

---

## 📖 Parameter Reference

| Flag | Requirement | Description |
| :--- | :--- | :--- |
| `--username` | **Required** | Unique login name for the user. |
| `--email` | **Required** | Unique email address. |
| `--password` | **Required** | Plain-text password (will be hashed). |
| `--superuser` | Optional | Grants full system-wide administrative rights. |
| `--staff` | Optional | Allows the user to log into the Admin interface. |

## ⚠️ Troubleshooting

**Error:** `ModuleNotFoundError: No module named 'core'`
**Fix:** You must set the `PYTHONPATH` so Python can find your project modules. Always prefix the command with:
`$env:PYTHONPATH = ".";` (PowerShell)
or
`export PYTHONPATH=.` (Bash/Linux)
