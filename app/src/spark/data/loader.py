from spark.data.models import Customer, Category, Product, Interaction

def load_customers(idxs:list=[]):
    customers = []
    # TODO: get a list of customers with given idx list
    # If list is empty, return all customers
    # else return a subject filtered by idxs
    for idx in idxs:
        # TODO: construct Customer objects and add to list
        pass
        
    return customers

def load_interactions(idxs:list=[], k=0):
    interactions = []
    # TODO: get a list of interactoins with given idx list
    # If list is empty, return all interactions
    # else return a subject filtered by idxs
    # if k > 0, return the most recent k interactions
    
    for idx in idxs:
        # TODO: construct Interaction and related objects and add to list
        pass
        
    return interactions

def load_categories(idxs:list=[]):
    # TODO: get categoires in objects from the db
    # If list is empty, return all categories
    # else return a subject filtered by idxs
    # Object type spark.data.model.Category
    categories = [] 
    
    for idx in idxs:
        # TODO: construct Category objects and add to list
        pass
        
    return categories

def load_category_names(idxs:list=[]):
    # TODO: get a list of cat names in order if idx
    # If list is empty, return all categories
    # else return a subject filtered by idxs
    names = [] # list of strings of cat names
    
    return names

def load_products(idxs:list=[]):
    products = []
    # TODO: get a list of products with given idx list
    # If list is empty, return all products
    # else return a subject filtered by idxs
    for idx in idxs:
        # TODO: construct Produc and related objects objects and add to list
        pass
        
    return products
    