import torch

def predict_next(model, last_sequence):
    model.eval()
    with torch.no_grad():
        return model(last_sequence.cuda()).item()