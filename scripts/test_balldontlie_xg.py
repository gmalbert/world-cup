"""
Test script to verify BALLDONTLIE API xG data availability.
Checks 2022 World Cup data for xG values.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
BASE_URL = "https://fifa.balldontlie.io/api/v1"

def test_api_connection():
    """Test basic API connectivity."""
    if not API_KEY:
        print("❌ ERROR: BALLDONTLIE_API_KEY not found in .env file")
        return False
    
    print(f"✅ API Key found: {API_KEY[:20]}...")
    
    try:
        url = f"{BASE_URL}/matches"
        headers = {"Authorization": API_KEY}  # Match actual client format
        params = {"season": 2022, "per_page": 5}
        
        print(f"\n📡 Testing API endpoint: {url}")
        print(f"   Parameters: season=2022, per_page=5")
        
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        print(f"\n✅ API Response successful!")
        print(f"   Status Code: {resp.status_code}")
        
        # Check if data exists
        matches = data.get("data", [])
        if not matches:
            print("\n⚠️  WARNING: No match data returned for 2022 season")
            print("   The BALLDONTLIE API may not have 2022 World Cup data yet.")
            return False
        
        print(f"\n📊 Found {len(matches)} matches")
        
        # Check for xG data in first few matches
        xg_count = 0
        for i, match in enumerate(matches[:3], 1):
            home_team = match.get("home_team", {}).get("name", "Unknown")
            away_team = match.get("away_team", {}).get("name", "Unknown")
            home_xg = match.get("home_xg")
            away_xg = match.get("away_xg")
            
            print(f"\n   Match {i}: {home_team} vs {away_team}")
            print(f"      home_xg: {home_xg if home_xg is not None else 'NULL'}")
            print(f"      away_xg: {away_xg if away_xg is not None else 'NULL'}")
            
            if home_xg is not None or away_xg is not None:
                xg_count += 1
        
        if xg_count == 0:
            print("\n❌ ISSUE: No xG data found in any matches!")
            print("   The BALLDONTLIE API does NOT provide xG data for World Cup matches.")
            print("   The message in Statistics page is MISLEADING.")
            return False
        else:
            print(f"\n✅ xG data found in {xg_count}/{len(matches[:3])} checked matches")
            return True
            
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        print(f"\n❌ HTTP Error {code}")
        if code == 401:
            print("   Invalid API key")
        elif code == 429:
            print("   Rate limit reached")
        else:
            print(f"   {e}")
        return False
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("BALLDONTLIE FIFA API - xG Data Verification Test")
    print("=" * 70)
    
    result = test_api_connection()
    
    print("\n" + "=" * 70)
    if result:
        print("✅ RESULT: xG data IS available from BALLDONTLIE API")
    else:
        print("❌ RESULT: xG data is NOT available from BALLDONTLIE API")
        print("\nRECOMMENDATION:")
        print("- Update Statistics page to remove misleading xG data message")
        print("- Consider using API-Football or another provider for xG data")
        print("- Or implement model-based xG using Dixon-Coles")
    print("=" * 70)
