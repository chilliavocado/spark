
import gym
from gym import spaces
import numpy as np
from typing import List
import random
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import numpy as np

# Now try importing again
from spark.data import loader
from spark.data.models import Customer, Product, Category, Interaction, InteractionType
from spark import utils

"""                 INCOMPLETE                  """
class RecommendationEnv(gym.Env):
    def __init__(self, users:List[Customer], products:List[Product], top_k:int):
        super().__init__()
        
        self.users = users                  # list of users as states
        self.products = products            # products as actions, potential recommendations
        self.top_k = top_k                  # number of recommendations
        self.user_idx = 0                   # index of users list, not user_id
        self.current_step = 0               # step is also the interactions list index
        self.categories = loader.load_categories()
        
        # get unique category data
            
        # number of products as actions
        self.action_space = self.action_space = spaces.Dict({
            'product_idx': spaces.Box(low=0, high=len(self.products), shape=(top_k,), dtype=np.uint8),
            'price': spaces.Box(low=0, high=100000, shape=(top_k,), dtype=np.float32),
            'category_idx': spaces.Box(low=0, high=len(self.categories), shape=(top_k,), dtype=np.uint8)
        })
        
        # number of customers as states
        # states are derived from customer profiles and interactioms
        # Users list will keep track of unique users
        # States include subset of features including product, interaction, ratings, and time in one-hot-encoding format
        # States exclude user_ids for policy network generalisation. But internal users list will be used as reference        
        self.observation_space = spaces.Dict({
            'user': self.user_observation_space,
            'product': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.uint8),
            'interaction': spaces.Box(low=0, high=1, shape=(len(InteractionType),), dtype=np.uint8),
            'rating': spaces.Box(low=0, high=5, shape=(1,), dtype=np.uint8)
            }) 
            ## add more features like time, ignored recommendtions, engagement etc
            
    @property
    def user_observation_space(self):
        obs_space = {'pref_prod': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                     'pref_cat': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                     'purchase': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                     'viewed': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                     'liked': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.int),
                     'ratings': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32)}
        
        return obs_space
        
    def reset(self):
        self.user_idx = np.random.randint(len(self.users)) # may run throught users one by one
        self.current_step = 0
        return self._get_observation() # get current user features as states

    def step(self, rec_products):
        """ randomly interacting with product to mimick real user unpredictable behavious """
        self.current_step += 1
        user = self.users[self.user_idx]
        
        reward = 0
        done = False
        
        # simulate selected recommended product and interaction
        rp = random.choice(rec_products)
        rit = random.choice(list(InteractionType)) # generate random interaction
        rv = 0
        
        if rit == InteractionType.NONE:
            reward = -1 # no interaction, customers not interested in recommendations
        elif rit ==  InteractionType.VIEW:
            reward = 1
        elif rit ==  InteractionType.Like:
            reward = 3
        elif rit ==  InteractionType.BUY:
            reward = 20
        elif rit ==  InteractionType.RATE:
            # generate rating, reward 1-2 is negative 3 neutral and 5 positive
            rit = random.randint(1, 5)
            reward = (rv - 3) * 2                
        elif rit ==  InteractionType.SESSION_START:
            reward = 0
        elif rit ==  InteractionType.SESSION_CLOSE:
            done = True
            reward = -1 # TODO: check if engament is too short
        else:
            reward = 0
        
        # generate random interaction
        ri = Interaction(self.current_step, datetime.now(), user.idx, rp.idx, rit, rv)
        # reward = self._calculate_reward(user, product)
        
        return self._update_obsercation(ri), reward, done, {}

    def _update_observatin(self, product_idx, interaction:Interaction):   
        # update user data     
        user = self.users[self.current_user_index]        
        if interaction == InteractionType.VIEW:
            user.views[product_idx] += 1
        elif interaction == InteractionType.LIKE:
            user.likes[product_idx] += 1
        elif interaction == InteractionType.BUY:
            user.buys[product_idx] += 1
        elif interaction == InteractionType.RATE:
            user.rates[product_idx] = interaction.value
          
        # update observation based on new data  
        obs = {
            'user': self._get_user_observation(user),
            'product': utils.one_hot_encode(product_idx, len(self.products)),
            'interaction': self._get__get_interaction_observation(),
            'rating': interaction.value if interaction.type == InteractionType.RATE else 0 }
        
        return obs

    def _get_user_observation(self, user:Customer): 
        obs = {'pref_prod': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                'pref_cat': spaces.Box(low=0, high=1, shape=(len(self.products),), dtype=np.float32),
                'purchase': utils.normalise(user.purchases),
                'viewed': utils.normalise(user.views),
                'liked': utils.normalise(user.likes),
                'ratings': user.ratings}
        
        return obs
        
    def _get_interaction_observation(self, interaction:Interaction):
        idx = list(InteractionType).index(interaction)
        size = len(InteractionType)
        
        return utils.one_hot_encode(idx, size)
    
    # calculate preferences based on past interactions
    def _get_product_preferences(self, user:Customer):
        view_prefs = np.array(user.views) / 20
        purchase_prefs = np.array(user.purchases)
        like_prefs = np.array(user.likes) / 15
        rate_prefs = (np.array(user.ratings) - 3) / 10
        
        product_prefs = view_prefs + purchase_prefs + like_prefs+ rate_prefs
        
        return product_prefs

    def render(self, mode='human'):
        # user_id = self.current_user
        # user_state = self.user_states[user_id]
        
        # print(f"Current User ID: {user_id}")
        # print("User Interaction Summary:")
        # print(f"Views: {user_state}")  # Assuming views are stored in user_state
        # print(f"Purchases: {[i for i in range(self.num_products) if user_state[i] > 1]}")  # Modify as needed

        # # Print the current state (user's views and purchases)
        # print(f"Current State (Views/Purchases): {user_state}")

        # Print the last action taken (recommended product)
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