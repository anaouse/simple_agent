---
created_at: 2026-08-27T11:55:31+08:00
status: todo # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

现在希望inputBox可以输入图片，先支持截图后直接ctrl+v输入图片，现在主流的一般好像都是插入后输入栏上方显示附件比如图片文件这种，而且比较厉害的是图片和附件还可以点击查看，以及每个附件显示的右上角有一个 x 点击后就可以删除

## 我要的

1. InputBox先只支持ctrl+v插入图片作为附件，然后可以通过关闭按钮删除图片，先不用支持点击后放大预览（但是好像既然都显示了那好像也是很简单？这个我不确定，你先给我方案，好做就做）
2. 现在有openai和anthropic两大api协议，要加入图片发送功能，统一使用base64（应该是这样吧？这个我也不太懂），先实现anthropic的，先不用管openai那边
2.1 主要要考虑的问题有，第一个历史记录如何保存？现在我的历史记录因为是纯文本所以直接保存的文本，但是现在要是我发送的信息有图片，是不是也可以直接base64保存问纯文本？
2.2 如果图片作为base64保存在历史记录当中那么历史记录的格式你看看要怎么改？涉及到对话历史的复原和保存问题
2.3 我发送图片作为附件的时候如何顺利展示到聊天栏当中？现在MessagesArea只是一个个MessageNode组合而成的，在用户的MessageNode下方新加入附件显示，类似InputBox一样？可行吗？
2.4 第二个问题有的模型没有图片识别功能，怎么办？我认为标示每个图片是否有其实不方便，让用户自己意识到就好，也就是说InputBox一直提供可以输入图片，但是消息发送后出问题那就返回消息说明该模型不支持图片输入，然后自动变为正常的文字消息输入

# 资料

## Using Images with the Anthropic API

In addition to the OpenAI-compatible endpoint above, you can send images through the Anthropic-compatible /messages endpoint (base_url = https://api.deepseek.com/anthropic). For general setup, see Anthropic API.

The difference is the shape of the image content block. Instead of image_url, Anthropic uses an image block with a source object whose type is one of base64, url, or file:

import anthropic

client = anthropic.Anthropic()  # ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic

message = client.messages.create(
    model="deepseek-v4-flash-vision-exp",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "<BASE64_DATA>",
                    },
                },
            ],
        }
    ],
)
print(message.content)

## Restrictions

    Images are supported in user messages only: images in system or assistant messages return a 400 error.
    Only vision models (deepseek-v4-flash-vision-exp) accept images; other models return a 400 error ("This model does not support image").
    User text containing the reserved image placeholder token is rejected with a 400 error.

## Token Usage

Images are converted into tokens based on their dimensions, and these tokens are billed together with your text tokens.

Before inference, every image is automatically resized:

    Images with a total pixel count below roughly 384×384 are scaled up while preserving their aspect ratio.
    Larger images are scaled down while preserving their aspect ratio, so that the total pixel count after resizing is roughly that of an 800×800 image.

As a result, there is an upper bound of 384 tokens per image: for example, a 2000×2000 image and a 5000×5000 image consume the same number of tokens after resizing. When a request contains multiple images, each image is counted independently under the same rule — there is no separate calculation for multi-image requests.

To estimate the token cost of an image of a specific size, use the image token calculator on the Token & Token Usage page.

## Detail Level

For image_url inputs you can optionally set a detail field to control how the image is processed:
Value   Behavior
low The image is downscaled to 512×512 before inference. Faster and cheaper when fine visual detail is not important.
high    Keeps the original image. (Provided for compatibility; equivalent to original.)
original    Keeps the original image.
auto    Automatic selection. Currently equivalent to original.

{
  "type": "image_url",
  "image_url": {"url": "https://example.com/image.jpg", "detail": "low"}
}

