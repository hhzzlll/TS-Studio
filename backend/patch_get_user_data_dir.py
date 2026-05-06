import re

with open('/root/TS-Studio/backend/api/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_func = """
def get_user_data_dir(user):
    import shutil
    base_data = os.path.join(settings.BASE_DIR, 'data')
    if not user or not user.is_authenticated:
        return base_data
        
    data_dir = os.path.join(base_data, str(user.id))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        # copy default csv files to user dir when created so they have them
        for f in ['ETTh1.csv', 'ETTh2.csv', 'Exchange.csv']:
            src = os.path.join(base_data, f)
            dst = os.path.join(data_dir, f)
            if os.path.exists(src):
                shutil.copy(src, dst)
    return data_dir
"""

old_func_pattern = r"def get_user_data_dir\(user\):[\s\S]*?return data_dir"
text = re.sub(old_func_pattern, new_func.strip(), text)

with open('/root/TS-Studio/backend/api/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Patched.")
