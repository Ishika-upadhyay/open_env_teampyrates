from typing import List
from pydantic import BaseModel

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
            self.cars = [
                CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=30.0, hours_until_deadline=10)
            ]
            
        #medium mode setup
        elif self.difficulty == "medium":
            self.grid_limit = 50.0
            self.price_curve = [0.30, 0.30, 0.25, 0.15, 0.10, 0.10, 0.15, 0.20, 0.25, 0.30]
            self.cars = [
                CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=30.0, hours_until_deadline=10),
                CarState(car_id=2, current_charge_kwh=10.0, target_charge_kwh=40.0, hours_until_deadline=8),
                CarState(car_id=3, current_charge_kwh=5.0, target_charge_kwh=20.0, hours_until_deadline=5)
            ]
            
        #hard mode setup
        elif self.difficulty == "hard":
            self.grid_limit = 40.0
            self.price_curve = [0.50, 0.10, 0.40, 0.10, 0.50, 0.10, 0.40, 0.10, 0.50, 0.10]
            self.cars = [
                CarState(car_id=1, current_charge_kwh=0.0, target_charge_kwh=20.0, hours_until_deadline=4),
                CarState(car_id=2, current_charge_kwh=0.0, target_charge_kwh=20.0, hours_until_deadline=6),
                CarState(car_id=3, current_charge_kwh=0.0, target_charge_kwh=20.0, hours_until_deadline=8),
                CarState(car_id=4, current_charge_kwh=10.0, target_charge_kwh=30.0, hours_until_deadline=5),
                CarState(car_id=5, current_charge_kwh=20.0, target_charge_kwh=40.0, hours_until_deadline=10)
            ]

        return self.state()
        
    #this will return the current variables to AI

    def state(self) -> EVObservation:
        current_price = self.price_curve[self.current_hour] if self.current_hour < 10 else 0.0
        
        return EVObservation(
            current_hour=self.current_hour,
            current_price_per_kwh=current_price,
            grid_max_kw=self.grid_limit,
            cars=self.cars
        )

    #this is the main physics engine

    def step(self, action: EVAction) -> tuple[EVObservation, Reward, bool, dict]:
        
        #check if grid is overload and fail if true
        total_kw_requested = sum(action.charge_allocations_kw)
        if total_kw_requested > self.grid_limit:
            self.is_done = True
            return self.state(), Reward(score=0.0, message="FAIL: Grid Overload!"), self.is_done, {}

        #add power to cars and take money
        current_price = self.price_curve[self.current_hour]
        for i, car in enumerate(self.cars):
            power_given = action.charge_allocations_kw[i]
            
            #stop car from overcharging
            if car.current_charge_kwh + power_given > car.target_charge_kwh:
                power_given = car.target_charge_kwh - car.current_charge_kwh
                
            car.current_charge_kwh += power_given
            self.total_spent += (power_given * current_price)
            car.hours_until_deadline -= 1
            
            #fail if deadline is missed
            if car.hours_until_deadline <= 0 and car.current_charge_kwh < car.target_charge_kwh:
                self.is_done = True
                return self.state(), Reward(score=0.1, message=f"FAIL: Car {car.car_id} missed deadline!"), self.is_done, {}

        #move time by 1 hour
        self.current_hour += 1
        
        #check if 10 hours are done and calculate final score
        if self.current_hour >= 10:
            self.is_done = True
            return self.state(), Reward(score=1.0, message="Shift complete!"), self.is_done, {"total_spent": self.total_spent}
            
        return self.state(), Reward(score=0.5, message="Running cleanly."), self.is_done, {"total_spent": self.total_spent}

   