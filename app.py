from flask import Flask, render_template, request, send_file, jsonify
import os
import tempfile
from functools import wraps
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
import json
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session

# 导入文件处理工具
from utils.file_processor import process_file, save_translated_file

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)  # 设置会话密钥，用于安全存储用户会话信息

# 设置上传文件夹和允许的文件扩展名
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB上限

# 获取OpenAI API配置（默认值）
DEFAULT_OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEFAULT_OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'http://modelurl/v1')
DEFAULT_OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'modelname')

# 支持的语言列表
SUPPORTED_LANGUAGES = [
    {'code': 'zh', 'name': '中文'},
    {'code': 'en', 'name': '英文'},
    {'code': 'ja', 'name': '日文'},
    {'code': 'th', 'name': '泰文'}
]

# 默认提示词 - 第一步翻译
DEFAULT_PROMPT_STEP1 = "你是一位专业的语言学家，专业于从事{{source_lang}}到{{target_lang}}的翻译工作。你的任务是从{{source_lang}}到{{target_lang}}的翻译工作，请提供{{source_lang}}的{{target_lang}}翻译。\n请只提供翻译内容，不要提供任何解释和其他文本。" 

# 默认提示词 - 第二步翻译纠错
DEFAULT_PROMPT_STEP2 = "你是一位专业的语言学家，专门从事到{{source_lang}}到{{target_lang}}的翻译工作。你将获得一段{{source_lang}}及其翻译（第一步提示词后生成的译文，你的目标是改进这个翻译。你的任务是仔细阅读{{source_lang}}，并参照第一步提示词后生成的译文，进行修改和完善翻译。请在编辑翻译时考虑以下几点：\n(i) 准确性（通过纠正添加错误、误译、遗漏或未翻译的文本）\n(ii) 流畅性（通过应用{{target_lang}}的语法、拼写和标点规则，确保没有不必要的重复）\n(iii) 风格（通过确保翻译反映源文本的风格）(iv) 术语（不适合上下文的术语、使用不一致）\n(v) 其他错误\n请只提供翻译内容，不要提供任何解释和其他文本。"

# 账号验证API地址(账号验证界面）
AUTH_API_URL = 'http://API_AUTH'

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 调用OpenAI API进行翻译
def translate_with_openai(text, source_lang, target_lang, custom_prompt=None, api_key=None, api_base=None, model=None):
    # 使用传入的API配置，如果没有则使用默认值
    api_key = api_key or DEFAULT_OPENAI_API_KEY
    api_base = api_base or DEFAULT_OPENAI_API_BASE
    model = model or DEFAULT_OPENAI_MODEL
    
    if not api_key:
        raise ValueError("OpenAI API密钥未配置，请在API设置中输入您的密钥")
    
    prompt = custom_prompt or DEFAULT_PROMPT_STEP1
    prompt = prompt.replace("{{source_lang}}", source_lang).replace("{{target_lang}}", target_lang)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(f"{api_base}/chat/completions", headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 401:
            raise Exception("API密钥无效，请检查您的密钥是否正确")
        elif http_err.response.status_code == 429:
            raise Exception("请求过于频繁，请稍后再试")
        else:
            raise Exception(f"翻译过程中出错: {str(http_err)}")
    except Exception as e:
        raise Exception(f"翻译过程中出错: {str(e)}")

# 两步翻译流程
def two_step_translation(text, source_lang, target_lang, prompt_step1=None, prompt_step2=None, api_key=None, api_base=None, model=None):
    # 第一步：初步翻译
    step1_prompt = prompt_step1 or DEFAULT_PROMPT_STEP1
    translated_text = translate_with_openai(
        text,
        source_lang,
        target_lang,
        step1_prompt,
        api_key,
        api_base,
        model
    )
    
    # 第二步：翻译纠错和完善
    step2_prompt = prompt_step2 or DEFAULT_PROMPT_STEP2
    step2_prompt = step2_prompt.replace("{{source_lang}}", source_lang).replace("{{target_lang}}", target_lang)
    
    # 构建第二步的提示词，包含原文和初步翻译结果
    correction_prompt = f"原文: {text}\n\n初步翻译: {translated_text}"
    
    # 调用API进行纠错
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key or DEFAULT_OPENAI_API_KEY}"
    }
    
    data = {
        "model": model or DEFAULT_OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": step2_prompt},
            {"role": "user", "content": correction_prompt}
        ],
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(f"{(api_base or DEFAULT_OPENAI_API_BASE)}/chat/completions", headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        # 如果第二步出错，返回第一步的翻译结果
        return translated_text

# 验证账号密码的函数
def verify_user_credentials(userid, password):
    try:
        # 准备请求数据
        data = {
            "Userid": userid,
            "UserPasswd": password
        }
        
        # 发送POST请求到验证API
        response = requests.post(AUTH_API_URL, json=data)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        
        # 根据返回结果判断验证是否通过
        if result == 1:
            return True, "验证通过"
        elif result == 0:
            return False, "账号或密码不正确"
        elif result == -1:
            return False, "系统故障，请稍后再试"
        else:
            return False, f"未知的返回结果: {result}"
            
    except requests.exceptions.RequestException as e:
        return False, f"连接验证服务器失败: {str(e)}"
    except Exception as e:
        return False, f"验证过程中发生错误: {str(e)}"

# 登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否已登录
        if 'userid' not in session:
            # 如果未登录，重定向到登录页面
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 登录页面路由
@app.route('/login')
def login():
    # 如果用户已经登录，直接重定向到主页
    if 'userid' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# 登录请求处理路由
@app.route('/login', methods=['POST'])
def login_post():
    try:
        # 获取请求数据
        data = request.get_json()
        userid = data.get('userid')
        password = data.get('password')
        
        # 验证输入
        if not userid or not password:
            return jsonify({'success': False, 'message': '请输入账号和密码'})
            
        # 调用验证函数
        is_valid, message = verify_user_credentials(userid, password)
        
        if is_valid:
            # 验证通过，将用户信息存入会话
            session['userid'] = userid
            # 返回用户ID，以便前端存储并显示
            return jsonify({'success': True, 'message': '登录成功', 'userid': userid})
        else:
            # 验证失败，返回错误消息
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录过程中发生错误: {str(e)}'})

# 登出路由
@app.route('/logout')
def logout():
    # 从会话中删除用户信息
    session.pop('userid', None)
    # 重定向到登录页面
    return redirect(url_for('login'))

# 调用OpenAI API进行翻译
# 两步翻译流程
# 主页路由
@app.route('/')
@login_required
def index():
    return render_template('index.html', languages=SUPPORTED_LANGUAGES)

# 设置页面路由
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', 
                          languages=SUPPORTED_LANGUAGES,
                          default_prompt_step1=DEFAULT_PROMPT_STEP1,
                          default_prompt_step2=DEFAULT_PROMPT_STEP2)

# 翻译文件路由
@app.route('/translate', methods=['POST'])
@login_required
def translate_file():
    try:
        # 获取当前登录用户的userid
        userid = session.get('userid')
        
        # 发送账号信息到验证API，记录翻译行为
        try:
            requests.post(
                AUTH_API_URL,
                json={'Userid': userid, 'Action': 'translate'}
            )
        except Exception as e:
            # 如果发送账号信息失败，不影响翻译功能的正常运行
            print(f"发送账号信息失败: {str(e)}")
            
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400
        
        file = request.files['file']
        
        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        # 检查文件类型是否允许
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件类型'}), 400
        
        # 获取表单数据
        source_lang_code = request.form.get('source_lang')
        target_lang_code = request.form.get('target_lang')
        
        # 从表单获取自定义提示词（如果有）
        prompt_step1 = request.form.get('prompt_step1')
        prompt_step2 = request.form.get('prompt_step2')
        
        # 获取API配置（来自表单或使用默认值）
        api_key = request.form.get('api_key', DEFAULT_OPENAI_API_KEY)
        api_base = request.form.get('api_base', DEFAULT_OPENAI_API_BASE)
        model = request.form.get('model', DEFAULT_OPENAI_MODEL)
        
        # 验证语言代码
        source_lang = next((lang['name'] for lang in SUPPORTED_LANGUAGES if lang['code'] == source_lang_code), source_lang_code)
        target_lang = next((lang['name'] for lang in SUPPORTED_LANGUAGES if lang['code'] == target_lang_code), target_lang_code)
        
        # 保存上传的文件到临时目录
        filename = secure_filename(file.filename)
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_file_path)
        
        try:
            # 创建一个包装函数，传递API配置参数和两步翻译流程
            def translate_wrapper(text, source, target, prompt=None):
                # prompt参数在这里不会使用，因为我们需要两个不同的提示词
                return two_step_translation(
                    text, 
                    source, 
                    target, 
                    prompt_step1, 
                    prompt_step2, 
                    api_key, 
                    api_base, 
                    model
                )
            
            # 处理文件并获取翻译后的内容
            translated_content, file_type = process_file(
                temp_file_path, 
                source_lang, 
                target_lang, 
                translate_wrapper
            )
            
            # 保存翻译后的文件
            output_filename = f"translated_{filename}"
            output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            save_translated_file(translated_content, file_type, output_file_path)
            
            # 返回翻译后的文件路径供下载
            return jsonify({
                'success': True,
                'file_path': output_file_path,
                'filename': output_filename
            })
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 文件下载路由
@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 发送文件并设置下载完成后删除
        response = send_file(file_path, as_attachment=True, download_name=filename)
        
        # 注册一个回调函数，在响应发送后删除文件
        @response.call_on_close
        def cleanup(): 
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 主函数
if __name__ == '__main__':
    # 确保uploads文件夹存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # 绑定到0.0.0.0:5000，使应用在内网可访问
    app.run(host='0.0.0.0', port=5000, debug=True)
