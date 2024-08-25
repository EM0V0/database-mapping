import json
import logging
import openai

logging.basicConfig(level=logging.INFO)

client = openai.OpenAI(
    base_url="",
    api_key=""
)

mappings_file_path = 'field_mappings.json'
output_sql_path = 'generated_sql.sql'

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

try:
    with open(mappings_file_path, 'r', encoding='utf-8') as f:
        field_mappings = json.load(f)

    # 限制每个字段映射的展示长度，防止提示词过长
    def truncate_string(s, max_length=50):
        return s if len(s) <= max_length else s[:max_length] + '...'

    # 准备提示词
    prompt = "根据以下字段映射关系生成SQL语句:\n\n"
    for mapping in field_mappings:
        source_field = truncate_string(mapping['source']['field'])
        source_table = truncate_string(mapping['source']['table']['name'])
        target_field = truncate_string(mapping['target']['field'])
        target_table = truncate_string(mapping['target']['table']['name'])
        transformation_rule = truncate_string(mapping.get('transformationRule', ''))

        prompt += f"源字段: {source_field} (表: {source_table}) -> 目标字段: {target_field} (表: {target_table})"
        if transformation_rule:
            prompt += f" (转换规则: {transformation_rule})"
        prompt += "\n"

    prompt += "\n请生成上述映射关系的SQL插入语句。"

    try:
        messages = [
            {"role": "system", "content": "你是数据库迁移专家，现在有一个任务，需要根据字段映射关系生成SQL语句。"},
            {"role": "user", "content": prompt}
        ]
        response = call_openai_api(messages)
        response_content = extract_content(response)

        # Continue generating if the response is not complete
        while response.choices[0].finish_reason != 'stop':
            messages.append({"role": "assistant", "content": response_content})
            messages.append({"role": "user", "content": "请继续生成剩余的SQL语句。"})
            response = call_openai_api(messages)
            response_content += '\n' + extract_content(response)

        # 去除Markdown格式的代码块标记
        if response_content.startswith("```sql") and response_content.endswith("```"):
            response_content = response_content[5:-3].strip()

        # 保存生成的SQL语句
        with open(output_sql_path, 'w', encoding='utf-8') as f:
            f.write(response_content)

        logging.info("SQL generation successful")
    except Exception as e:
        logging.exception("Exception occurred during SQL generation")
        raise

except Exception as e:
    logging.exception("Exception occurred while loading field mappings")
    raise
