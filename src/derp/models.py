import torch
import torch.nn as nn


class Block(nn.Module):
    def __init__(self, n_in, n_out, kernel_size=3, stride=1,
                 padding=None, pool=None):
        super(Block, self).__init__()

        if padding is None:
            padding = kernel_size // 2
            
        self.conv1 = nn.Conv2d(n_in, n_out, kernel_size=kernel_size, stride=stride, padding=padding)
        self.bn1 = nn.BatchNorm2d(n_out)
        self.elu = nn.ELU(inplace=True)

        self.pool = None
        if pool == 'max':
            self.pool = nn.MaxPool2d(2, stride=2, padding=0)
        elif pool == 'avg':
            self.pool = nn.AvgPool2d(2, stride=2, padding=0)
        
    def forward(self, x):
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.elu(out)
        if self.pool is not None:
            out = self.pool(out)
        return out

class ResnetBlock(nn.Module):
    def __init__(self, n_in, n_out=None):
        super(ResnetBlock, self).__init__()
        if n_out is None:
            n_out = n_in
        self.elu = nn.ELU(inplace=True)
        self.c1 = nn.Conv2d(n_in, n_out, kernel_size=3, stride=1, padding=1, bias=False)
        self.c2 = nn.Conv2d(n_out, n_out, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(n_out)
        self.bn2 = nn.BatchNorm2d(n_out)
        
    def forward(self, x):
        residual = x
        out = self.c1(x)
        out = self.bn1(out)
        out = self.elu(out)
        out = self.c2(out)
        out = self.bn2(out)
        out += residual
        out = self.elu(out)
        return out

    
class BasicModel(nn.Module):

    def __init__(self, config):
        super(BasicModel, self).__init__()
        self.d = config['patch']['depth']
        self.h = config['patch']['height']
        self.w = config['patch']['width']
        self.c1 = Block(self.d, 64, 5, stride=2) ; self.h /= 2 ; self.w /= 2
        self.c2 = Block(64, 64, 3, pool='max') ; self.h /= 2 ; self.w /= 2
        self.c3 = Block(64, 64, 3, pool='max') ; self.h /= 2 ; self.w /= 2
        self.c4 = Block(64, 64, 3, pool='max') ; self.h /= 2 ; self.w /= 2
        self.fc1 = nn.Linear(int(self.h * self.w * 64), 64)
        self.fc2 = nn.Linear(64, len(config['fields']))
        self.elu = nn.ELU(inplace=True)

    def forward(self, x):
        out = self.c1(x)
        out = self.c2(out)
        out = self.c3(out)
        out = self.c4(out)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)
        out = self.elu(out)
        out = nn.functional.dropout(out, p=0.5, training=self.training)
        out = self.fc2(out)
        return out

    
class ResidualModel(nn.Module):
    def __init__(self, config):
        super(ResidualModel, self).__init__()
        self.d = config['patch']['depth']
        self.h = config['patch']['height']
        self.w = config['patch']['width']
        self.n_feats = 64
        self.maxpool = nn.MaxPool2d(2, stride=2, padding=0)
        self.c1 = Block(self.d, 64, 5, stride=2) ; self.h /= 2 ; self.w /= 2
        self.c2a = ResnetBlock(64)
        self.c2b = ResnetBlock(64) ; self.h /= 2 ; self.w /= 2
        self.c3a = ResnetBlock(64)
        self.c3b = ResnetBlock(64) ; self.h /= 2 ; self.w /= 2
        self.c4a = ResnetBlock(64)
        self.c4b = ResnetBlock(64) ; self.h /= 2 ; self.w /= 2
        self.c4a = ResnetBlock(64)
        self.c4b = ResnetBlock(64) ; self.h /= 2 ; self.w /= 2
        self.fc1 = nn.Linear(int(self.w * self.h * 64 + 0.5), len(config['fields']))

    def forward(self, x):
        out = self.c1(x)
        out = self.c2a(out)
        out = self.c2b(out)
        out = self.maxpool(out)
        out = self.c3a(out)
        out = self.c3b(out)
        out = self.maxpool(out)
        out = self.c4a(out)
        out = self.c4b(out)
        out = self.maxpool(out)
        out = self.c4a(out)
        out = self.c4b(out)
        out = self.maxpool(out)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)
        return out
    
