import subprocess
import sys
import time

def main():
    print("🚀 Starting NewsHub Project...")

    # 1. Start Django Backend on Port 8000
    print("⏳ Starting Backend (Django) on http://127.0.0.1:8000 ...")
    backend_process = subprocess.Popen(
        [sys.executable, "news-backend/manage.py", "runserver", "127.0.0.1:8000"]
    )

    # 2. Start Frontend using Python's built-in HTTP server on Port 5500
    print("⏳ Starting Frontend on http://127.0.0.1:5500 ...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "5500", "--directory", "news-website"]
    )

    try:
        # Jab tak dono chal rahe hain, script wait karegi
        print("\n✅ Dono servers successfully run ho rahe hain!")
        print("➡️ Frontend URL: http://127.0.0.1:5500")
        print("➡️ Backend API:  http://127.0.0.1:8000/api")
        print("\n🛑 Servers ko completely band (kill) karne ke liye 'Ctrl + C' press karein...\n")
        
        backend_process.wait()
        frontend_process.wait()
        
    except KeyboardInterrupt:
        # Jab aap Ctrl+C press karenge toh ye block execute hoga
        print("\n⚠️ Ctrl+C detect hua! Servers ko band (kill) kiya ja raha hai...")
        
        # Dono processes ko terminate karein
        backend_process.terminate()
        frontend_process.terminate()
        
        # Pura close hone ka wait karein taaki ports properly free ho jayein
        backend_process.wait()
        frontend_process.wait()
        
        print("✅ Servers successfully band ho gaye. Ports 8000 aur 5500 ab free hain!")

if __name__ == "__main__":
    main()