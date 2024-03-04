import torch
import torch.nn as nn
from torch.nn.init import xavier_normal_
from numpy.random import RandomState
import numpy as np 

class FeaturesLinear(torch.nn.Module):

    def __init__(self, field_dims, output_dim=1):
        super().__init__()
        self.fc = torch.nn.Embedding(sum(field_dims), output_dim)
        self.bias = torch.nn.Parameter(torch.zeros((output_dim,)))
        self.offsets = np.array((0, *np.cumsum(field_dims)[:-1]), dtype=np.long)

    def forward(self, x):
        """
        :param x: Long tensor of size ``(batch_size, num_fields)``
        """
        x = x + x.new_tensor(self.offsets).unsqueeze(0)
        return torch.sum(self.fc(x), dim=1) + self.bias

class FeaturesEmbedding(torch.nn.Module):

    def __init__(self, field_dims, n_factors):
        super().__init__()
        self.embedding = torch.nn.Embedding(sum(field_dims), n_factors)
        self.offsets = np.array((0, *np.cumsum(field_dims)[:-1]), dtype=np.long)
        torch.nn.init.xavier_uniform_(self.embedding.weight.data)

    def forward(self, x):
        """
        :param x: Long tensor of size ``(batch_size, num_fields)``
        """
        x = x + x.new_tensor(self.offsets).unsqueeze(0)
        return self.embedding(x)
    
class FactorizationMachine(torch.nn.Module):

    def __init__(self, reduce_sum=True):
        super().__init__()
        self.reduce_sum = reduce_sum

    def forward(self, x):
        """
        :param x: Float tensor of size ``(batch_size, num_fields, n_factors)``
        """
        square_of_sum = torch.sum(x, dim=1) ** 2
        sum_of_square = torch.sum(x ** 2, dim=1)
        ix = square_of_sum - sum_of_square
        if self.reduce_sum:
            ix = torch.sum(ix, dim=1, keepdim=True)
        return 0.5 * ix


class FM(nn.Module):
    """Factorization Machine considers the second-order interaction with features to predict the final score."""

    def __init__(self, config):
        super(FM, self).__init__()

        n_factors = config['n_factors']
        #field_dims = config['field_dims']
        field_dims = [config['n_users'], config['n_items']]

        self.embedding = FeaturesEmbedding(field_dims, n_factors)
        self.linear = FeaturesLinear(field_dims)
        self.fm = FactorizationMachine(reduce_sum=True)
            
        # parameters initialization
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        if isinstance(module, nn.Embedding):
            xavier_normal_(module.weight.data)

    def forward(self, users_feat, items_feat):
        #import pdb; pdb.set_trace()
        x = torch.cat([users_feat.view(-1, 1), items_feat.view(-1, 1)], dim=1)
        x = self.linear(x) + self.fm(self.embedding(x))
        return x.squeeze(1)

    def predict(self, users_feat, items_feat):
        return self.forward(users_feat, items_feat)
