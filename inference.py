import asyncio
import os
from openai import OpenAI
from environment import EVFleetEnvironment, EVAction

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN")

def log_step(step, action, reward, done):
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    game = EVFleetEnvironment(difficulty="hard")
    obs = game.reset()
    
    print(f"[START] task=ev-fleet-charging env=ev-fleet model={MODEL_NAME}", flush=True)

    rewards = []
    
    for step in range(1, 11):
        if game.is_done: break

        # 1. Give the AI the current rules and prices
        car_info = "\n".join([f"Car {c.car_id}: Needs {c.target_charge_kwh - c.current_charge_kwh} kWh in the next {c.hours_until_deadline} hours." for c in obs.cars])
        
        prompt = f"""
        You manage an EV charging fleet.
        Current Price: ${obs.current_price_per_kwh} per kWh.
        Grid Limit: {obs.grid_max_kw} kW.
        
        {car_info}
        
        Reply ONLY with a comma-separated list of 3 numbers representing the kW to give each car this hour.
        Rule 1: The sum MUST be less than {obs.grid_max_kw}.
        Rule 2: If the price is high ($0.30), try to charge 0.0 unless a deadline is imminent.
        Example output: 10.0, 5.5, 0.0
        """

        # 2. Ask the AI for its move
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20
            )
            reply = completion.choices[0].message.content.strip()
            
            # Clean up the AI's response into a list of floats
            clean_reply = ''.join(c for c in reply if c in '0123456789.,')
            allocations = [float(x) for x in clean_reply.split(",")][:len(obs.cars)]
            
            # Fill missing values with 0.0 if AI glitches
            while len(allocations) < len(obs.cars):
                allocations.append(0.0)
                
        except Exception as e:
            allocations = [0.0, 0.0, 0.0] # Safe fallback

        # 3. Apply the move to the game
        action = EVAction(charge_allocations_kw=allocations)
        obs, reward_obj, done, _ = game.step(action)
        
        rewards.append(reward_obj.score)
        log_step(step, str(allocations), reward_obj.score, done)

    # 4. End the game
    final_score = rewards[-1] if rewards else 0.0
    success = final_score > 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    
    print(f"[END] success={str(success).lower()} steps={len(rewards)} score={final_score:.2f} rewards={rewards_str}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())