import os
import numpy as np
from typing import List
import gym
from gym import spaces
from gym.utils import seeding
from app.src.spark.data.loader import load_categories
from app.src.spark.data.models import Customer, Product, InteractionType


class UserBehaviorModel:
    def __init__(self, customers: List[Customer], num_products: int):
        num_users = len(customers)
        # Initialize matrices for interaction counts
        self.view_counts = np.zeros((num_users, num_products))
        self.like_counts = np.zeros((num_users, num_products))
        self.buy_counts = np.zeros((num_users, num_products))
        self.rate_counts = np.zeros((num_users, num_products))

        # Populate counts from customers' interaction data
        for user_idx, customer in enumerate(customers):
            self.view_counts[user_idx, :] = customer.views
            self.like_counts[user_idx, :] = customer.likes
            self.buy_counts[user_idx, :] = customer.purchases
            # For ratings, count non-zero ratings
            self.rate_counts[user_idx, :] = np.array([1 if rating > 0 else 0 for rating in customer.ratings])

        # Compute total interaction counts per user-product pair
        self.total_counts = self.view_counts + self.like_counts + self.buy_counts + self.rate_counts

        # Avoid division by zero
        self.total_counts[self.total_counts == 0] = 1

        # Compute probabilities
        self.view_probs = self.view_counts / self.total_counts
        self.like_probs = self.like_counts / self.total_counts
        self.buy_probs = self.buy_counts / self.total_counts
        self.rate_probs = self.rate_counts / self.total_counts

    def get_interaction_probabilities(self, user_idx: int, product_idx: int):
        # Return the probabilities for the user-product pair
        probs = {
            InteractionType.VIEW: self.view_probs[user_idx, product_idx],
            InteractionType.LIKE: self.like_probs[user_idx, product_idx],
            InteractionType.BUY: self.buy_probs[user_idx, product_idx],
            InteractionType.RATE: self.rate_probs[user_idx, product_idx],
            InteractionType.SESSION_CLOSE: 0.05,  # Fixed small probability
        }

        # Compute total probability without NONE
        total_prob = sum(probs.values())

        # Compute NONE probability as the remaining probability
        probs[InteractionType.NONE] = max(0.0, 1.0 - total_prob)

        # Get probabilities in the order of possible_interactions
        interaction_probs = [
            probs[itype]
            for itype in [
                InteractionType.NONE,
                InteractionType.VIEW,
                InteractionType.LIKE,
                InteractionType.BUY,
                InteractionType.RATE,
                InteractionType.SESSION_CLOSE,
            ]
        ]

        # Normalize probabilities
        total = sum(interaction_probs)
        if total > 0:
            interaction_probs = [prob / total for prob in interaction_probs]
        else:
            # If total is zero, assign uniform probabilities
            interaction_probs = [1.0 / len(interaction_probs)] * len(interaction_probs)

        return interaction_probs


class RecommendationEnv(gym.Env):
    def __init__(
        self, users: List[Customer], products: List[Product], top_k: int, max_price: float, user_behavior_model: UserBehaviorModel, price_interval: int = 500
    ):
        super().__init__()

        # Initialize users and products data
        self.users = users
        self.products = products
        self.num_products = len(products)
        self.top_k = top_k  # Number of top recommendations
        self.user_idx = 0  # Index of the current user
        self.current_step = 0  # Step count in the current episode
        self.categories = load_categories()  # Load category data
        self.num_categories = len(self.categories)
        self.possible_interactions = [
            InteractionType.NONE,
            InteractionType.VIEW,
            InteractionType.LIKE,
            InteractionType.BUY,
            InteractionType.RATE,
            InteractionType.SESSION_CLOSE,
        ]

        # Define price levels based on max price and price interval
        self.num_price_levels = int(np.ceil(max_price / price_interval))
        self.price_interval = price_interval

        # Initialize the random number generator
        self.seed()

        # User behavior model
        self.user_behavior_model = user_behavior_model

        # Define the action space
        self.action_space = spaces.Discrete(self.num_products)

        # Define the observation space
        self.observation_space = spaces.Dict(
            {
                "pref_prod": spaces.Box(low=0, high=1, shape=(self.num_products,), dtype=np.float32),
                "pref_cat": spaces.Box(low=0, high=1, shape=(self.num_categories,), dtype=np.float32),
                "purchase": spaces.Box(low=0, high=1, shape=(self.num_products,), dtype=np.float32),
                "viewed": spaces.Box(low=0, high=1, shape=(self.num_products,), dtype=np.float32),
                "liked": spaces.Box(low=0, high=1, shape=(self.num_products,), dtype=np.float32),
                "ratings": spaces.Box(low=0, high=5, shape=(self.num_products,), dtype=np.float32),
            }
        )

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self, user_idx=None):
        # Reset the environment to start a new episode
        if user_idx is not None:
            self.user_idx = user_idx % len(self.users)  # Ensure user_idx is within bounds
        else:
            self.user_idx = self.np_random.integers(0, len(self.users))
        self.current_step = 0
        return self._get_observation()

    def step(self, action):
        # Execute one time step within the environment
        self.current_step += 1  # Increment step count
        user = self.users[self.user_idx]  # Get the current user

        # Decode the action
        decoded_action = self.decode_action(action)
        recommended_product_idx = decoded_action["product_idx"]

        # Get the interaction probabilities from the behavior model
        interaction_probs = self.user_behavior_model.get_interaction_probabilities(user_idx=self.user_idx, product_idx=recommended_product_idx)

        # Simulate user interaction based on actual data
        interaction_type = self.np_random.choice(a=self.possible_interactions, p=interaction_probs)

        # Define rating_value based on interaction_type
        if interaction_type == InteractionType.RATE:
            # Use historical rating if available
            rating_value = user.ratings[recommended_product_idx]
            if rating_value == 0:
                rating_value = self.np_random.integers(1, 6)
        else:
            rating_value = 0

        # Calculate the reward and check if the episode is done
        reward = self._calculate_reward(interaction_type, rating_value)
        done = interaction_type == InteractionType.SESSION_CLOSE  # Episode ends if session is closed

        # Update the user's observation based on the interaction
        obs = self._update_observation(recommended_product_idx, interaction_type, rating_value)

        return obs, reward, done, {}

    def decode_action(self, action):
        # Action directly corresponds to product index
        product_idx = action
        return {"product_idx": product_idx}

    # def _calculate_interaction_probabilities(self, product_pref):
    #     # Ensure product_pref is within [0, 1]
    #     product_pref = np.clip(product_pref, 0.0, 1.0)

    #     # Example probabilities based on product preference
    #     base_prob = 0.05  # Adjusted base probability
    #     interaction_probs = {
    #         InteractionType.VIEW: base_prob + 0.2 * product_pref,
    #         InteractionType.LIKE: base_prob + 0.15 * product_pref,
    #         InteractionType.BUY: base_prob + 0.1 * product_pref,
    #         InteractionType.RATE: base_prob + 0.05 * product_pref,
    #         InteractionType.SESSION_CLOSE: 0.05,  # Fixed small probability
    #     }
    #     # Compute total probability so far
    #     total_prob = sum(interaction_probs.values())
    #     # Compute NONE probability as the remaining probability
    #     interaction_probs[InteractionType.NONE] = max(0.0, 1.0 - total_prob)
    #     # Ensure all probabilities are non-negative
    #     interaction_probs = {k: max(0.0, v) for k, v in interaction_probs.items()}

    #     # Get probabilities in the order of possible_interactions
    #     probs = [interaction_probs[itype] for itype in self.possible_interactions]

    #     # Normalize probabilities
    #     total = sum(probs)
    #     if total == 0:
    #         # Handle the case where all probabilities are zero
    #         probs = [1.0 / len(probs)] * len(probs)
    #     else:
    #         probs = [prob / total for prob in probs]

    #     return probs

    def _calculate_reward(self, interaction_type, rating_value):
        # Define rewards based on interaction type and rating
        if interaction_type == InteractionType.NONE:
            return -1
        elif interaction_type == InteractionType.VIEW:
            return 1
        elif interaction_type == InteractionType.LIKE:
            return 3
        elif interaction_type == InteractionType.BUY:
            return 20
        elif interaction_type == InteractionType.RATE:
            return (rating_value - 3) * 2  # Encourage high ratings
        elif interaction_type == InteractionType.SESSION_CLOSE:
            return -1
        else:
            return 0

    def _update_observation(self, product_idx, interaction_type, rating_value):
        # Update the user's interaction data based on the interaction
        user = self.users[self.user_idx]

        if interaction_type == InteractionType.VIEW:
            user.views[product_idx] += 1
        elif interaction_type == InteractionType.LIKE:
            user.likes[product_idx] += 1
        elif interaction_type == InteractionType.BUY:
            user.purchases[product_idx] += 1
        elif interaction_type == InteractionType.RATE:
            user.ratings[product_idx] = rating_value

        # Return the updated observation
        return self._get_observation()

    def _get_observation(self):
        # Construct the observation dictionary
        user = self.users[self.user_idx]
        max_views = max(user.views) if max(user.views) > 0 else 1
        max_purchases = max(user.purchases) if max(user.purchases) > 0 else 1
        max_likes = max(user.likes) if max(user.likes) > 0 else 1

        observation = {
            "pref_prod": self._get_product_preferences(user),
            "pref_cat": self._get_category_preferences(user),
            "purchase": np.array(user.purchases, dtype=np.float32) / max_purchases,
            "viewed": np.array(user.views, dtype=np.float32) / max_views,
            "liked": np.array(user.likes, dtype=np.float32) / max_likes,
            "ratings": np.array(user.ratings, dtype=np.float32),
        }
        return observation

    def _get_product_preferences(self, user):
        # Calculate dynamic maximums for normalization
        max_view = max(user.views) if max(user.views) > 0 else 1
        max_purchase = max(user.purchases) if max(user.purchases) > 0 else 1
        max_like = max(user.likes) if max(user.likes) > 0 else 1
        max_rating = max(user.ratings) if max(user.ratings) > 0 else 5

        # Calculate preferences dynamically
        view_pref = np.array(user.views, dtype=np.float32) / max_view
        purchase_pref = np.array(user.purchases, dtype=np.float32) / max_purchase
        like_pref = np.array(user.likes, dtype=np.float32) / max_like
        rate_pref = (np.array(user.ratings, dtype=np.float32) - 3.0) / max_rating

        # Combine preferences and normalize
        product_pref = view_pref + purchase_pref + like_pref + rate_pref
        max_pref = np.max(product_pref) if np.max(product_pref) > 0 else 1
        product_pref = np.clip(product_pref / max_pref, 0.0, 1.0)

        return product_pref

    def _get_category_preferences(self, user):
        # Calculate category preferences by summing interactions per category
        category_pref = np.zeros(self.num_categories, dtype=np.float32)
        for product_idx in range(self.num_products):
            category = self.products[product_idx].category
            if category is not None:
                category_idx = category.idx  # Assuming category.idx is zero-based
                category_pref[category_idx] += user.views[product_idx] + user.purchases[product_idx]
        total_pref = np.sum(category_pref)
        if total_pref > 0:
            category_pref = category_pref / total_pref
        return category_pref

    def render(self, mode="human"):
        # Optional: implement visualization if needed
        print(f"Current User Index: {self.user_idx}")
        print(f"Step: {self.current_step}")

    def close(self):
        # Optional: implement any necessary cleanup
        pass
