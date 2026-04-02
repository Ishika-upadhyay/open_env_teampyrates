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

    

   