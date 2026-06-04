# 🚀 FastAdmin Quick Start Guide

This guide will walk you through setting up and running the FastAdmin API and Admin Panel.

---

## 🛠 1. Backend Setup (FastAPI)

The backend is located in the `/api` directory.

### Step 1: Environment Setup
Navigate to the api directory and activate your virtual environment:
```powershell
cd "C:\Users\samra\Desktop\Client Dev\BlogAgent\FastAdmin\api"
.\env\Scripts\activate
```

### Step 2: Install Dependencies
Ensure you have all required packages installed:
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create a `.env` file in the `/api` directory. You can copy `.env.example` or use these minimum required values for development:
```env
SECRET_KEY=your_random_secret_key
JWT_SECRET=your_random_jwt_secret
ENVIRONMENT=development
DEBUG=True
DB_ENGINE=sqlite
DB_PATH=./db.sqlite3
```

### Step 4: Run the API
Start the production server:
```powershell
fastapi run main.py
```
The API will be available at `http://0.0.0.0:8000`.

---

## 👤 2. User & Admin Management (CLI)

Since the system is secure, you cannot log in without an account. Use the CLI tool to create your first admin. **Run these commands from the `/api` directory.**

### Create a Superuser (Full Admin Access)
```powershell
$env:PYTHONPATH = "."; python cli/create_user.py --username admin --email admin@example.com --password admin123 --superuser --staff
```

### Create a Regular User
```powershell
$env:PYTHONPATH = "."; python cli/create_user.py --username user1 --email user1@example.com --password user123
```

**CLI Parameter Guide:**
- `--username`: The login name.
- `--email`: The user's email address.
- `--password`: The plain-text password.
- `--superuser`: (Flag) Grants full system-wide permissions.
- `--staff`: (Flag) Allows the user to log into the administrative area.

---

## 💻 3. Frontend Setup (Next.js)

The admin panel is located in the `/admin` directory.

### Step 1: Install Dependencies
Navigate to the admin directory and install packages:
```powershell
cd "C:\Users\samra\Desktop\Client Dev\BlogAgent\FastAdmin\admin"
npm install
```

### Step 2: Run in Development Mode
Start the Next.js development server:
```powershell
npm run dev
```
The Admin Panel will be available at `http://localhost:7000`.

---

## 🧪 4. Verification Checklist

1.  **API Health:** Open `http://localhost:8000/docs` to see the Swagger UI.
2.  **Admin Access:** Go to `http://localhost:7000` and log in with the superuser credentials you created in the CLI step.
3.  **Database:** Check that `db.sqlite3` has been created in the `/api` folder.

## ⚠️ Common Troubleshooting

| Issue | Solution |
| :--- | :--- |
| `ModuleNotFoundError: No module named 'core'` | Use `$env:PYTHONPATH = "."` before running Python scripts. |
| `ValidationError: SECRET_KEY Field required` | Ensure your `.env` file exists in the `/api` folder. |
| `InvalidRequestError` (SQLAlchemy) | Ensure you are using the latest version of the code where `Model` is marked as `__abstract__`. |
| `npm install` fails on `check-node.js` | Ensure you are using Node.js v20, v22, or v24. |
