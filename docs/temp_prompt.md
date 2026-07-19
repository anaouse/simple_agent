1. inputbox模仿at命令加入slash命令，实现 /model，我现在大概可以知道只在初次访问网站时候向后端申请一次模型数据，修改config后要刷新一下网页重新加载
2. 我现在模型、apikey、模型url都写在.env里面，我希望.env应该改成config path，然后是~/.simple_agent/config.json，内部应该有model的列表，一个模型包含名称，apikey，url，以及加入compatible字段，默认anthropic方便之后加入其他不同api格式。然后前端默认使用第一个模型，当然你修改不了 .env 你只要修改代码然后告诉我config和.env怎么改就好
3. 前端界面新写一个组件，放到InputBox上方比InputBox高度小一点，叫SessionInfo.tsx，放当前模型的名称信息，之后我会在这个组件加入更多的信息