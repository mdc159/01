"""
query_o1_feedback.py — One-off script to get architectural feedback from o1.
Uses the unified LLM client already built for the AI Lab.
"""

import logging
from config import Paths, Models
import llm
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

def get_feedback():
    print("Reading architecture document...")
    try:
        context = (Paths.ROOT / "o1_system_prompt.md").read_text()
    except Exception as e:
        print(f"Error reading prompt document: {e}")
        return

    print("Constructing prompt...")
    prompt = (
        "This is the architecture of an autonomous engineering lab where you will act as the "
        "Strategic Planner (CEO). Please review this architecture document:\n\n"
        f"--- DOCUMENT START ---\n{context}\n--- DOCUMENT END ---\n\n"
        "Are there any flaws in the memory hierarchy or the escalation criteria that would "
        "hinder your ability to make good strategic decisions?\n"
        "How should we structure the JSON `project_graph` that you will be expected to output "
        "so that less-capable worker models can effectively execute the tasks?"
    )

    messages = [{"role": "user", "content": prompt}]

    print(f"Querying {Models.STRATEGIC}... (this may take 30+ seconds for deep reasoning)")
    try:
        # Call the o1 model specifically
        response = llm.call(messages, model=Models.STRATEGIC)
        
        print("\n" + "="*80)
        print("💡 o1 FEEDBACK:")
        print("="*80)
        print(response)
        print("="*80 + "\n")
        
        # Save the feedback to an artifact for reference
        feedback_path = Paths.ARTIFACTS / "o1_architecture_feedback.md"
        Paths.ensure_dirs()
        feedback_path.write_text(response)
        print(f"Feedback saved to: {feedback_path}")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error calling o1:\n{e}")
        traceback.print_exc()

if __name__ == "__main__":
    get_feedback()
