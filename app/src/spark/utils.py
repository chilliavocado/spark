import numpy as np
from typing import List, Union
from sklearn.preprocessing import MinMaxScaler

def one_hot_encode(index, size):
    one_hot = np.zeros(size)
    
    if index < size:
        one_hot[index] = 1
    
    return one_hot

def normalise(list:List[float]):
    list = np.array(list).reshape(-1, 1)
    scaler = MinMaxScaler()
    normalized_array = scaler.fit_transform(list)
    normalized_list = normalized_array.flatten().tolist()
    
    return normalized_list