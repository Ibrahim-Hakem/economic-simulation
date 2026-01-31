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
        self.last_labor = 0
        self.total_labor = 0
        self.employees: list[Individual] = []
        self.products = {"wheet" : 0.0, "bread" : 0.0} # Stock

        # Statistiques
        self.step_production = 0
        self.step_sold = 0
        self.step_demanded = 0
        self.step_costs = 0 # <--- NOUVEAU : Pour calculer le coût de revient
        self.unit_cost = 0  # <--- NOUVEAU : Coût d'un produit
        self.step_consumption_price = 0

        self.product_price = price
        self.money = 15000

    def add_labour(self, work_done):
        self.step_labor += work_done
        self.total_labor += work_done


    def request_work(self, individual):
        # Simplification : on accepte tout le monde pour l'instant
        individual.working_at = self
        self.employees.append(individual)
        return True
    
    def produce(self):
        # On calcule combien on peut produire
        production = 0
        if self.purpose == "food_raw_material":
            production = self.step_labor / self.labor
            self.products["wheet"] += production
        
        elif self.purpose == "agrifood":
            # Fonction de production Leontief (Need 3 wheet for 1 bread)
            max_possible_by_wheet = self.products["wheet"] / 3
            max_possible_by_labor = self.step_labor / self.labor
            
            production = min(max_possible_by_labor, max_possible_by_wheet)
            
            self.products["bread"] += production
            self.products['wheet'] -= production * 3

        self.step_production = production



    def income_distribution(self):
        # Paiement des salaires
        for employee in self.employees:
            if self.money <= 0.1: break
            
            salary = employee.current_skill # Salaire = compétence
            to_pay = min(self.money, salary)
            
            employee.wealth += to_pay
            self.money -= to_pay
            self.step_costs += to_pay # <-- On enregistre le coût !


    def intermediary_consumption(self):
        if self.purpose != "agrifood": return
            
        # 1. Identifier le besoin
        capacite_travail = min((self.step_labor / self.labor) * 3 * 2, self.step_demanded*3)
        ble_necessaire = (capacite_travail ) - self.products['wheet']
        
        if ble_necessaire <= 0: return

        # 2. Trouver les vendeurs
        vendeurs = self.model.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "food_raw_material")
        if not vendeurs: return
        
        # Tri par prix croissant
        vendeurs_tries = sorted(vendeurs, key=lambda x: x.product_price)
        
        self.step_consumption_price = vendeurs_tries[0].product_price

        i = 0
        while ble_necessaire > 0.1 and self.money > 0 and i < len(vendeurs_tries):
            vendeur: Entreprise = vendeurs_tries[i]
            
            # Important : on note la demande chez le vendeur même si on achète pas tout
            vendeur.step_demanded += min(ble_necessaire, self.money/vendeur.product_price) 

            if vendeur.products['wheet'] > 0:
                # Quantité max qu'on peut acheter
                qty = min(ble_necessaire, vendeur.products['wheet'], self.money / vendeur.product_price)
                
                cout = qty * vendeur.product_price
                
                # Transaction
                self.money -= cout
                self.step_costs += cout # <-- On enregistre le coût matière !
                self.products['wheet'] += qty
                
                vendeur.money += cout
                vendeur.products['wheet'] -= qty
                vendeur.step_sold += qty

                
                ble_necessaire -= qty
            i += 1

    def update_unit_cost(self):
        # On calcule le coût marginal théorique (plus stable)
        # Salaire moyen (basé sur les compétences des employés)
        if len(self.employees) > 0:
            avg_salary = sum([e.current_skill for e in self.employees]) / len(self.employees)
        else:
            avg_salary = 1.0 # Valeur par défaut

        # Coût du travail pour 1 unité
        work_cost = avg_salary * self.labor
        
        # Coût des matières premières
        raw_material_cost = 0
        if self.purpose == "agrifood":
            raw_material_cost = 3 * self.step_consumption_price
            
        current_theoretical_cost = work_cost + raw_material_cost
        
        # Lissage pour éviter les sauts brusques
        if self.unit_cost == 0: 
            self.unit_cost = current_theoretical_cost
        else:
            self.unit_cost = (self.unit_cost * 0.9) + (current_theoretical_cost * 0.1)


    def adjust_price(self):
        final_good = "wheet" if self.purpose == "food_raw_material" else "bread"
        current_stock = self.products[final_good]
        
        # Si on n'a rien vendu, on ne peut PAS augmenter le prix, c'est illogique
        if self.step_sold == 0:
            if current_stock > 0 and self.product_price > self.unit_cost:
                self.product_price *= 0.90 # On baisse si on a du stock invendu
            

        if self.last_labor > self.step_labor - len(self.employees)*0.01-0.01 and self.step_demanded < 20:
            self.product_price *= 0.90
        # Si on a vendu, on regarde la tension
        # On n'augmente que si la demande est vraiment supérieure à l'offre ET qu'on a vendu
        elif self.step_demanded > self.step_sold and self.step_demanded > 20:
            self.product_price *= 1.05 # Hausse prudente
            
        elif current_stock > 300: # Stock trop élevé
            self.product_price *= 0.95

 
        print(f"Last labor : {self.last_labor:.2f} | Step Labor : {self.step_labor:.2f}")
        self.step_sold = 0
        self.step_demanded = 0 
        self.last_labor = self.step_labor      
        self.step_labor = 0

    
    def step(self):

        # Reset des compteurs de tour
        self.step_costs = 0
        
        # 1. Payer les gens (Flux monétaire sortant)
        self.income_distribution()
        
        # 2. Acheter matières premières (Flux monétaire sortant)
        self.intermediary_consumption()
        
        # 3. Produire (Création de valeur)
        self.produce()
        self.update_unit_cost()

        products_formated = {key: round(value, 2) for key, value in self.products.items()}
        print(f"Id :\033[91m{self.name}\033[0m | Money : {self.money:.2f}$ | Products : {products_formated} | Price : {self.product_price:.2f} | Production {self.step_production:.2f} | Demand : {self.step_demanded:.2f}")





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
        self.step_price = 0
        self.current_skill = None
    
    def demand_work(self):
        if self.working_at is None:
            entreprise = self.model.agents.select(lambda a: isinstance(a, Entreprise))[random.randint(0, self.model.num_entreprises-1)]
            if entreprise.request_work(self):
                self.current_skill = self.skills.get(self.working_at.purpose)

    def work(self):
        if self.working_at is not None and self.hunger > 0:
            self.current_skill += 0.01
            self.working_at.add_labour(self.current_skill)

    def buy(self, desired_product):
        if desired_product == "bread":
            # 1. Récupérer et trier les boulangeries
            boulangeries = self.model.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "agrifood")
            if not boulangeries: return
            
            # Trier par prix (Mesa utilise souvent des listes d'agents qu'on peut trier ainsi)
            entreprises = sorted(boulangeries, key=lambda x: x.product_price)
            self.step_price = entreprises[0].product_price

            # 2. Calculer le besoin réel (Combien je VEUX manger + un petit stock de sécurité)
            # On veut compenser la faim actuelle + avoir un peu d'avance (max 2 pains au total)
            ideal_stock = 2.0
            product_needed = int(max(0, ideal_stock - self.inventory['bread']))
            
            if product_needed <= 0: return

            # 3. Calculer le budget (Combien je PEUX mettre)
            # Stratégie : Je dépense au max 30% de ma richesse, 
            # MAIS si j'ai très faim (hunger < 50), je peux monter jusqu'à 90%
            budget_ratio = 0.3 if self.hunger > 50 else 0.9
            accepted_price = self.wealth * budget_ratio
            
            i = 0
            while product_needed > 0.01 and accepted_price > 0.01 and i < len(entreprises):
                vendeur: Entreprise = entreprises[i]
                
                # Prix unitaire du vendeur
                price = vendeur.product_price
                
                # Combien puis-je acheter avec mon budget chez lui ?
                max_payable = int(accepted_price / price)
                
                # Quantité finale pour cette transaction
                qty_to_buy = min(product_needed, int(vendeur.products['bread']), max_payable)
                
                # Enregistrer la demande solvable (très important pour l'ajustement des prix)
                vendeur.step_demanded += min(product_needed, max_payable)

                if qty_to_buy > 0:
                    transaction_total = qty_to_buy * price
                    
                    # Transfert d'argent
                    self.wealth -= transaction_total
                    vendeur.money += transaction_total
                    
                    # Transfert de marchandise
                    vendeur.products['bread'] -= qty_to_buy
                    self.inventory['bread'] += qty_to_buy
                    
                    # Mise à jour des stats vendeur
                    vendeur.step_sold += qty_to_buy
                    
                    # Mise à jour des besoins individuels
                    product_needed -= qty_to_buy
                    accepted_price -= transaction_total
                
                i += 1

    def eat(self):
        to_eat = (100-self.hunger)/25

        can_be_eaten = min(to_eat, self.inventory['bread'])
        self.inventory['bread'] -= can_be_eaten
        self.hunger += can_be_eaten*25

    def stat(self):
        print(f"Id :{self.unique_id} | Money : {self.wealth:.2f}$ | Hunger : {int(self.hunger)} | Working at {self.working_at if self.working_at is None else self.working_at.name}")


    def step(self):
        self.hunger -= 2
        self.demand_work()
        self.work()
        self.buy("bread")
        self.eat()



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
        # 1. Les individus travaillent (on remplit step_labor des entreprises)
        individus = self.agents.select(lambda a: isinstance(a, Individual))
        individus.shuffle_do("step") 

        # 2. Les entreprises transforment le travail en produits
        # On commence par le blé pour que les boulangeries puissent l'acheter ensuite
        providers = self.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "food_raw_material")
        agrifoods = self.agents.select(lambda a: isinstance(a, Entreprise) and a.purpose == "agrifood")
        
        # On lance le cycle des entreprises (paie, achat matières, production)
        for e in providers: e.step()
        for e in agrifoods: e.step()

        # 3. Ajustement des prix pour TOUTES les entreprises (basé sur step_sold du tour précédent)
        all_entreprises = self.agents.select(lambda a: isinstance(a, Entreprise))
        for e in all_entreprises:
            e.adjust_price()
            e.step_demanded = 0

        # Logs
        print(f"Moyenne Argent Individus : {sum([i.wealth for i in individus])/len(individus):.2f}$")
        print(f"Satiété moyenne : {sum([i.hunger for i in individus])/len(individus):.2f}")
    
    def individual_stats(self):
        individus = self.agents.select(lambda a: isinstance(a, Individual))

        for i in individus: i.stat()





society_1 = Society(100, (('WheetCo', "food_raw_material", 1, 1), ('FarmCo', "food_raw_material", 1, 1), ("BreadCo", "agrifood", 2, 3), ("BakeryCo", "agrifood", 2, 3)))



for i in range(500):
    print("Step number :", i,"-------------------------")
    society_1.step()


society_1.individual_stats()
