from .model import ExpenseLSTM
import torch.nn as nn
import torch

model = ExpenseLSTM(input_size=num_features).cuda()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
loss_fn = nn.MSELoss()

for epoch in range(200):
    optimizer.zero_grad()
    preds = model(X_train.cuda())
    loss = loss_fn(preds.squeeze(), y_train.cuda())
    loss.backward()
    optimizer.step()