import torch.nn as nn
import torch
import json
import numpy as np
import time

def read_json(json_path: str):
    with open(json_path, 'r') as f:
        j_txt = f.read()
        list_obj = json.loads(s=j_txt)
        arr_obj = np.array(list_obj, dtype=np.float32)
        tensor_obj = torch.from_numpy(arr_obj)
        return tensor_obj


def set_weights(module: nn.modules, json_path: str):
    # https://stackoverflow.com/a/59468760
    w = read_json(json_path)
    module.weight = torch.nn.Parameter(w)


def set_biases(module: nn.modules, json_path: str):
    # https://stackoverflow.com/a/59468760
    w = read_json(json_path)
    w = w.reshape(w.shape[1])
    module.bias = torch.nn.Parameter(w)


class SE_VGG(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.num_classes = num_classes
        # define an empty for Conv_ReLU_MaxPool
        net = []

        # block 1
        net.append(nn.Conv2d(in_channels=3, out_channels=64, kernel_size=3, padding=1, stride=1))  # 0
        set_weights(net[0], './0122.function_422860.weights_0.json')
        set_biases(net[0], './0115.function_4213e0.biases_0.json')
        net.append(nn.ReLU())  # 1
        # the input channels is the output channels of previous conv2d layer
        net.append(nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1, stride=1))  # 2
        set_weights(net[2], './0063.function_40a8b0.weights_0.json')
        set_biases(net[2], './0115.function_4213e0.biases_1.json')
        net.append(nn.ReLU())  # 3
        net.append(nn.MaxPool2d(kernel_size=2, stride=2))  # 4

        # block 2
        net.append(nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1))  # 5
        set_weights(net[5], './0081.function_413f90.weights_0.json')
        set_biases(net[5], './0089.function_417530.biases_0.json')
        net.append(nn.ReLU())  # 6
        net.append(nn.Conv2d(in_channels=128, out_channels=128, kernel_size=3, stride=1, padding=1))  # 7
        set_weights(net[7], './0058.function_407460.weights_0.json')
        set_biases(net[7], './0089.function_417530.biases_1.json')
        net.append(nn.ReLU())  # 8
        net.append(nn.MaxPool2d(kernel_size=2, stride=2))  # 9

        # block 3
        net.append(nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, padding=1, stride=1))  # 10
        set_weights(net[10], './0053.function_403830.weights_0.json')
        set_biases(net[10], './0048.function_401e40.biases_0.json')
        net.append(nn.ReLU())  # 11
        net.append(nn.Conv2d(in_channels=256, out_channels=256, kernel_size=3, padding=1, stride=1))  # 12
        set_weights(net[12], './0074.function_40f750.weights_0.json')
        set_biases(net[12], './0048.function_401e40.biases_1.json')
        net.append(nn.ReLU())  # 13
        net.append(nn.Conv2d(in_channels=256, out_channels=256, kernel_size=3, padding=1, stride=1))  # 14
        set_weights(net[14], './0074.function_40f750.weights_1.json')
        set_biases(net[14], './0048.function_401e40.biases_2.json')
        net.append(nn.ReLU())  # 15
        net.append(nn.MaxPool2d(kernel_size=2, stride=2))  # 16

        # block 4
        net.append(nn.Conv2d(in_channels=256, out_channels=512, kernel_size=3, padding=1, stride=1))  # 17
        set_weights(net[17], './0103.function_41cd70.weights_0.json')
        set_biases(net[17], './0076.function_4127e0.biases_0.json')
        net.append(nn.ReLU())  # 18
        net.append(nn.Conv2d(in_channels=512, out_channels=512, kernel_size=3, padding=1, stride=1))  # 19
        set_weights(net[19], './0131.function_425db0.weights_0.json')
        set_biases(net[19], './0076.function_4127e0.biases_1.json')
        net.append(nn.ReLU())  # 20
        net.append(nn.Conv2d(in_channels=512, out_channels=512, kernel_size=3, padding=1, stride=1))  # 21
        set_weights(net[21], './0131.function_425db0.weights_1.json')
        set_biases(net[21], './0076.function_4127e0.biases_2.json')
        net.append(nn.ReLU())  # 22
        net.append(nn.MaxPool2d(kernel_size=2, stride=2))  # 23

        # block 5
        net.append(nn.Conv2d(in_channels=512, out_channels=512, kernel_size=3, padding=1, stride=1))  # 24
        set_weights(net[24], './0098.function_419790.weights_0.json')
        set_biases(net[24], './0107.function_420290.biases_0.json')
        net.append(nn.ReLU())  # 25
        net.append(nn.Conv2d(in_channels=512, out_channels=512, kernel_size=3, padding=1, stride=1))  # 26
        set_weights(net[26], './0098.function_419790.weights_1.json')
        set_biases(net[26], './0107.function_420290.biases_1.json')
        net.append(nn.ReLU())  # 27
        net.append(nn.Conv2d(in_channels=512, out_channels=512, kernel_size=3, padding=1, stride=1))  # 28
        set_weights(net[28], './0098.function_419790.weights_2.json')
        set_biases(net[28], './0107.function_420290.biases_2.json')
        net.append(nn.ReLU())  # 29
        net.append(nn.MaxPool2d(kernel_size=2, stride=2))  # 30

        # add net into class property
        self.extract_feature = nn.Sequential(*net)

        # define an empty container for Linear operations
        classifier = []
        classifier.append(nn.Linear(in_features=512*7*7, out_features=4096))
        #print(type(classifier[0].weight))
        #print(classifier[0].weight.shape)
        #print(classifier[0].bias.shape)
        set_weights(classifier[-1], './0139.function_429530.dense_weights_0.json')
        set_biases(classifier[-1], './0126.function_4250f0.biases_0.json')
        #print(classifier[0].bias.shape)
        #print(classifier[0].bias)
        classifier.append(nn.ReLU())
        # classifier.append(nn.Dropout(p=0.5))
        classifier.append(nn.Linear(in_features=4096, out_features=4096))
        set_weights(classifier[-1], './0091.function_417b30.dense_weights_0.json')
        set_biases(classifier[-1], './0126.function_4250f0.biases_1.json')
        classifier.append(nn.ReLU())
        # classifier.append(nn.Dropout(p=0.5))
        classifier.append(nn.Linear(in_features=4096, out_features=self.num_classes))
        set_weights(classifier[-1], './0067.function_40dd90.dense_weights_0.json')
        set_biases(classifier[-1], './0113.function_420ee0.biases_0.json')

        # add classifier into class property
        self.classifier = nn.Sequential(*classifier)

    def forward(self, x):
        feature = self.extract_feature(x)
        feature = feature.view(x.size(0), -1)
        classify_result = self.classifier(feature)
        return classify_result


if __name__ == "__main__":
    # x = torch.rand(size=(1, 3, 224, 224))
    with open('cat.bin', 'br') as f:
        bin_data = f.read()
        np_arr = np.frombuffer(bin_data, dtype=np.float32)
        print(np_arr.shape)
        np_arr = np_arr.reshape(3, 224, 224)
        np_arr = np_arr.reshape((1, 3, 224, 224))
        x = torch.Tensor(np_arr)
        print(x.shape)

    time1 = time.time()
    print('building the model:', end=' ')
    vgg = SE_VGG(num_classes=1000)
    time2 = time.time()
    print('{}s'.format(time2 - time1))

    print('predicting the label:', end=' ')
    out = vgg(x)
    time3 = time.time()
    print('{}s'.format(time3 - time2))

    print(out.size())
    print(type(out))
    max_index = np.argmax(out.detach().numpy())
    print(max_index)
    # print(out)
    print(out.detach().numpy()[0, max_index])
