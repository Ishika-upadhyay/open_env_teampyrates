from typing import List
from pydantic import BaseModel
import random 

class CarState(BaseModel):
    car_id: int
    current_charge_kwh: float
    target_charge_kwh: float
    hours_until_deadline: int

#this is the car current state that needs to be charged

class EVObservation(BaseModel):
    current_hour: int
    current_price_per_kwh: float
    grid_max_kw: float
    cars: List[CarState]
    # Added for openenv-core v0.2.x compatibility
    reward: float = 0.0
    done: bool = False

#this is the data of all the cars and the contraints

class EVAction(BaseModel):
    charge_allocations_kw: List[float]

#action step by AI

class Reward(BaseModel):
    score: float
    message: str


#environment

class EVFleetEnvironment:
    def __init__(self, difficulty: str = "medium"):
        self.difficulty = difficulty
        self.current_hour = 0
        self.is_done = False
        self.total_spent = 0.0
        
        self.grid_limit = 0.0
        self.price_curve = []
        self.cars = []
        
    #this will set the starting settings

    def reset(self) -> EVObservation:
        self.current_hour = 0
        self.is_done = False
        self.total_spent = 0.0
        
        #easy mode setup
        if self.difficulty == "easy":
            self.grid_limit = 100.0
            self.price_curve = [0.10] * 10 
            self.cars = [CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=30.0, hours_until_deadline=10)]
            
        #medium mode setup
        elif self.difficulty == "medium":
            self.grid_limit = 50.0
            self.price_curve = [0.30, 0.30, 0.25, 0.15, 0.10, 0.10, 0.15, 0.20, 0.25, 0.30]
            self.cars = [
                CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=30.0, hours_until_deadline=10),
                CarState(car_id=2, current_charge_kwh=10.0, target_charge_kwh=40.0, hours_until_deadline=8),
                CarState(car_id=3, current_charge_kwh=5.0, target_charge_kwh=20.0, hours_until_deadline=5)
            ]
            
        #hard mode setup (NOW WITH RANDOMNESS)
        elif self.difficulty == "hard":
            #start with random grid limit between 30 and 60
            self.grid_limit = float(random.randint(30, 60))
            #base price curve, we will add noise later
            self.price_curve = [0.50, 0.10, 0.40, 0.10, 0.50, 0.10, 0.40, 0.10, 0.50, 0.10]
            #start with only 2 cars, more will arrive later
            self.cars = [
                CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=20.0, hours_until_deadline=4),
                CarState(car_id=2, current_charge_kwh=10.0, target_charge_kwh=30.0, hours_until_deadline=6)
            ]
            self.next_car_id = 3

        return self.state()

    def state(self) -> EVObservation:
        current_price = self.price_curve[self.current_hour] if self.current_hour < 10 else 0.0
        
        #add price uncertainty in hard mode (+ or - 5 cents)
        if self.difficulty == "hard" and self.current_hour < 10:
            noise = random.uniform(-0.05, 0.05)
            current_price = max(0.01, current_price + noise)
            
        return EVObservation(
            current_hour=self.current_hour,
            current_price_per_kwh=round(current_price, 2),
            grid_max_kw=float(self.grid_limit),
            cars=self.cars
        )

    def step(self, action: EVAction) -> tuple[EVObservation, Reward, bool, dict]:
        # 1. Basic Validation
        if len(action.charge_allocations_kw) != len(self.cars):
             self.is_done = True
             return self.state(), Reward(score=0.0, message="FAIL: Action array size did not match number of cars!"), self.is_done, {}

        total_kw_requested = sum(action.charge_allocations_kw)
        
        # --- NEW: HACKATHON-SAFE "PUNISH BUT CONTINUE" LOGIC ---
        is_overloaded = False
        step_message = "Running cleanly."

        if total_kw_requested > self.grid_limit:
            is_overloaded = True
            step_message = "PENALTY: Grid Overload! Breaker tripped, zero power delivered."
            # Set action to 0 so the cars don't charge this hour
            action.charge_allocations_kw = [0.0] * len(self.cars)
            total_kw_requested = 0.0 # reset for utilization math below

        # 2. Process Charging and Money
        current_price = self.state().current_price_per_kwh
        
        for i, car in enumerate(self.cars):
            power_given = action.charge_allocations_kw[i]
            
            # Stop car from overcharging
            if car.current_charge_kwh + power_given > car.target_charge_kwh:
                power_given = car.target_charge_kwh - car.current_charge_kwh
                
            car.current_charge_kwh += power_given
            self.total_spent += (power_given * current_price)
            car.hours_until_deadline -= 1
            
            # Fail if deadline is missed
            if car.hours_until_deadline <= 0 and car.current_charge_kwh < car.target_charge_kwh:
                self.is_done = True
                return self.state(), Reward(score=0.1, message=f"FAIL: Car {car.car_id} missed deadline!"), self.is_done, {}

        # 3. Move Time Forward
        self.current_hour += 1

        # 4. Hard Mode Random Events
        if self.difficulty == "hard" and self.current_hour < 10:
            self.grid_limit = float(random.randint(30, 60))
            if random.random() < 0.30:
                new_target = float(random.randint(10, 40))
                new_deadline = random.randint(3, 8)
                self.cars.append(CarState(car_id=self.next_car_id, current_charge_kwh=0.0, target_charge_kwh=new_target, hours_until_deadline=new_deadline))
                self.next_car_id += 1

        # 5. Shift Completion Check (Hour 10)
        if self.current_hour >= 10:
            self.is_done = True
            final_score = 1.0
            
            if self.difficulty == "medium":
                raw_score = 1.0 - ((self.total_spent - 9.0) / (27.0 - 9.0))
                final_score = max(0.1, min(1.0, raw_score))
                
            elif self.difficulty == "hard":
                raw_score = 1.0 - ((self.total_spent - 10.0) / (50.0 - 10.0))
                final_score = max(0.1, min(1.0, raw_score))

            return self.state(), Reward(score=final_score, message="Shift complete!"), self.is_done, {"total_spent": self.total_spent}

        # 6. Step-by-Step Scoring (Hours 1-9)
        if is_overloaded:
            # The ultimate legal punishment for this step
            step_score = 0.0 
        else:
            utilization = total_kw_requested / self.grid_limit if self.grid_limit > 0 else 0
            step_score = 0.4 
            
            if current_price <= 0.15:
                step_score += (utilization * 0.2)  
            elif current_price >= 0.25:
                step_score -= (utilization * 0.2) 
            else:
                step_score += (utilization * 0.05) 

        final_step_score = max(0.0, min(1.0, step_score))
        return self.state(), Reward(score=round(final_step_score, 2), message=step_message), self.is_done, {"total_spent": self.total_spent}
    
# --- OPENENV SERVER INTEGRATION ---
import uuid
from openenv_core.env_server import Environment

try:
    from openenv_core.env_server.types import State
except ImportError:
    class State(BaseModel):
        episode_id: str
        step_count: int

class EVFleetAdapter(Environment):
    def __init__(self):
        self.game = EVFleetEnvironment()
        self.ep_id = str(uuid.uuid4())
        self.steps = 0
        
    def reset(self):
        self.ep_id = str(uuid.uuid4())
        self.steps = 0
        return self.game.reset()
        
    def step(self, action: EVAction):
        obs, reward, done, info = self.game.step(action)
        self.steps += 1
        
        # Merge reward and done directly into the Observation
        obs.reward = reward.score
        obs.done = done
        return obs
        
    @property
    def state(self):
        return State(episode_id=self.ep_id, step_count=self.steps)
   