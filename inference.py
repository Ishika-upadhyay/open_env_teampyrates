import asyncio
import os
from typing import List, Optional
from openai import OpenAI
from environment import EVFleetEnvironment, EVAction

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
TASK_NAME = "ev-fleet-charging"
BENCHMARK = "openenv-hackathon"
MAX_STEPS = 10

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = EVFleetEnvironment(difficulty="medium")
    
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset()
        for step in range(1, MAX_STEPS + 1):
            if env.is_done:
                break
                
            prompt = f"EV Fleet state: Hour {obs.current_hour}. Limit {obs.grid_max_kw}kW. Cars: {obs.cars}. Reply with ONLY a python list of numbers for power, like [10.0, 5.0, 0.0]."
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                ai_text = response.choices[0].message.content.strip()
                ai_numbers = eval(ai_text)
                action = EVAction(charge_allocations_kw=ai_numbers)
                action_str = str(ai_numbers).replace(" ", "")
                error = None
            except Exception as e:
                action = EVAction(charge_allocations_kw=[0.0, 0.0, 0.0])
                action_str = "[0.0,0.0,0.0]"
                error = "ai_parse_error"

            obs, reward, is_done, info = env.step(action)
            rewards.append(reward.score)
            steps_taken = step
            
            log_step(step=step, action=action_str, reward=reward.score, done=is_done, error=error)
            
            if is_done:
                score = reward.score
                break

        success = score >= 0.5
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())