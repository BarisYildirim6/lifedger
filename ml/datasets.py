import numpy as np

def build_sequences(data, window=6):
    X, y = [], []

    for i in range(len(data) - window):
        X.append(data[i:i+window])
        y.append(data[i+window][0])  # predict total_expense

    return np.array(X), np.array(y)