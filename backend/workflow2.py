import json
import logging
import openai
import re

logging.basicConfig(level=logging.INFO)

client = openai.OpenAI(
    base_url="",
    api_key=""
)

source_file_path = 'uploaded_tables.json'
with open(source_file_path, 'r', encoding='utf-8') as file:
    source_data = json.load(file)

target_file_path = 'uploaded_target.json'
with open(target_file_path, 'r', encoding='utf-8') as file:
    target_data = json.load(file)


def call_openai_api(messages, max_tokens=4096):
    response = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response


def extract_content(response):
    return response.choices[0].message.content.strip()


def clean_response_content(response_content):
    # 去除 Markdown 代码块标记
    response_content = response_content.replace("```json", "").replace("```", "").strip()
    # 去除所有的 [ 和 ]
    response_content = response_content.replace("[", "").replace("]", "")
    return response_content


def remove_incomplete_json_fragment(content):
    # 寻找最后一个完整的 JSON 对象
    last_open_brace = content.rfind("{")
    last_close_brace = content.rfind("}")
    if last_open_brace > last_close_brace:
        content = content[:last_open_brace]
    return content


def add_missing_commas(content):
    # 为每个 JSON 对象后添加逗号，确保 JSON 数组格式正确
    content = content.strip()
    if content and content[-1] != ",":
        content += ","
    return content


def generate_field_mappings(source_tables, target_table):
    messages = [
        {"role": "system", "content": "你是数据库迁移专家，现在有一个任务，需要将多个来源表中的字段映射到一个目标表中。"},
        {"role": "user", "content": f"来源表数据:\n{json.dumps(source_tables, ensure_ascii=False, indent=4)}"},
        {"role": "user", "content": f"目标表数据:\n{json.dumps(target_table, ensure_ascii=False, indent=4)}"},
        {"role": "user", "content": """
#### 具体任务
1. **字段映射分析**：理解每个来源表的字段名和字段注释，确定目标表字段在来源表中最可能对应的字段。
2. **映射关系表创建**：生成一个包含目标表中全部字段的映射关系表，内容示例如下：
[
  {
    "sourceField": "字段名",
    "sourceTable": "来源表名",
    "targetField": "目标字段名",
    "targetTable": "目标表名"
  },
  ...
]
#### 注意事项
- 只需输出最终的json代码，不用输出中间步骤。
- 确保来源表表名的准确性，不要编造不存在的表名。
- 不要遗漏标准表中的任何一个字段。
"""}
    ]

    try:
        response_content = ""
        while True:
            response = call_openai_api(messages)
            part_content = extract_content(response)

            # 清理响应内容，去除多余的 Markdown 代码块标记和所有的 [ 和 ]
            cleaned_part_content = clean_response_content(part_content)

            # 移除不完整的 JSON 片段
            cleaned_part_content = remove_incomplete_json_fragment(cleaned_part_content)

            # 为 JSON 片段添加缺失的逗号
            cleaned_part_content = add_missing_commas(cleaned_part_content)

            response_content += cleaned_part_content

            # 检查是否结束
            if response.choices[0].finish_reason == 'stop':
                break
            else:
                messages.append({"role": "assistant", "content": part_content})
                messages.append({"role": "user", "content": "请继续生成剩余的字段映射。"})

        # 移除最后一个逗号
        response_content = response_content.rstrip(',')

        # 日志记录响应内容
        logging.info(f"Response content: {response_content}")

        # 确保响应内容是有效的 JSON 数组，添加 [ 和 ]
        response_content = f"[{response_content}]"
        mappings = json.loads(response_content)

        return mappings
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode mappings response: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Error during OpenAI API call or processing: {str(e)}")
        return []


try:
    target_table = {
        "name": target_data['name'],
        "fields": target_data.get('fields', [])
    }
    mappings = generate_field_mappings(source_data, target_table)

    with open('mapping_fields.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=4)

    logging.info("Successfully generated field mappings")
except Exception as e:
    logging.exception("Exception occurred during field mapping generation")
    raise
