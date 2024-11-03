import pandas as pd
from pathlib import Path
rootpath=Path(r'D:\repos\spark\data')

customers      = pd.read_csv(rootpath.joinpath('olist_customers_dataset.csv'))
# geolocation    = pd.read_csv(rootpath.joinpath('olist_geolocation_dataset.csv'))
orders         = pd.read_csv(rootpath.joinpath('olist_orders_dataset.csv'))
order_items    = pd.read_csv(rootpath.joinpath('olist_order_items_dataset.csv'))
# order_payments = pd.read_csv(rootpath.joinpath('olist_order_payments_dataset.csv'))
order_reviews  = pd.read_csv(rootpath.joinpath('olist_order_reviews_dataset.csv'))
products       = pd.read_csv(rootpath.joinpath('olist_products_dataset.csv'))
# sellers        = pd.read_csv(rootpath.joinpath('olist_sellers_dataset.csv'))
product_category_name_translation = pd.read_csv(rootpath.joinpath('product_category_name_translation.csv'))

products = products[['product_id','product_category_name']]
orders = orders[['order_id', 'customer_id']]


order_value = (order_items
               .groupby('order_id')
               .agg({'product_id':'count', 'price':'sum'})
               .rename(columns={'product_id':'product_count', 'price':'value'})
               .merge(orders[['order_id','customer_id']], how='inner', on='order_id')
               .sort_values(by='product_count',ascending=False)
               .reset_index()
               )

customer_value = (order_value
                  .groupby('customer_id')
                  .agg({'order_id':'count', 'product_count':'sum', 'value':'sum'})
                  .rename(columns={'order_id':'order_count'})
                  .merge(customers[['customer_id','customer_unique_id']], how='inner', on='customer_id')
                  .sort_values(by=['order_count','product_count'],ascending=False)
                  .reset_index()
                  )

customer_unique_value = (customer_value
                         .groupby('customer_unique_id')
                         .agg({'customer_id':'count', 'order_count':'sum', 'product_count':'sum', 'value':'sum'})
                         .rename(columns={'customer_id':'customer_count'})
                         .sort_values(by=['customer_count','order_count','product_count'],ascending=False)
                         .reset_index()
                         )

top_customers = (customer_unique_value
                 .sort_values(by=['product_count'],ascending=False)
                 .head(50)
                 )

customers = (customers
             .merge(top_customers, how='inner', on='customer_unique_id')
             .sort_values(by=['customer_unique_id','customer_id'])
             .reset_index()
             )

orders = (order_value
          .merge(customers[['customer_id']], how='inner', on='customer_id')
          )

order_items = (order_items
               .merge(orders[['order_id']], how='inner', on='order_id')
               )

order_reviews = (order_reviews
                 .merge(orders[['order_id']], how='inner', on='order_id')
                 )



# customers.nunique()
# orders.nunique()

# Derive unique price for each product
prod_price = (order_items[['product_id', 'price']]
              .sort_values(by=['product_id', 'price'])
              .drop_duplicates(subset='product_id')
              )

products=(products
          .merge(prod_price,how='inner',on='product_id')
          )

products=(products
          .merge(product_category_name_translation,how='left',on='product_category_name')
          )

products.drop(columns=['product_category_name'],inplace=True)

del order_value
del customer_value