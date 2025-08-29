# Translate4Original
基于Python和OpenAI API的完整保留排版的Word/Excel/PPT文档全文四语翻译，支持标准OpenAI API调用，vLLM\LM Studio等均可无损接入。

## 功能特性
- **多语言支持**：支持中文、英文、日文、泰文四种语言之间的互译
- **多格式支持**：支持上传和翻译DOC、DOCX、XLS、XLSX、PPT、PPTX格式的文件
- **格式保留**：翻译过程中完整保留原文件的格式排版
- **API配置**：支持通过界面配置OpenAI API密钥和参数
- **提示词设置**：内置默认提示词，并支持用户自定义提示词
- **文件下载**：翻译完成后提供文件下载功能

## 安装与配置

### 前提条件

- Python 3.8或更高版本
- 具备OpenAI API，也可以是本地部署的AI大模型API

### 安装步骤

1. 克隆或下载项目代码
2. 安装依赖包

cd Translate4Original
pip install -r requirements.txt

3. 配置环境变量（可选）

创建或编辑'.env'文件，添加以下内容：

OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

> 注意：如果不配置.env文件，也可以在应用界面中设置API参数

## 使用方法
1. 启动应用
cd Translate4Original
python app.py

2. 打开浏览器，访问 'http://localhost:5000'

3. 设置API参数（如果未在.env文件中配置）
   - 点击"API配置"按钮
   - 输入OpenAI API密钥、API基础URL和模型名称
   - 点击"保存"按钮

4. 上传并翻译文件
   - 选择源语言和目标语言
   - 上传要翻译的文件（支持DOC、DOCX、XLS、XLSX、PPT、PPTX格式）
   - 可选：修改翻译提示词
   - 点击"开始翻译"按钮
   - 等待翻译完成后，点击"下载翻译文件"按钮获取翻译后的文件

## 注意事项

- 文件大小限制为16MB
- 对于.doc、.xls、.ppt格式的文件，由于技术限制，需要先转换为对应的.docx、.xlsx、.pptx格式后再进行翻译
- 翻译速度取决于文件大小、网络状况和OpenAI API响应速度
- 请确保您的OpenAI API密钥有足够的额度用于翻译

## 常见问题

1. **API密钥无效**
   - 请检查您的OpenAI API密钥是否正确
   - 确保您的API密钥有足够的额度
   - 可能需要等待几分钟让密钥生效

2. **文件格式不支持**
   - 请确保您上传的文件格式在支持列表中
   - 对于旧版Office格式（.doc、.xls、.ppt），请先转换为新版格式

3. **翻译过程中出错**
   - 可能是网络问题，请检查您的网络连接
   - 可能是OpenAI API暂时不可用，请稍后再试
   - 如果问题持续存在，请检查API配置和密钥
  
## License
[Apache License 2.0](LICENSE)
