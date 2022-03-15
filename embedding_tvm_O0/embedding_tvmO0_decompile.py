#! /usr/bin/python3
import os
import sys
sys.path.append("../")
import math
import utils
from utils import list_to_json, dict_to_json, json_to_dict, json_to_list
import pin_tools


if __name__ == '__main__':
    utils.funcs_dir = "/export/d1/zliudc/DLE_Decompiler/TVM/rebuild_ida/embedding/embedding_tvm_O0_funcs/"

    # prepared in advance
    prog_path = "/export/d1/zliudc/DLE_Decompiler/TVM/rebuild_ida/embedding/embedding_tvm_O0"
    in_data = ''  # no input needed
    label_file = './step1.txt'
    config_file = './config.json'

    # (tmp files) generated during analysis
    log_path = './embedding_tvm_O0_func_call.log'
    tmp_log_path = './inst_trace.log'
    exp_log_path = './mem_exp.log'
    mem_read_log_path = './mem_read.log'
    mem_write_log_path = './mem_write.log'
    mem_dump_log_path = './mem_dump.log'

    # ===============================
    # Recover the Computational Graph
    # ===============================
    # without parameters, only start addresses
    utils.get_funcs_trace(prog_path, in_data, log_path, label_file, compiler='tvm', only_fused=False)
    utils.print_layer_label_tvm(log_path, only_fused=False)

    # with parameters from entry functions
    utils.get_funcs_trace(prog_path, in_data, log_path, label_file, compiler='tvm', only_fused=True)
    param_list = utils.print_layer_label_tvm(log_path, only_fused=True)
    # print(param_list)
    func_meta_data, topo_list = utils.print_input_id(log_path)  
    # print(func_meta_data)
    # print(topo_list)
    
    # ===============================
    # Recover other layers
    # ===============================
    func_data = {
                 'embedding': '0037.sub_405A30.txt',  # take
                 'avg_pool': '0025.sub_403330.txt',
                 'matmul': '0031.sub_4046E0.txt',
                 'add': '0019.sub_401D70.txt'
                 }

    for func_type, func_name in func_data.items():
        utils.generate_inst_trace(func_name, tmp_log_path, prog_path, in_data)

        utils.generate_symbolic_expression(func_name, tmp_log_path, exp_log_path, max_inst=5000000)

        shape = utils.recover_shape_tvm(func_name, exp_log_path,
                                        mem_read_log_path, mem_write_log_path,
                                        prog_path, in_data, func_type=func_type)
        print(shape)
        if 'embedding' in func_type:
            embedding_start = int('0x41ec40', 16)  # get fomr topo_list
            for param in param_list:
                if param > embedding_start:
                    dict_size = (param - embedding_start)/4/shape
                    dict_size = math.floor(dict_size)
                    print('embedding dict size: {}'.format(dict_size))
                    break
        for i in range(len(func_meta_data)):
            if func_meta_data[i][0] == func_name:
                if 'embedding' in func_type:
                    func_meta_data[i][1] = (dict_size, shape)
                else:
                    func_meta_data[i][1] = shape
                break
    
    list_to_json(topo_list, './topo_list.json')
    dict_to_json(func_meta_data, './meta_data.json')

    # ===============================
    # Extract Parameters
    # ===============================
    # func_meta_data is collected from previous output
    func_meta_data = [
                      ('0037.sub_405A30.txt', (25006, 100), '0x405a30', '0x41ec40', 'embedding'),
                      ('0031.sub_4046E0.txt', (1, 100), '0x4046e0', '0xdacc40', 'matmul'),
                      ('0019.sub_401D70.txt', (1, 1), '0x401d70', '0x415440', 'add'),
                      ]
    for fun_data in func_meta_data:
        func_name = fun_data[0]
        w_shape = fun_data[1]
        dump_point = fun_data[2]
        dump_addr = fun_data[3]
        func_type = fun_data[4]
        utils.extract_params_general(prog_path, in_data, w_shape, dump_point,
                                     mem_dump_log_path, func_name, dump_addr)
