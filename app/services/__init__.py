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
    :return: (csv_bytes, filename)  bytes类型
    """
    if not data:
        return b'', f'{filename_prefix}_{datetime.now().strftime("%Y%m%d")}.csv'

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
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
    # 编码为UTF-8并添加BOM（确保Excel正确识别中文）
    return b'\xef\xbb\xbf' + output.getvalue().encode('utf-8'), filename


def export_to_json(data, filename_prefix='export'):
    """
    将数据导出为JSON格式
    :param data: 字典列表或字典
    :param filename_prefix: 文件名前缀
    :return: (json_content, filename)
    """
    filename = f'{filename_prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    return json.dumps(data, ensure_ascii=False, indent=2, default=str), filename
