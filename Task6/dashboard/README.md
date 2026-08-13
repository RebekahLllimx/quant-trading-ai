# TASK6 交互展示

- `index.html`：只读、离线的结果看板，双击即可查看。
- `tools/csv_regression.html`：纯前端CSV回归小工具，可选择X、Y以及线性/逻辑回归，并下载预测CSV和模型JSON。

双击`tools/csv_regression.html`即可使用，无需启动服务器。数据只保存在当前浏览器页面的内存中，不上传、不使用后端或数据库。由于浏览器无法原生生成与scikit-learn兼容的Python pickle，页面下载模型JSON；正式`.pkl`仍由TASK6 Python脚本生成。
