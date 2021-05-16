import os
import re
import math
import collections


# ==============================================================
# Utils
# ==============================================================
def output_region(mem_write_regions: list):
    big_mem = (0, 0)
    for mem_blk in mem_write_regions:
        if (mem_blk[1] - mem_blk[0]) > (big_mem[1] - big_mem[0]):
            big_mem = mem_blk
    return big_mem


def choose_one_4bytes(exp_log_path: str, mem_write_regions: list, num=0):
    """ Choose one expression from the exp_log to recover the filter shape """
    out_mem = output_region(mem_write_regions)
    exp_log_path = os.path.abspath(exp_log_path)
    with open(exp_log_path, 'r') as f:
        exp_txt = f.read()
        lines = exp_txt.split('\n')
        f.close()
        index = 0
        length = len(lines)
        name = ''
        exp = ''
        while index < length-2:
            name = lines[index]
            index += 1
            exp = lines[index].strip('<>')
            index += 1
            if name.endswith('32') or name.endswith('16') or name.startswith('0x7ff'):
                continue
            else:  # choose the first expression of one 4 bytes memory block
                if out_mem[0] <= int(name.split(',')[0], 16) <= out_mem[1]:
                    num -= 1
                if num < 0:
                    return name, exp
        return '', ''


def choose_one_16bytes(exp_log_path: str, mem_write_regions: list, num=0):
    out_mem = output_region(mem_write_regions)
    exp_log_path = os.path.abspath(exp_log_path)
    with open(exp_log_path, 'r') as f:
        exp_txt = f.read()
        lines = exp_txt.split('\n')
        f.close()
        index = 0
        length = len(lines)
        name = ''
        exp = ''
        while index < length-2:
            name = lines[index]
            index += 1
            exp = lines[index].strip('<>')
            index += 1
            if (not name.endswith('16')) or name.startswith('0x7ff'):
                continue
            elif exp_txt.count(name) > 1:
                continue
            else:  # choose the first expression of one 4 bytes memory block
                if out_mem[0] <= int(name.split(',')[0], 16) <= out_mem[1]:
                    num -= 1
                if num < 0:
                    return name, exp
        return name, exp


def get_output_channel(exp: str, one_channel_size: int, mem_regions: list, compiler='tvm', on_the_right=True):
    # get one weight address
    """
    if compiler == 'tvm' and on_the_right:
        it = re.search(r'\* (0x[0-9a-f]+),16\)', exp)
        addr_str = it.group(1)
        addr = int(addr_str, 16)
    elif compiler == 'tvm' and not on_the_right:
        it = re.search(r'(0x[0-9a-f]+),16 \*', exp)
        addr_str = it.group(1)
        addr = int(addr_str, 16)
    for mem_blk in mem_regions:
        if mem_blk[0] <= addr <= mem_blk[1]:
            weights_region = mem_blk
            break
    output_channel = (weights_region[1] - weights_region[0]) / 4 / filter_size
    """
    big_mem = (0, 0)
    if compiler == 'tvm' or compiler == 'glow' :
        for mem_blk in mem_regions:
            if (mem_blk[1]-mem_blk[0]) > (big_mem[1]-big_mem[0]):
                big_mem = mem_blk
    output_channel = ((big_mem[1] - big_mem[0]) / one_channel_size) / 4
    return big_mem, output_channel


def get_input_shape(name, exp, mem_regions, input_channel, size):
    offset_list = get_addr_list(exp, 'tvm', size)
    input_start_addr = min(offset_list)
    print(hex(input_start_addr))
    for mem_start, mem_end in mem_regions:
        if mem_start <= input_start_addr < mem_end:
            return math.sqrt(((mem_end-input_start_addr)/input_channel)/4)


# ==============================================================
# Heuristics used to recover shape for TVM Conv2d
# ==============================================================


# -----------------------------------------------
# how to interpret the taint analysis result
# can we assume that we know the start addresses of inputs and output?
def explain_tvm_conv2d_result(exp_log_path: str, mem_read_regions: list, mem_write_regions: list):
    # assume the mem_log comes from a convolution layer

    name, exp = choose_one_4bytes(exp_log_path, mem_write_regions)
    if len(name) == 0:
        name, exp = choose_one_16bytes(exp_log_path, mem_write_regions)
        return explain_tvm_conv2d_result_16(name, exp, mem_read_regions, mem_write_regions)
    mem_list = [(name, exp)]
    mem_list.append(tuple(choose_one_4bytes(exp_log_path, mem_write_regions, 1)))

    # TODO: here assume width==height
    input_shape = [1, 1, 1, 1]
    filter_shape = [1, 1, 1, 1]
    output_shape = [1, 1, 1, 1]

    if len(mem_read_regions) > 10:
        kernel_num, input_num = kernel_1_1(name, exp, mem_read_regions, mem_write_regions)
        filter_shape[1] = kernel_num
        input_shape[1] = kernel_num
        input_shape[2] = input_shape[3] = input_num
        output_shape[2] = output_shape[3] = math.ceil(input_num/2)
    else:
        # get the filter shape and input shape from first output
        offset_list = get_offset_list(mem_list[0][1], compiler='tvm')  # analyze the first expression (with the smallest address)
        stride = offset_list[1] - offset_list[0]  # not the real stride
        index = 0
        while index < len(offset_list) - 1:
            if offset_list[index+1] - offset_list[index] > stride:
                tmp1 = offset_list[index + 1]  # input[1] * input[2]
                tmp2 = offset_list[index] + stride  # filter[1] * filter[2]
                filter_shape[3] = len(offset_list)/tmp2
                filter_shape[2] = filter_shape[3]  # TODO assume
                filter_shape[1] = tmp2/filter_shape[2]
                # input[1] = filter[1]
                input_shape[1] = filter_shape[1]
                input_shape[2] = tmp1 / input_shape[1]
                input_shape[3] = input_shape[2]  # TODO assume
                break
            elif offset_list[index+1] - offset_list[index] < stride:
                filter_shape[3] = index + 1
                filter_shape[2] = filter_shape[3]  # TODO assume
                filter_shape[1] = len(offset_list) / (filter_shape[2] * filter_shape[3])
                # input[1] = filter[1]
                input_shape[1] = filter_shape[1]
                input_shape[2] = input_shape[3] = get_input_shape(name, exp, mem_read_regions, input_shape[1], 4)
                break
            index += 1

        addr_list_0 = get_addr_list(mem_list[0][1], 'tvm', 4)
        if addr_list_0[0] > addr_list_0[-1]:
            addr_list_0.reverse()  # addr_list_0.sort()
        addr_list_1 = get_addr_list(mem_list[1][1], 'tvm', 4)
        if addr_list_1[0] > addr_list_1[-1]:
            addr_list_1.reverse()  # addr_list_1.sort()
        addr_1 = addr_list_1[0]
        # idx_0 = addr_list_0.index(addr_1)
        idx_0 = 0
        while idx_0 < len(addr_list_0):
            if addr_list_0[idx_0] >= addr_1:
                break
            idx_0 += 1
        if idx_0 == 1:
            stride = 1
        elif idx_0 <= 3:
            stride = idx_0  # / filter_shape[1]  # TODO: calculate the stride, can be wrong
        else:
            stride = idx_0 / filter_shape[1]

        output_shape[2] = math.ceil((input_shape[2] - filter_shape[2] + 1)/stride)
        output_shape[3] = math.ceil((input_shape[3] - filter_shape[3] + 1)/stride)
    # get output shape
    # TODO: cannot get output_channel easily, because we do not have all mem_log (too huge and too slow)
    # filter_size = filter_shape[1] * filter_shape[2] * filter_shape[3]
    one_channel_size = output_shape[2] * output_shape[3]
    weights_region, output_channel = get_output_channel(mem_list[0][1], one_channel_size, mem_write_regions, compiler='tvm')
    # XXX: Did I made it ?

    output_shape[1] = output_channel
    filter_shape[0] = output_shape[1]

    # final shape
    print('input shape', input_shape)
    print('filter shape', filter_shape)
    print('output shape', output_shape)
    return filter_shape, input_shape, output_shape


def kernel_1_1(name, exp, mem_read_regions: list, mem_write_regions: list):
    """ function to handle layer with 1*1 kernel """
    mem_start = 0x7f0000000000
    mem_end = 0
    target_size = dict()
    for mem_blk in mem_read_regions:
        mem_size = mem_blk[1] - mem_blk[0]
        if mem_size in target_size:
            target_size[mem_size] += 1
        else:
            target_size[mem_size] = 1

    target_list = list(target_size.items())
    target_list = sorted(target_list, key=lambda x: x[1])
    mem_size = target_list[-1][0]
    for mem_blk in mem_read_regions:
        if mem_blk[1] - mem_blk[0] == mem_size:
            if mem_blk[0] < mem_start:
                mem_start = mem_blk[0]
            if mem_blk[1] > mem_end:
                mem_end = mem_blk[1]
    offset_list = get_offset_list(exp, compiler='tvm')
    kernel_num = len(offset_list)
    input_shape = math.sqrt((mem_end-mem_start)/4/kernel_num)
    return kernel_num, input_shape


def explain_tvm_conv2d_result_16(name: str, exp: str, mem_read_regions: list, mem_write_regions: list):
    mem_list = [(name, exp)]

    # TODO: here assume width==height
    input_shape = [1, 1, 1, 1]
    filter_shape = [1, 1, 1, 1]
    output_shape = [1, 1, 1, 1]

    offset_list = get_offset_list(mem_list[0][1], compiler='tvm', size=16)
    # print(offset_list)
    stride = offset_list[1] - offset_list[0]
    index = 0
    while index < len(offset_list) - 1:
        if offset_list[index+1] - offset_list[index] != stride:
            tmp1 = offset_list[index + 1]  # input[1] * input[2]
            tmp2 = offset_list[index] + stride  # filter[1] * filter[2]
            filter_shape[3] = index + 1
            filter_shape[2] = filter_shape[3]  # TODO assume
            filter_shape[1] = len(offset_list) / (filter_shape[2] * filter_shape[3])
            # input[1] = filter[1]
            input_shape[1] = filter_shape[1]
            input_shape[2] = input_shape[3] = get_input_shape(name, exp, mem_read_regions, input_shape[1], 16)
            break
        index += 1

    output_shape[2] = input_shape[2] - filter_shape[2] + 1
    output_shape[3] = input_shape[3] - filter_shape[3] + 1
    # get output shape
    # TODO: cannot get output_channel easily, because we do not have all mem_log (too huge and too slow)
    # filter_size = filter_shape[1] * filter_shape[2] * filter_shape[3]
    one_channel_size = output_shape[2] * output_shape[3]
    weights_region, output_channel = get_output_channel(mem_list[0][1], one_channel_size, mem_write_regions, compiler='tvm', on_the_right=False)
    output_shape[1] = output_channel
    filter_shape[0] = output_shape[1]

    # final shape
    print('input shape', input_shape)
    print('filter shape', filter_shape)
    print('output shape', output_shape)
    return filter_shape, input_shape, output_shape


def get_offset_list(value: str, compiler: str, size=4):
    times = value.count('*')
    if compiler == 'tvm':
        offset_list = get_addr_list(value, 'tvm', size)
    elif compiler == 'glow':
        offset_list = get_addr_list(value, 'glow', size)
    else:
        print('at get_offset_list')
        print('compiler not supported:', compiler)
        exit(-1)
        return
    start_addr = min(offset_list)
    for i in range(len(offset_list)):
        offset_list[i] = (offset_list[i] - start_addr) / 4
    if size == 4 and offset_list[0] > offset_list[-1]:
        offset_list.reverse()  # offset_list.sort()
    elif size == 16:
        offset_list.reverse()
    return offset_list


input_on_the_left = True


def get_addr_list(value: str, compiler: str, size=4):
    global input_on_the_left
    """

    :param value: the expression
    :param compiler: 'tvm' or 'glow'
    :return: list of used input addresses
    """
    addr_list = []
    if compiler == 'tvm' and size == 4:
        it = re.finditer(r'(0x[0-9a-f]+),4 \*', value)
        for match in it:
            addr = match.group(1)
            addr_list.append(int(addr, 16))
        return addr_list
    if compiler == 'tvm' and size == 16:
        it = re.finditer(r'\* (0x[0-9a-f]+),4', value)
        for match in it:
            addr = match.group(1)
            addr_list.append(int(addr, 16))
        return addr_list
    elif compiler == 'glow':
        # assume the input is on the left
        if input_on_the_left:
            it = re.finditer(r'(0x[0-9a-f]+),4 \*', value)
            for match in it:
                addr = match.group(1)
                addr_list.append(int(addr, 16))
            addr_list.sort()
        else:
            # input on the right
            addr_list.clear()
            it = re.finditer(r'\* (0x[0-9a-f]+),4', value)
            for match in it:
                addr = match.group(1)
                addr_list.append(int(addr, 16))
            addr_list.sort()
        if addr_list[-1] - addr_list[0] == (len(addr_list) - 1) * 4:
            input_on_the_left = False
            addr_list = get_addr_list(value, compiler)
        return addr_list


# ==============================================================
# Heuristics used to recover shape for Glow Conv2d
# ==============================================================
def explain_glow_conv2d_result(exp_log_path: str, mem_read_regions: list, mem_write_regions: list):
    name, exp = choose_one_4bytes(exp_log_path, mem_write_regions)
    if len(name) == 0:
        name, exp = choose_one_16bytes(exp_log_path, mem_write_regions)
        return explain_tvm_conv2d_result_16(name, exp, mem_read_regions, mem_write_regions)
    mem_list = [(name, exp)]
    mem_list.append(tuple(choose_one_4bytes(exp_log_path, mem_write_regions, 1)))


    # TODO: here assume width==height
    input_shape = [1, 1, 1, 1]
    filter_shape = [1, 1, 1, 1]
    output_shape = [1, 1, 1, 1]

    # get the filter shape and input shape from first output
    offset_list = get_offset_list(mem_list[0][1], compiler='glow')
    stride = offset_list[1]-offset_list[0]
    index = 0
    while index < len(offset_list) - 1:
        if offset_list[index+1] - offset_list[index] > stride:
            tmp1 = offset_list[index + 1]  # input[1] * input[2]
            tmp2 = offset_list[index] + stride  # filter[1] * filter[2]
            filter_shape[3] = len(offset_list)/tmp2
            filter_shape[2] = filter_shape[3]  # TODO assume
            filter_shape[1] = tmp2/filter_shape[2]
            # input[1] = filter[1]
            input_shape[1] = filter_shape[1]
            input_shape[2] = tmp1 / input_shape[1]
            input_shape[3] = input_shape[2]  # TODO assume
            break
        index += 1
    """
    addr_list_0 = get_addr_list(mem_list[0][1], 'glow', 4)
    if addr_list_0[0] > addr_list_0[-1]:
        addr_list_0.reverse()  # addr_list_0.sort()
    addr_list_1 = get_addr_list(mem_list[1][1], 'glow', 4)
    if addr_list_1[0] > addr_list_1[-1]:
        addr_list_1.reverse()  # addr_list_1.sort()
    addr_1 = addr_list_1[0]
    # idx_0 = addr_list_0.index(addr_1)
    idx_0 = 0
    while idx_0 < len(addr_list_0):
        if addr_list_0[idx_0] >= addr_1:
            break
        idx_0 += 1
    if idx_0 == 1:
        stride = 1
    elif idx_0 <= 3:
        stride = idx_0  # / filter_shape[1]  # TODO: calculate the stride, can be wrong
    else:
        stride = idx_0 / filter_shape[1]
    """
    # Does not work for GLOW, how could wew get the stride?
    output_shape[2] = math.ceil((input_shape[2] - filter_shape[2] + 1) / stride)
    output_shape[3] = math.ceil((input_shape[3] - filter_shape[3] + 1) / stride)

    # get output shape
    output_channel = 0
    one_channel_size = output_shape[2] * output_shape[3]
    weights_region, output_channel = get_output_channel(mem_list[0][1], one_channel_size, mem_write_regions,
                                                        compiler='glow')

    output_shape[1] = output_channel
    filter_shape[0] = output_shape[1]

    # final shape
    print('input shape', input_shape)
    print('filter shape', filter_shape)
    print('output shape', output_shape)


# ==============================================================
# Heuristics used to recover shape for TVM dense/fully-connected layer
# ==============================================================
def explain_tvm_dense_result(exp_log_path: str, mem_write_regions: list):
    name, exp = choose_one_4bytes(exp_log_path, mem_write_regions)
    if len(name) == 0:
        exit(-1)

    input_size = exp.count('*') * 4
    output_size = 0
    big_mem = (0, 0)
    for mem_blk in mem_write_regions:
        if (mem_blk[1] - mem_blk[0]) > (big_mem[1] - big_mem[0]):
            big_mem = mem_blk
    output_size = (big_mem[1] - big_mem[0]) / 4
    return input_size, output_size


# ==============================================================
# Heuristics used to recover shape for TVM add layer
# ==============================================================
def explain_tvm_add_result(exp_log_path: str, mem_read_regions: list, mem_write_regions: list):
    # TODO: cannot assume the order of input and bias
    # name, exp = choose_one_16bytes(exp_log_path)
    # match = re.search(r'\+ 0x([0-9a-f]+),4', exp)
    # bias_addr = int(match.group(1), 16)

    output_size = 0
    small_blk = (0, 0x7ffffff)
    for mem_blk in mem_read_regions:
        if 4 < (mem_blk[1] - mem_blk[0]) < (small_blk[1] - small_blk[0]):
            small_blk = mem_blk
    output_size = (small_blk[1] - small_blk[0]) / 4
    return output_size


# ==============================================================
# Heuristics used to recover shape for TVM max-pool2d layer
# ==============================================================
def explain_tvm_maxpool_result(exp_log_path: str, mem_write_regions: list):
    out_mem = (0, 0)
    for mem_blk in mem_write_regions:
        if (mem_blk[1] - mem_blk[0]) > (out_mem[1] - out_mem[1]):
            out_mem = mem_blk
    with open(exp_log_path, 'r') as f:
        exp_txt = f.read()
        lines = exp_txt.split('\n')
        idx = 0
        while idx < len(lines):
            name1 = lines[idx]
            idx += 1
            exp1 = lines[idx]
            idx += 1
            if out_mem[0] <= int(name1.split(',')[0].strip(), 16) <= out_mem[1] and \
                    int(math.sqrt(exp1.count('max')))**2 == exp1.count('max'):
                break
        name2 = lines[idx]
        idx += 1
        exp2 = lines[idx]
        idx += 1

    if name1.endswith(',4') and name2.endswith(',4'):
        kernel_size = math.sqrt(exp1.count('max'))
        match = re.search(r', 0x([0-9a-f]+),4\)', exp1[exp1.find(')'):])
        addr1 = int(match.group(1), 16)
        match = re.search(r', 0x([0-9a-f]+),4\)', exp2[exp2.find(')'):])
        addr2 = int(match.group(1), 16)
        stride = (addr2 - addr1) / 4
        return kernel_size, stride
    elif name1.endswith(',32') and name2.endswith(',32'):
        kernel_size = math.sqrt(exp1.count('max'))
        match = re.search(r'\(0x([0-9a-f]+),32, ', exp1[:exp1.find(')')])
        addr1 = int(match.group(1), 16)
        match = re.search(r'\(0x([0-9a-f]+),32, ', exp2[:exp2.find(')')])
        addr2 = int(match.group(1), 16)
        stride = (addr2 - addr1) / 16
        return kernel_size, stride


if __name__ == '__main__':
    pass
    # explain_tvm_conv2d_result('./mem_log.txt')
