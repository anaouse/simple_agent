看@D:/projects/agent/docs/specified.md了解项目
1. 前端选择一个项目后，后端维护当前项目文件夹下已有的文件夹和文件，使用watchfiles库，如果后端文件新建或改变文件后发送给前端
2. 参考： ../my_agent/src/idle/at_completer.py
3. 前端InputBox支持 @ 命令，打@后跳出本项目下的文件夹和文件并且支持打字过滤