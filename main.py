import mesa
import random
import math






class Entreprise(mesa.Agent):
    def __init__(self, model: mesa.Model, name, purpose, labor, price):
        super().__init__(model)
        self.name = name
        self.purpose = purpose # Soit : agrifood, food_raw_material 
        self.labor = labor
        self.step_labor = 0
        self.total_labor = 0
        self.employees: list[Individual] = []
        self.products = {
            "wheet" : 0.0,
            "bread" : 0.0
        }
        self.step_production = 0
        self.step_sold = 0
        self.step_demanded = 0
        self.product_price = price
        self.sold = 0
        self.money = 10000

    def add_labour(self, work_done):
        self.step_labor += work_done
        self.total_labor += work_done


    def request_work(self, individual):
        
        if (True):
            individual.working_at = self
            self.employees.append(individual)
            return True
        return False
    
    def produce(self):
        if self.purpose == "food_raw_material":
            self.products["wheet"] += self.step_labor / self.labor
            self.step_production += self.step_labor / self.labor
        
        elif self.purpose == "agrifood":
            production = min(self.step_labor/self.labor, self.products.get("wheet")/3)
            self.products["bread"] += production
            self.products['wheet'] -= production* 3
            self.step_production += production

    def set_price(self):
        if self.step_demanded > self.step_sold * 0.95:
            self.product_price *= 1.05
        elif self.step_sold < self.step_production * 0.8:
            if self.product_price > (self.labor + 3) * 1.1:
                self.product_price *= 0.95

            



    def intermediary_consumption(self):
        if self.purpose == "agrifood":
            fournisseurs: list[Entreprise] = self.model.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "food_raw_material")
            fournisseurs = fournisseurs.sort("product_price")

            if self.products['wheet']/3 < self.step_labor/self.labor:
                wheet_needed = (self.step_labor/self.labor - self.products['wheet']/3)*3
                i = 0
                while wheet_needed > 0 and self.money > 0:
                    wheet_to_buy = min(fournisseurs[i].products['wheet'], wheet_needed)
                    wheet_price = min(wheet_to_buy*fournisseurs[i].product_price, self.money)

                    fournisseurs[i].step_demanded += wheet_to_buy
                    if self.step_production > self.step_demanded:
                        break

                    if wheet_price == self.money:
                        wheet_to_buy = self.money/fournisseurs[i].product_price
                    
                    fournisseurs[i].money += wheet_price
                    fournisseurs[i].step_sold += wheet_to_buy
                    self.money -= wheet_price

                    fournisseurs[i].products['wheet'] -= wheet_to_buy
                    self.products['wheet'] += wheet_to_buy
                    wheet_needed -= wheet_to_buy
                    
                    i +=1
                    if i >= len(fournisseurs):
                        break

    def income_distribution(self):
        for employee in self.employees:
            if self.money  <= 1.0:
                break
            employee.wealth += employee.current_skill
            self.money -= employee.current_skill
        
    

    
    def step(self):
        self.income_distribution()

        self.intermediary_consumption()

        print(f"Step Production : {self.step_production:.2f}")
        print(f"Step Demanded : {self.step_demanded:.2f}")
        print(f"Step Sold : {self.step_sold:.2f}")

        self.set_price()
        
        self.step_production = 0
        self.produce()

        products_formated = {key: round(value, 2) for key, value in self.products.items()}
        print(f"Id :{self.name} | Money : {self.money:.2f}$ | Products : {products_formated} | Price : {self.product_price:.2f} | Work done {self.step_labor/self.labor:.2f}")

        self.step_sold = 0
        self.step_labor = 0
        self.step_demanded = 0


class Individual(mesa.Agent):
    def __init__(self, model, wealth):
        super().__init__(model)
        self.wealth = wealth
        self.hunger = 100
        self.working_at : Entreprise = None
        self.skills = {
            "food_raw_material" : 1.0,
            "agrifood" : 2.0
        }
        self.inventory = {
            "bread": 0
        }
        self.current_skill = None
    
    def demand_work(self):
        if self.working_at is None:
            entreprise = self.model.agents.select(lambda a: isinstance(a, Entreprise))[random.randint(0, self.model.num_entreprises-1)]
            if entreprise.request_work(self):
                self.current_skill = self.skills.get(self.working_at.purpose)

    def work(self):
        if self.working_at is not None:
            self.current_skill += 0.01
            self.working_at.add_labour(self.current_skill)

    def buy(self, desired_product):
        if desired_product == "bread":
            entreprises: list[Entreprise] = self.model.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "agrifood")
            entreprises = entreprises.sort("product_price")


        if self.inventory['bread'] <= 0:
            product_needed = (100-self.hunger)/25

            
            i = 0
            while product_needed > 0 and self.wealth > 0:
                product_to_buy = min(entreprises[i].products[desired_product], product_needed)
                product_price = min(product_to_buy*entreprises[i].product_price, self.wealth)

                entreprises[i].step_demanded += product_to_buy

                if self.hunger*1.5 > self.wealth:
                    break

                if product_price == self.wealth:
                    product_to_buy = self.wealth/entreprises[i].product_price
                
                entreprises[i].money += product_price
                entreprises[i].step_sold += product_to_buy
                self.wealth -= product_price

                entreprises[i].products[desired_product] -= product_to_buy
                self.inventory[desired_product] += product_to_buy
                product_needed -= product_to_buy
                
                i +=1
                if i >= len(entreprises):
                    break

    def eat(self):
        to_eat = (100-self.hunger)/25

        can_be_eaten = min(to_eat, self.inventory['bread'])
        self.inventory['bread'] -= can_be_eaten
        self.hunger += can_be_eaten*25



    def step(self):
        self.hunger -= 5
        self.demand_work()
        self.work()
        self.buy("bread")
        self.eat()
        # print(f"Id :{self.unique_id} | Money : {self.wealth:.2f}$ | Hunger : {int(self.hunger)} | Working at {self.working_at if self.working_at is None else self.working_at.name}")



class Society(mesa.Model):
    def __init__(self, n, entreprises):
        super().__init__()
        self.num_individuals = n
        self.num_entreprises = len(entreprises)

        for i in range(self.num_individuals):
            Individual(self, 100)
            
        for entreprise in entreprises:
            Entreprise(self, entreprise[0], entreprise[1], entreprise[2], entreprise[3])
    
    def step(self):
        # 1. On récupère uniquement les individus et on les fait agir
        individus = self.agents.select(lambda a: isinstance(a, Individual))
        individus.shuffle_do("step")
        print(f"Moyenne d'argent d'un individu : {sum([individu.wealth for individu in individus])/len(individus):.2f}$")
        print(f"Moyenne de faim : {sum([individu.hunger for individu in individus])/len(individus):.2f}")
        # 2. Une fois que TOUS les individus ont fini, on fait agir les entreprises
        entreprises = self.agents.select(lambda a: isinstance(a, Entreprise))
        entreprises.shuffle_do("step")


society_1 = Society(100, (('WheetCo', "food_raw_material", 1, 1), ('FarmCo', "food_raw_material", 1, 1), ("BreadCo", "agrifood", 2, 1)))



for i in range(100):
    print("Step number :", i,"-------------------------")
    society_1.step()



