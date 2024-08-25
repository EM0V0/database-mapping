#workflow.py
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import openai
import pandas as pd

logging.basicConfig(level=logging.INFO)

# Gets API Key from environment variable OPENAI_API_KEY
client = openai.OpenAI(
    base_url="",
    api_key=""
)

source_file_path = 'uploaded_source.xlsx'
df = pd.read_excel(source_file_path, sheet_name=None)

target_file_path = 'uploaded_target.json'
with open(target_file_path, 'r', encoding='utf-8') as file:
    target_data = json.load(file)


def process_sheet(sheet_name, sheet_df):
    return f'Sheet name: {sheet_name}\n' + sheet_df.to_string(index=False) + '\n\n'


try:
    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda item: process_sheet(*item), df.items())

    table_data = ''.join(results)

    messages = [
        {"role": "system",
         "content": "你是数据库迁移专家，现在有一个任务，需要从多个来源表中将数据映射到一个目标表中。其中，来源表的表结构在Source.xlsx文件中，目标表的表结构在Target.json中。"},
        {"role": "user", "content": f"表格数据:\n{table_data}"},
        {"role": "user", "content": f"目标表数据:\n{json.dumps(target_data, ensure_ascii=False, indent=4)}"},
        {"role": "user", "content": """
#### 具体任务 
1.**目标表结构分析**：分析目标表中的内容，根据字段名称和注释，理解表中每个字段的含义。
2.**来源表结构分析**：分析Source.xlsx文件中包含的所有表格，理解每个来源表的表名与表中每个字段的含义(尤其关注包含病人信息的表格)。
3.**关联表分析预测**：基于对目标表字段的理解，预测可能与目标表存在关联关系的所有来源表。
4.**输出关联的来源表**：列出和目标表最相关的来源表的中文表名，以json格式输出。选出大约10张来源表，确保不遗漏任何潜在的来源表。

#### 注意事项
- 只需输出最终的json代码，不用输出中间步骤。
- 确保来源表表名的准确性，不要编造不存在的表名。
"""}
    ]

    completion = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
    )

    response_content = completion.choices[0].message.content
    table_names = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9_]+', response_content)

    with open('table_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({"union": table_names}, f, ensure_ascii=False, indent=4)
    print("Successfully processed the sheets and generated analysis")
    logging.info("Successfully processed the sheets and generated analysis")
except Exception as e:
    logging.exception("Exception occurred during processing")
    raise
