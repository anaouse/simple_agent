我现在想要做一个可以单纯可以聊天的mvp出来，先不考虑数据持久化和工具调用

# 后端

/app
  main.py 就是fastapi主设置
  config.py 提供 websocket 接口
  ai/
    anthropic_agent.py 这里写一个anthropic api compitable的 agent 类，然后前端打开请求的时候后端直接实例化一个类
    anthropic_adaptor.py 负责把anthropic sdk的流式输出内容转化为前端可见的东西的一个中间接口

# 前端

HomePage.tsx 排列一个 MessageArea，然后下方是InputBox
InputBox.tsx其实就是一个输入框
input-box.css
MessageNode.tsx我现在希望聊天页面不是单纯的用户发送后ai回答，而是把这些东西都包装到MessageNode当中，默认不展开，node可以点击后打开内部内容，然后如果是在回应的话就实时渲染
message-node.css
MessageArea.tsx：从上到下按顺序排列MessageNode，用户-回答-用户-回答这样子
