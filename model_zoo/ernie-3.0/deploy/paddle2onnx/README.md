# ERNIE 3.0 ONNX导出及部署指南
本文介绍ERNIE 3.0 模型模型如何转化为ONNX模型，并基于ONNXRuntime引擎部署，本文将以序列标注和分类两大场景作为介绍示例。
- [ERNIE 3.0 ONNX导出及部署指南](#ERNIE3.0ONNX导出及部署指南)
  - [1. 环境准备](#1-环境准备)
  - [2. 序列标注模型推理](#2-序列标注模型推理)
    - [2.1 模型获取](#21-模型获取)
    - [2.2 模型转换](#22-模型转换)
    - [2.3 ONNXRuntime推理样例](#23-ONNXRuntime推理样例)
  - [3. 分类模型推理](#3-分类模型推理)
    - [3.1 模型获取](#31-模型获取)
    - [3.2 模型转换](#32-模型转换)
    - [3.3 ONNXRuntime推理样例](#33-ONNXRuntime推理样例)
## 1. 环境准备
ERNIE 3.0模型转换与ONNXRuntime预测部署依赖Paddle2ONNX和ONNXRuntime，Paddle2ONNX支持将Paddle模型转化为ONNX模型格式，算子目前稳定支持导出ONNX Opset 7~15，更多细节可参考：[Paddle2ONNX](https://github.com/PaddlePaddle/Paddle2ONNX)
如果基于CPU部署，请使用如下命令安装所需依赖:
```
python -m pip install onnxruntime
```
如果基于GPU部署，请先确保机器已正确安装NVIDIA相关驱动和基础软件，确保CUDA >= 11.2，CuDNN >= 8.2，并使用以下命令安装所需依赖:
```
python -m pip install onnxruntime-gpu onnx onnxconverter-common
```

## 2. 序列标注模型推理
### 2.1 模型获取
用户可使用自己训练的模型进行推理，具体训练调优方法可参考[模型训练调优](./../../README.md#微调)，也可以使用我们提供的msra_ner数据集训练的ERNIE 3.0模型，请执行如下命令获取模型：
```
# 获取序列标注FP32模型
wget https://paddlenlp.bj.bcebos.com/models/transformers/ernie_3.0/msra_ner_pruned_infer_model.zip
unzip msra_ner_pruned_infer_model.zip
```
### 2.2 模型转换
使用Paddle2ONNX将Paddle静态图模型转换为ONNX模型格式的命令如下，以下命令成功运行后，将会在当前目录下生成ner_model.onnx模型文件。
```
paddle2onnx --model_dir msra_ner_pruned_infer_model/ --model_filename float32.pdmodel --params_filename float32.pdiparams --save_file ner_model.onnx --opset_version 13 --enable_onnx_checker True --enable_dev_version True
```
Paddle2ONNX的命令行参数说明请查阅：[Paddle2ONNX命令行参数说明](https://github.com/PaddlePaddle/Paddle2ONNX#参数选项)

### 2.3 ONNXRuntime推理样例
请使用如下命令进行部署
```
python infer.py --task_name token_cls --model_path ner_model.onnx
```
输出打印如下:
```
input data: 北京的涮肉，重庆的火锅，成都的小吃都是极具特色的美食。
The model detects all entities:
entity: 北京   label: LOC   pos: [0, 1]
entity: 重庆   label: LOC   pos: [6, 7]
entity: 成都   label: LOC   pos: [12, 13]
-----------------------------
input data: 乔丹、科比、詹姆斯和姚明都是篮球界的标志性人物。
The model detects all entities:
entity: 乔丹   label: PER   pos: [0, 1]
entity: 科比   label: PER   pos: [3, 4]
entity: 詹姆斯   label: PER   pos: [6, 8]
entity: 姚明   label: PER   pos: [10, 11]
-----------------------------
```
在GPU设备的CUDA计算能力 (CUDA Compute Capability) 大于7.0，包括V100、T4、A10、A100、GTX 20系列和30系列显卡等设备上，可以使用如下命令开启ONNXRuntime的FP16进行推理加速：
```
python infer.py --task_name token_cls --model_path ner_model.onnx --use_fp16
```
输出打印如下:
```
input data: 北京的涮肉，重庆的火锅，成都的小吃都是极具特色的美食。
The model detects all entities:
entity: 北京   label: LOC   pos: [0, 1]
entity: 重庆   label: LOC   pos: [6, 7]
entity: 成都   label: LOC   pos: [12, 13]
-----------------------------
input data: 乔丹、科比、詹姆斯和姚明都是篮球界的标志性人物。
The model detects all entities:
entity: 乔丹   label: PER   pos: [0, 1]
entity: 科比   label: PER   pos: [3, 4]
entity: 詹姆斯   label: PER   pos: [6, 8]
entity: 姚明   label: PER   pos: [10, 11]
-----------------------------
```
infer.py脚本中的参数说明：
| 参数 |参数说明 |
|----------|--------------|
|--task_name | 配置任务名称，可选seq_cls和token_cls，默认为seq_cls|
|--model_name_or_path | 模型的路径或者名字，默认为ernie-3.0-medium-zh|
|--model_path | 用于推理的ONNX模型的路径|
|--max_seq_length |最大序列长度，默认为128|
|--use_fp16 |是否开启FP16进行推理，默认关闭，请GPU设备的CUDA计算能力 (CUDA Compute Capability) 大于7.0时才可开启，否则不会带来加速效果|

**Note**：在GPU设备的CUDA计算能力 (CUDA Compute Capability) 大于7.0时才可以开启FP16进行加速，在CPU或者CUDA计算能力 (CUDA Compute Capability) 小于7.0时开启不会带来加速效果。

## 3. 分类模型推理
### 3.1 模型获取
用户可使用自己训练的模型进行推理，具体训练调优方法可参考[模型训练调优](./../../README.md#微调)，也可以使用我们提供的tnews数据集训练的ERNIE 3.0模型，请执行如下命令获取模型：
```
# 分类模型模型：
wget  https://paddlenlp.bj.bcebos.com/models/transformers/ernie_3.0/tnews_pruned_infer_model.zip
unzip tnews_pruned_infer_model.zip
```
### 3.2 模型转换
使用Paddle2ONNX将Paddle静态图模型转换为ONNX模型格式的命令如下，以下命令成功运行后，将会在当前目录下生成tnews_model.onnx模型文件。
```
paddle2onnx --model_dir tnews_pruned_infer_model/ --model_filename float32.pdmodel --params_filename float32.pdiparams --save_file tnews_model.onnx --opset_version 13 --enable_onnx_checker True --enable_dev_version True
```
Paddle2ONNX的命令行参数说明请查阅：[Paddle2ONNX命令行参数说明](https://github.com/PaddlePaddle/Paddle2ONNX#参数选项)

### 3.3 ONNXRuntime推理样例
请使用如下命令进行部署
```
python infer.py --task_name seq_cls --model_path tnews_model.onnx
```
输出打印如下:
```
input data: 未来自动驾驶真的会让酒驾和疲劳驾驶成历史吗？
seq cls result:
label: news_car   confidence: 0.554353654384613
-----------------------------
input data: 黄磊接受华少快问快答，不光智商逆天，情商也不逊黄渤
seq cls result:
label: news_entertainment   confidence: 0.9495906829833984
-----------------------------
```
和命名实体识别模型推理类似，开启FP16推理加速的命令如下：
```
python infer.py --task_name seq_cls --model_path tnews_model.onnx --use_fp16
```
输出打印如下:
```
input data: 未来自动驾驶真的会让酒驾和疲劳驾驶成历史吗？
seq cls result:
label: news_car   confidence: 0.5540072321891785
-----------------------------
input data: 黄磊接受华少快问快答，不光智商逆天，情商也不逊黄渤
seq cls result:
label: news_entertainment   confidence: 0.9496589303016663
-----------------------------
```
infer.py脚本中的参数说明：
| 参数 |参数说明 |
|----------|--------------|
|--task_name | 配置任务名称，可选seq_cls和token_cls，默认为seq_cls|
|--model_name_or_path | 模型的路径或者名字，默认为ernie-3.0-medium-zh|
|--model_path | 用于推理的ONNX模型的路径|
|--max_seq_length |最大序列长度，默认为128|
|--use_fp16 |是否开启FP16进行推理，默认关闭，请GPU设备的CUDA计算能力 (CUDA Compute Capability) 大于7.0时才可开启，否则不会带来加速效果|
