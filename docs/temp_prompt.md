1. ~/.simple_agent/config.json当中多一个skills_path字段，存放skill的文件夹
2. skill的样式是：
skills/
    ffmpeg/
        SKILL.md (这个markdown说明这个skill是如何使用的以及文件夹是什么意思，文件如何使用)
        xxx/
        xx.py
3. 模仿/model命令加入一个 /skill 命令，前端输入 /skill 后空格跳出skills文件夹下的文件夹名称就是skill。最后选择类似 /skill ffmpeg这是写下来的对话xxx，然后prompt在后端转化为：“请你阅读 `skills_path/ffmpeg/SKILL.md` 然后结合这个文件夹下的提示理接下来的问题”
4. /model和/skill已有的东西我希望类似 @ 命令使用watchfiles进行监控，/model监控 ~/.simple_agent/config.json这个文件夹，如果有变化向前端发送，然后/skill就是监控 skills_path里面（只有文件夹当中有 SKILL.md才算一个skill），当然skills_path文件夹要先存在，所以都和 @ 命令类似使用websocket进行通信