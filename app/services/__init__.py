"""
数据导出服务 - 支持CSV和JSON格式导出
"""
import csv
import json
import io
from datetime import datetime


def export_to_csv(data, filename_prefix='export'):
    """
    将数据导出为CSV格式（含UTF-8 BOM，确保中文在Excel中正常显示）
    :param data: 字典列表
    :param filename_prefix: 文件名前缀
    :return: (csv_content, filename)
    """
    if not data:
        return '', f'{filename_prefix}_{datetime.now().strftime("%Y%m%d")}.csv'

    output = io.StringIO()
    # 写入UTF-8 BOM，确保Excel正确识别UTF-8编码
    output.write('﻿')
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    # 处理复杂类型（dict/list转JSON字符串，None转空字符串）
    cleaned_data = []
    for row in data:
        cleaned_row = {}
        for k, v in row.items():
            if v is None:
                cleaned_row[k] = ''
            elif isinstance(v, (dict, list)):
                cleaned_row[k] = json.dumps(v, ensure_ascii=False, default=str)
            else:
                cleaned_row[k] = v
        cleaned_data.append(cleaned_row)
    writer.writerows(cleaned_data)

    filename = f'{filename_prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return output.getvalue(), filename


def export_to_json(data, filename_prefix='export'):
    """
    将数据导出为JSON格式
    :param data: 字典列表或字典
    :param filename_prefix: 文件名前缀
    :return: (json_content, filename)
    """
    filename = f'{filename_prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    return json.dumps(data, ensure_ascii=False, indent=2, default=str), filename
