看 @D:/projects/agent/docs/specified.md 了解项目基础知识，然后：
1. 在 py 当中加入openai_agent.py openai_adaptor.py openai_session_adaptor.py，实现支持openai格式api的模型聊天以及工具结合，工具调用，实现openai消息格式和本项目event的转化，最终目的应该是同一段聊天记录，我可以和openai格式的模型聊天，也可以和anthropic格式的模型聊天
2. 注意 /model 切换模型的命令，现在config当中的compatible字段会加入openai字段，然后这个时候的模型就要选择openai agent
3. 还有其他和模型api格式有关但是现在写死的地方也要修改