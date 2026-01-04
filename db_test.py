#!/usr/bin/env python3
"""Test script to check database connectivity"""

import socket
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config import config as settings

def test_hostname_resolution():
    """Test if hostname resolves correctly"""
    print("Testing hostname resolution...")
    try:
        ip_address = socket.gethostbyname('localhost')
        print(f"[SUCCESS] localhost resolves to {ip_address}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to resolve localhost: {e}")
        return False

def test_port_connectivity():
    """Test if we can connect to postgresql port"""
    print("\nTesting port connectivity...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex(('127.0.0.1', 5432))
        sock.close()

        if result == 0:
            print("[SUCCESS] Port 5432 is open and accessible")
            return True
        else:
            print("[ERROR] Cannot connect to port 5432 - PostgreSQL might not be running")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing port: {e}")
        return False

async def test_async_db_connection():
    """Test async database connection"""
    print("\nTesting async database connection...")
    try:
        db_url = settings.db.get_url()
        print(f"Database URL: {db_url}")

        engine = create_async_engine(db_url, echo=True)
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        print("[SUCCESS] Async database connection successful!")
        return True
    except Exception as e:
        print(f"[ERROR] Async database connection failed: {e}")
        return False
    finally:
        try:
            await engine.dispose()
        except:
            pass

async def main():
    print("=== Database Connection Test ===")
    
    # Test basic connectivity
    if not test_hostname_resolution():
        print("\nFix your DNS/hostname resolution before proceeding.")
        return
    
    if not test_port_connectivity():
        print("\nMake sure PostgreSQL is running on your system.")
        return
    
    # Test actual database connection
    await test_async_db_connection()

if __name__ == "__main__":
    asyncio.run(main())