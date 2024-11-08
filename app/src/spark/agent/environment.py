# environment.py

import gymnasium as gym
from gym import spaces
import numpy as np
import random
from datetime import datetime
from typing import List
from app.src.spark.data.models import Customer, Product, Category, Interaction, InteractionType
from app.src.spark import utils

class RecommendationEnv(gym.Env):
    def __init__(self, users:List[Customer], products:List[Product], categories:List[Category], top_k:int):
        super().__init__()
        
        self.users = users                  # list of users as states
        self.products = products            # products as actions, potential recommendations
        self.categories = categories
        self.top_k = top_k                  # number of recommendations
        self.user_idx = 0                   # index of users list, not user_id
        self.current_step = 0               # step is also the interactions list index
        
        for user in users:
            user.views = np.zeros(len(products), dtype=np.int16)
            user.likes = np.zeros(len(products), dtype=np.int16)
            user.buys = np.zeros(len(products), dtype=np.int16)
            user.ratings = np.zeros(len(products), dtype=np.int16)
            for interaction in user.interactions:
                i_type = interaction.type.value    
                product_idx = interaction.product_idx  
                if i_type == InteractionType.VIEW.value:
                    user.views[product_idx] += 1
                elif i_type == InteractionType.LIKE.value:
                    user.likes[product_idx] += 1
                elif i_type == InteractionType.BUY.value:
                    user.buys[product_idx] += 1
                elif i_type == InteractionType.RATE.value:
                    user.ratings[product_idx] = interaction.value
                    
        # define action space to return top_k recommended product ids.    
        self.action_space = spaces.MultiDiscrete([len(products)] * top_k) 
        
        # number of customers as states
        # states are derived from customer profiles and interactioms
        # Users list will keep track of unique users
        # States include subset of features including product, interaction, ratings, and time in one-hot-encoding format
        # States exclude user_ids for policy network generalisation. But internal users list will be used as reference        
        self.observation_space = spaces.Dict({
            'pref_prod': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
            'pref_cat': spaces.Box(low=0, high=1, shape=(len(self.categories),), dtype=np.float32),
            'buys': spaces.Box(low=0, high=1000, shape=(len(self.products),), dtype=np.int16),
            'views': spaces.Box(low=0, high=1000, shape=(len(self.products),), dtype=np.int16),
            'likes': spaces.Box(low=0, high=1000, shape=(len(self.products),), dtype=np.int16),
            'ratings': spaces.Box(low=0, high=5, shape=(len(self.products),), dtype=np.uint8),
            'product': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.uint8),
            'interaction': spaces.Box(low=0, high=1, shape=(len(list(InteractionType)),), dtype=np.uint8),
            'rating': spaces.Discrete(6)
            }) 
        
        
    def reset(self, seed=None, options=None):
        # Call the parent class's reset method to handle seeding
        super().reset(seed=seed)
        
        self.user_idx = np.random.randint(len(self.users)) # may run throught users one by one
        user = self.users[self.user_idx]
        self.current_step = 0
        return self._get_observation(user), {}# get current user features as states

    def step(self, rec_products, interaction:Interaction=None):
        """ randomly interacting with product to mimick real user unpredictable behavious """
        self.current_step += 1
        
        # interaction passed in fro
        if interaction:    
            self.user_idx = interaction.customer_idx
        else:       
            # simulate selected recommended product and interaction
            interaction = self._simulate_interaction(rec_products) # generate random interaction
        
        reward = 0
        done = False
        
        # reward function if the recommended product is clicked
        if interaction.product_idx in rec_products:
            if interaction.type == InteractionType.NONE:
                reward = -1 # no interaction, customers not interested in recommendations
            elif interaction.type ==  InteractionType.VIEW:
                reward = 3
            elif interaction.type ==  InteractionType.LIKE:
                reward = 10
            elif interaction.type ==  InteractionType.BUY:
                reward = 30
            elif interaction.type ==  InteractionType.RATE:            
                reward = (interaction.value - 2)  * 3 # rating of 1 is negative
        
        done = interaction.type ==  InteractionType.SESSION_CLOSE
        
        interaction_info = {
                'interaction': {
                    'idx': -1,
                    'timestamp': interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'customer_id': interaction.customer_idx,
                    'product_id': interaction.product_idx,
                    'interaction': interaction.type.value,
                    'rating': interaction.value
                }
            }
        
        user = self.users[self.user_idx]
        
        return self._update_observation(user, interaction), reward, done, False, interaction_info

    def _update_observation(self, user:Customer, interaction:Interaction):            
        if interaction.type == InteractionType.VIEW:
            user.views[interaction.product_idx] += 1
        elif interaction.type == InteractionType.LIKE:
            user.likes[interaction.product_idx] += 1
        elif interaction.type == InteractionType.BUY:
            user.buys[interaction.product_idx] += 1
        elif interaction.type == InteractionType.RATE:
            user.ratings[interaction.product_idx] = interaction.value
            
        product_obs = np.zeros(len(self.products), dtype=np.int16)
        if interaction.type == InteractionType.VIEW \
            or interaction.type == InteractionType.LIKE  \
            or interaction.type == InteractionType.BUY \
            or interaction.type == InteractionType.RATE:
                product_obs = utils.one_hot_encode(interaction.product_idx, len(self.products))
        
        # update observation based on new data  
        obs = {
                'pref_prod': self._get_product_preferences(user),
                'pref_cat': self._get_category_preferences(user), 
                'buys': user.buys,
                'views': user.views,
                'likes': user.likes,
                'ratings': user.ratings,
                'product': product_obs,
                'interaction': self._get_interaction_observation(interaction),
                'rating': interaction.value if interaction.type == InteractionType.RATE else 0 
            }
        
        return obs
    
    def update_observation(self, user:Customer, interaction:Interaction):
        return self._update_observation(user, interaction)

    def _get_observation(self, user:Customer): 
        
        obs = {
                'pref_prod': self._get_product_preferences(user),
                'pref_cat': self._get_category_preferences(user), 
                'buys': user.buys,
                'views': user.views,
                'likes': user.likes,
                'ratings': user.ratings,
                'product': np.zeros(len(self.products)),
                'interaction': np.zeros(len(list(InteractionType))),
                'rating': 0 
            }
        
        return obs
        
    def _get_interaction_observation(self, interaction:Interaction):
        idx = list(InteractionType).index(interaction.type)
        size = len(InteractionType)
        
        return utils.one_hot_encode(idx, size)
    
    # calculate preferences based on past interactions
    def _get_product_preferences(self, user:Customer):
        view_prefs = user.views / 20
        purchase_prefs = user.buys
        like_prefs = user.likes / 15

        rating_prefs = user.ratings.copy()
        rating_prefs[rating_prefs > 0] -= 2
        
        product_prefs = view_prefs + purchase_prefs + like_prefs+ rating_prefs
        
        product_prefs / 5 # reduce space
        
        return product_prefs    # calculate preferences based on past interactions
    
    def _get_category_preferences(self, user:Customer):
        prod_prefs = self._get_product_preferences(user)
        cat_prefs = np.zeros(len(self.categories), np.float32)
        
        for idx, prod_pref in enumerate(prod_prefs):
            if prod_pref > 0:
                product = self.products[idx]
                cat_idx = product.category.idx
                cat_prefs[cat_idx] += prod_pref # accumulation of fav products for this cat
                # print(f"added pf {prod_pref} to cat {cat_idx}")
                
        cat_prefs = cat_prefs / 5 # reduce space     
           
        return cat_prefs

    def _simulate_interaction(self, product_ids):        
        user = self.users[self.user_idx]
        product_list = []
        
        # simulate selection
        num_products = len(product_ids)
        prod_scores = np.zeros(num_products, np.uint8)
        product_prefs = self._get_product_preferences(user)
        category_prefs = self._get_category_preferences(user)
        product_probs = np.full((num_products,), 1.0 / num_products) # equal probs by default
        
        for idx, pid in enumerate(product_ids):
            product_list.append(self.products[pid]) # get the product objects
            prod_scores[idx] = product_prefs[pid]
            
        # combining category prefs to calculate probabilities
        for idx, product in enumerate(product_list):
            cid = product.category.idx
            prod_scores[idx] += category_prefs[cid] # scores higher for favourite categories
    
        # Ensure the probabilities sum to 1 for a valid probability distribution
        if np.max(prod_scores) > 0: # probability selection based on prefernces
            product_probs = np.array(prod_scores) / sum(prod_scores)

        # Randomly select a product based on the defined probabilities
        selected_product_id = np.random.choice(product_ids, p=product_probs)
        
        # simulate interaction for the selected product
        inter_types = list(InteractionType)
        inter_scores = np.zeros(len(inter_types), np.uint8)
        inter_probs = np.full((len(inter_types),), 1.0 / len(inter_types)) # equal probs by default        
        inter_probs[-1] = 0.1 # lower prob for SESSION_CLOSE ending epsidoe flag to encourage longer training
        
        for idx, inter_type in enumerate(inter_types):
            if inter_type == InteractionType.VIEW:
                inter_scores[idx] = user.views[selected_product_id]
            if inter_type == InteractionType.LIKE:
                inter_scores[idx] = user.likes[selected_product_id]
            if inter_type == InteractionType.BUY:
                inter_scores[idx] = user.buys[selected_product_id]
            if inter_type == InteractionType.RATE:
                inter_scores[idx] = user.ratings[selected_product_id]
        
        if np.max(inter_scores) > 0:
            inter_scores += 1 # default score for interaction that are 0
            inter_scores = inter_scores * inter_probs # scale distribution
            inter_probs = np.array(inter_scores) / sum(inter_scores)

        # Randomly select a product based on the defined probabilities
        inter_probs = np.array(inter_probs) / sum(inter_probs) # normalise
        selected_interaction_type = np.random.choice(inter_types, p=inter_probs)
        
        selected_product_rating = random.randint(0, 5)
        if selected_interaction_type == InteractionType.RATE:
            # likely rating if the product is a prefered product
            prod_pref_score = product_prefs[selected_product_id]
            max_pref_score = np.max(product_prefs)
            if prod_pref_score > 0: # one of favourite products, rating of 2-5
                selected_product_rating = int((prod_pref_score/max_pref_score) * 3) + 2
                
        rating_probs = np.full(6, 1/6)
        rating_probs[selected_product_rating] = 0.7 # up chance of raing
        rating_probs = rating_probs/sum(rating_probs) # normlise
        selected_product_rating = np.random.choice([0,1,2,3,4,5], p=rating_probs)
            
        user_id = self.user_idx
        interaction_time = datetime.now()        
        interaction = Interaction(-1, interaction_time, user_id, selected_product_id, selected_interaction_type, selected_product_rating)

        return interaction

    def seed(self, seed=None):
        """
        Set the seed for reproducibility.
        """
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        random.seed(seed)
        np.random.seed(seed)
        return [seed]
    
    def render(self, mode='human'):
        if hasattr(self, 'last_action'):
            print(f"Recommended Product ID (Last Action): {self.last_action}")
        else:
            print("No product recommended yet.")

        # Optionally, print the reward received for the last action
        if hasattr(self, 'last_reward'):
            print(f"Reward for Last Action: {self.last_reward}")

        print("-----")

    def close(self):
        pass