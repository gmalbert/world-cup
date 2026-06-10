"""
Run Monte Carlo tournament simulation and save results to JSON.
This script is run nightly by GitHub Actions to pre-compute simulation results.
"""
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from goallineiq_utils.api_client import get_all_wc_matches
from goallineiq_utils.models import build_predictor, WC2026_GROUPS
from goallineiq_utils.simulator import TournamentSimulator

# Configuration
N_SIMULATIONS = 25_000  # Run more sims since it's offline
OUTPUT_FILE = Path(__file__).parent.parent / "data_files" / "tournament_simulation.json"

def run_simulation():
    """Run Monte Carlo simulation and save results."""
    print(f"🎲 Starting Monte Carlo simulation with {N_SIMULATIONS:,} iterations...")
    
    # Load data and build predictor
    print("📊 Loading match data and building predictor...")
    all_matches = get_all_wc_matches()
    predictor = build_predictor(all_matches)
    
    # Run simulation
    print(f"🔄 Running {N_SIMULATIONS:,} tournament simulations...")
    sim = TournamentSimulator(predictor)
    results = sim.run(groups=WC2026_GROUPS, n=N_SIMULATIONS)
    
    # Add rank column
    results["rank"] = range(1, len(results) + 1)
    
    # Convert to JSON-friendly format
    results_dict = results.to_dict(orient="records")
    
    # Create metadata
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_simulations": N_SIMULATIONS,
        "num_teams": len(results),
        "version": "1.0",
    }
    
    # Combine metadata and results
    output = {
        "metadata": metadata,
        "results": results_dict,
    }
    
    # Save to file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Simulation complete! Results saved to {OUTPUT_FILE}")
    print(f"📈 Top 5 contenders:")
    for i, row in enumerate(results.head(5).itertuples(), 1):
        winner_pct = getattr(row, "Winner %", getattr(row, "Winner", 0))
        print(f"   {i}. {row.team}: {winner_pct:.1f}%")

if __name__ == "__main__":
    run_simulation()
