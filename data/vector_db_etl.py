# -*- coding: utf-8 -*-
"""
Created on Sun Nov  3 15:42:45 2024

@author: crowl

title: 
"""
#%% ===========================================================================
# 1) Set-up
# =============================================================================
import pandas as pd
from pathlib import Path
import os
import numpy as np

root_path=Path(os.getcwd())
source_path=root_path.joinpath('source')
target_path=root_path.joinpath('cleaned')

os.makedirs(source_path, exist_ok=True)
os.makedirs(target_path, exist_ok=True)

#%% ===========================================================================
# 2) Import datasets from source
# =============================================================================

customers      = pd.read_csv(source_path.joinpath('olist_customers_dataset.csv'))
# geolocation    = pd.read_csv(source_path.joinpath('olist_geolocation_dataset.csv'))
orders         = pd.read_csv(source_path.joinpath('olist_orders_dataset.csv'))
order_items    = pd.read_csv(source_path.joinpath('olist_order_items_dataset.csv'))
# order_payments = pd.read_csv(source_path.joinpath('olist_order_payments_dataset.csv'))
order_reviews  = pd.read_csv(source_path.joinpath('olist_order_reviews_dataset.csv'))
products       = pd.read_csv(source_path.joinpath('olist_products_dataset.csv'))
# sellers        = pd.read_csv(source_path.joinpath('olist_sellers_dataset.csv'))
product_category_name_translation = pd.read_csv(source_path.joinpath('product_category_name_translation.csv'))


#%% ===========================================================================
# 3) Apply translation to product_category_name
# =============================================================================
products = products[['product_id','product_category_name']]
products=(products
          .merge(product_category_name_translation,how='left',on='product_category_name')
          .drop(columns=['product_category_name'])
          .rename(columns={'product_category_name_english':'product_category'})
          )


#%% ===========================================================================
# 4) Combine orders and customers tables
# =============================================================================
orders = (orders[['order_id', 'customer_id', 'order_purchase_timestamp']]
          .rename(columns={'order_purchase_timestamp':'timestamp'})
          )

# Merge customers and orders tables together as customer_id and order_id is 1:1
customers_orders=(customers
                  .rename(columns={'customer_zip_code_prefix':'zip_code',
                                   'customer_city':'city',
                                   'customer_state':'state'})
                  .merge(orders, how='inner', on='customer_id')
            )


#%% ===========================================================================
# 5) Identify top X customers
# =============================================================================
# De-duplicate customer attributes, will be used later
customers_unique = (customers_orders[['customer_unique_id','customer_id','zip_code','city','state']]
                    .drop_duplicates(subset='customer_unique_id', keep='first')
                    .drop(columns=['customer_id'])
                    .sort_values(by=['customer_unique_id'])
                    .reset_index(drop=True)
                    # .reset_index()
                    )

# Aggregate order_items to find the value for each customer_id/order_id
order_value = (order_items
               .groupby('order_id')
               .agg({'product_id':'count', 'price':'sum'})
               .rename(columns={'product_id':'product_count', 'price':'value'})
               .merge(customers_orders[['order_id','customer_unique_id']], how='inner', on='order_id')
               .sort_values(by='product_count',ascending=False)
               .reset_index()
               )

# Further aggregate order_value to customer_unique_id level
customer_value = (order_value
                  .groupby('customer_unique_id')
                  .agg({'order_id':'count', 'product_count':'sum', 'value':'sum'})
                  .rename(columns={'order_id':'order_count'})
                  .merge(customers_unique, how='inner', on='customer_unique_id')
                  .sort_values(by=['product_count'],ascending=False)
                  .reset_index(drop=True)
                  .reset_index()
                  .rename(columns={'index':'customer_num_id'})
                  )

# Identify the top X customers to reduce the dataset to
top_customers = (customer_value
                 .head(100)
                 )

out_customers =(top_customers
                .drop(columns=['customer_unique_id', 'order_count', 'product_count','value'])
    )


#%% ===========================================================================
# 6) Curate top_order_items to cascade down to other datasets
# =============================================================================
top_order_items = (order_items[['order_id', 'order_item_id', 'product_id', 'price']]
                   .merge(customers_orders[['timestamp','order_id','customer_unique_id']], how='inner', on='order_id')
                   .merge(top_customers[['customer_unique_id','customer_num_id']], how='inner', on='customer_unique_id')
                   .merge(products, how='left', on='product_id')
                   .drop(columns='customer_unique_id')
                   .sort_values(by=['timestamp','order_id'])
                   .reset_index(drop=True)
                   .reset_index()
                   .rename(columns={'index':'order_num_id'})
                   )


top_order_items['timestamp'] = pd.to_datetime(top_order_items['timestamp']) + pd.to_timedelta(top_order_items['order_item_id'], unit='s')
top_order_items['interaction_id'] = 'order-'+ top_order_items['order_num_id'].astype(str)
top_order_items['review_score'] = 0
top_order_items['type'] = 'buy'


#%% ===========================================================================
# 6) Derive category and product tables to be used in env())
# =============================================================================
products_unique = (top_order_items[['product_id','product_category','price']]
                   .drop_duplicates(subset='product_id', keep='first')
                   .fillna(value={'product_category':'shrubbery'})
                   .sort_values(by=['product_category'])
                   .reset_index(drop=True)
                   # .reset_index()
                   # .rename(columns={'index':'product_num_id'})
                   )

# =============================================================================
# A hack to reduce the total count of categories to 14
# =============================================================================
category_unique=(products_unique[['product_category']]
                .drop_duplicates(subset='product_category', keep='first')
                .reset_index(drop=True)
                .reset_index()
                .rename(columns={'index':'category_num_id_raw'})
    )
category_unique['category_num_id']=category_unique['category_num_id_raw'].apply(lambda x: (x ) % 14)
category_unique['product_category_raw']=category_unique['product_category']

out_category=(category_unique[['product_category','category_num_id']]
                .drop_duplicates(subset='category_num_id', keep='first')
                )

category_unique=(category_unique
                 .drop(columns=['product_category'])
                 .merge(out_category, how='left', on='category_num_id')
                 )

products_unique = (products_unique
                   .rename(columns={'product_category':'product_category_raw'})
                   .merge(category_unique[['product_category_raw','product_category','category_num_id']], how='left', on='product_category_raw')
                   .drop(columns=['product_category_raw'])
                )

# =============================================================================
# A second hack to limit the total number of products to 5 per category at most
# =============================================================================
products_unique['category_seq_id'] = products_unique.groupby(['product_category']).cumcount()+1


# Step 1: Map category_seq_id values > 5 to range 1–5
products_unique['category_seq_id'] = products_unique['category_seq_id'].apply(lambda x: (x - 1) % 5 + 1)
products_unique['product_name_id'] = products_unique['product_category'] + '-' + products_unique['category_seq_id'].astype(str)

product_first=(products_unique
                .sort_values(by=['product_name_id'])
                .drop_duplicates(subset='product_name_id', keep='first')
                .reset_index(drop=True)
                .reset_index()
                .rename(columns={'index':'product_num_id'})
    )

products_unique = (products_unique
                   .drop(columns=['price'])
                   .merge(product_first[['product_num_id','product_name_id','price']], how='left', on='product_name_id')
                   )


out_products = (products_unique
                .drop_duplicates(subset='product_num_id', keep='first')
                .sort_values(by=['product_num_id'])
                .drop(columns=['product_id'])
                )

out_products['desc']     =out_products['product_name_id']
out_products['long_desc']=out_products['product_name_id']
out_category['desc']     =out_category['product_category']

#%% ===========================================================================
# 6) Feed back category_num_id into top_order_items
# =============================================================================
top_order_items=(top_order_items
                 .drop(columns=['product_category', 'price'])
                 .merge(products_unique, how='left', on='product_id')
    )

#%% ===========================================================================
# 7) Derive unique list of reviews
# =============================================================================
unique_order_products=(top_order_items[['order_id','order_item_id','product_num_id','customer_num_id']]
                       .drop_duplicates(subset=['order_id','product_num_id'], keep='first')
    )


top_reviews =(order_reviews[['review_id','order_id','review_score','review_answer_timestamp']]
              .rename(columns={'review_answer_timestamp':'timestamp'})
              .merge(unique_order_products, how='inner', on='order_id')
              .reset_index(drop=True)
              .reset_index()
              .rename(columns={'index':'review_num_id'})
    )

top_reviews['timestamp'] = pd.to_datetime(top_reviews['timestamp']) + pd.to_timedelta(top_reviews['order_item_id'], unit='s')
top_reviews['interaction_id'] = 'review-'+ top_reviews['review_num_id'].astype(str)
top_reviews['type'] = 'rate'
top_reviews['value'] = 1

#%% ===========================================================================
# 7) Combine top_order_items and top_reviews to derive out_interactions
# =============================================================================
out_interactions=(pd.concat([top_order_items[['timestamp','interaction_id','product_num_id','customer_num_id','review_score', 'type', 'price']].rename(columns={'price':'value'}),
                        top_reviews[['timestamp','interaction_id','product_num_id','customer_num_id','review_score', 'type', 'value']].rename(columns={'price':'value'})
                        ])
                  .sort_values(by=['timestamp','interaction_id'])
                  .reset_index(drop=True)
                  )


#%% ===========================================================================
# 8) Create out_customer_interactions flatfile
# =============================================================================
unique_zip_code = (out_customers[['zip_code']]
                   .drop_duplicates(subset='zip_code', keep='first')
                   .sort_values(by=['zip_code'])
                   .reset_index(drop=True)
                   .reset_index()
                   .rename(columns={'index':'zip_code_id'})
                   )

unique_city = (out_customers[['city']]
                .drop_duplicates(subset='city', keep='first')
                .sort_values(by=['city'])
                .reset_index(drop=True)
                .reset_index()
                .rename(columns={'index':'city_id'})
                )

unique_state = (out_customers[['state']]
                .drop_duplicates(subset='state', keep='first')
                .sort_values(by=['state'])
                .reset_index(drop=True)
                .reset_index()
                .rename(columns={'index':'state_id'})
                )

out_customer_interactions=(out_interactions
                           .merge(out_customers,    how='left', on='customer_num_id')
                           .merge(out_products[['product_num_id','category_num_id']], how='left', on='product_num_id')
                           .merge(unique_zip_code,  how='left', on='zip_code')
                           .merge(unique_city,      how='left', on='city')
                           .merge(unique_state,     how='left', on='state')
                           )

city_dummies = pd.get_dummies(out_customer_interactions['city_id']).astype(int)
state_dummies = pd.get_dummies(out_customer_interactions['state_id']).astype(int)
zip_code_dummies = pd.get_dummies(out_customer_interactions['zip_code_id']).astype(int)

# Step 2: Convert each row’s one-hot encoding into a dense numpy array
out_customer_interactions['city_embedding'] = city_dummies.apply(lambda row: row.values, axis=1)
out_customer_interactions['state_embedding'] = state_dummies.apply(lambda row: row.values, axis=1)
out_customer_interactions['zip_code_embedding'] = zip_code_dummies.apply(lambda row: row.values, axis=1)


#%% ===========================================================================
# 9) Derive purchase_history and rate_history
# =============================================================================
# Number of unique products
product_count  = out_customer_interactions['product_num_id'].nunique()
category_count = out_category['category_num_id'].nunique()

# Define scaling factor for review scores and EMA for purchase history
review_score_max = 5  # Known max value for review scores
alpha = 0.1  # EMA scaling factor for purchase history

# Initialize lists to store the scaled purchase and rate histories
hist_purchase_list = []
hist_rate_list     = []
hist_category_list = []

# Diagnostic counter for scaled_purchase_vector values exceeding 1
count_exceeds_one = 0

# Step 1: Iterate over each row in out_interactions
for idx, row in out_customer_interactions.iterrows():
    # Step 2: Initialize the purchase and rate history vectors
    purchase_vector     = np.zeros(product_count,  dtype=int)
    rate_history_vector = np.zeros(product_count,  dtype=float)
    category_vector     = np.zeros(category_count, dtype=int)
    
    # Step 3: Filter past 'buy' interactions for the purchase vector
    past_buys = out_customer_interactions[
        (out_interactions['customer_num_id'] == row['customer_num_id']) &
        (out_interactions['type'] == 'buy') &
        (out_interactions['timestamp'] < row['timestamp'])
    ]

    # Increment the purchase vector based on past buys
    for _, buy_row in past_buys.iterrows():
        product_id=buy_row['product_num_id']
        category_id=buy_row['category_num_id']
        purchase_vector[product_id] += 1
        category_vector[category_id] += 1

    # Apply EMA scaling to purchase vector
    scaled_purchase_vector = 1 - np.exp(-alpha * purchase_vector)
    scaled_category_vector = 1 - np.exp(-alpha * category_vector)

    # Diagnostic check for values exceeding 1 in scaled_purchase_vector
    if np.any(scaled_purchase_vector > 1):
        count_exceeds_one += np.sum(scaled_purchase_vector > 1)

    # Step 4: Filter past 'rate' interactions for the rate history vector
    past_rates = out_interactions[
        (out_interactions['customer_num_id'] == row['customer_num_id']) &
        (out_interactions['type'] == 'rate') &
        (out_interactions['timestamp'] < row['timestamp'])
    ]

    # Replace rate history vector elements with the most recent review_score, scaled to [0, 1]
    for product_id in past_rates['product_num_id'].unique():
        most_recent_rate = past_rates[past_rates['product_num_id'] == product_id].sort_values('timestamp').iloc[-1]
        rate_history_vector[product_id] = most_recent_rate['review_score'] / review_score_max

    # Append the scaled purchase and rate vectors to their respective lists
    hist_purchase_list.append(scaled_purchase_vector)
    hist_rate_list.append(rate_history_vector)
    hist_category_list.append(scaled_category_vector)

# Add the purchase and rate history vectors as new columns in out_interactions
out_customer_interactions['product_purchase_history'] = hist_purchase_list
out_customer_interactions['category_purchase_history'] = hist_category_list
out_customer_interactions['rate_history'] = hist_rate_list

# Print diagnostic result
print(f"Number of instances where scaled_purchase_vector elements exceeded 1: {count_exceeds_one}")


#%% ===========================================================================
# 10) Rename columns to align to data model requirements
# =============================================================================
out_interactions.rename(columns={'interaction_id':'idx',
                                 'timestamp':'timestamp',
                                 'customer_num_id':'customer_idx',
                                 'product_num_id':'product_idx',
                                 'type':'type',
                                 'value':'value',
                                 'review_score':'review_score',
                                 }
                        ,inplace=True)

out_customer_interactions.rename(columns={'interaction_id':'idx',
                                 'timestamp':'timestamp',
                                 'customer_num_id':'customer_idx',
                                 'product_num_id':'product_idx',
                                 'type':'type',
                                 'value':'value',
                                 'review_score':'review_score',
                                 }
                        ,inplace=True)

out_customers.rename(columns={'customer_num_id':'idx',
                              'city':'city',
                              'zip_code':'zip_code',
                              'state':'state',
                                 }
                        ,inplace=True)

out_category.rename(columns={'category_num_id':'idx',
                              'product_category':'name'
                                 }
                        ,inplace=True)

out_products.rename(columns={'product_num_id':'idx',
                             'product_name_id':'name',
                             'product_category_id':'category_id',
                             'product_category':'category',
                             'price':'price',
                                 }
                        ,inplace=True)

#%% ===========================================================================
# 11) Output transformed datasets files
# =============================================================================
out_interactions.to_csv(target_path.joinpath('Interaction.csv'))
out_customer_interactions.to_csv(target_path.joinpath('Customer_Interactions.csv'))
out_customers.to_csv(target_path.joinpath('Customer.csv'))
out_category.to_csv(target_path.joinpath('Category.csv'))
out_products.to_csv(target_path.joinpath('Product.csv'))