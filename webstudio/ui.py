import gradio as gr

from .config import *
from .core import *
from .settings import *
from .workflows import *

theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="rose",
    neutral_hue="slate",
).set(
    body_background_fill="#f6f2ea",
    block_background_fill="#ffffff",
    block_border_width="1px",
    block_border_color="#e6ded2",
    button_primary_background_fill="#243b53",
    button_primary_background_fill_hover="#1b2f43",
    button_primary_text_color="#ffffff",
)

css = """
.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
}
.app-shell {
    padding: 18px 8px 28px;
}
.hero {
    min-height: 190px;
    padding: 34px 38px;
    border-radius: 8px;
    background:
        linear-gradient(90deg, rgba(4, 13, 24, .98) 0%, rgba(12, 25, 38, .94) 52%, rgba(81, 45, 34, .82) 100%),
        url("https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1600&q=80");
    background-size: cover;
    background-position: center;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    margin-bottom: 16px;
}
.hero h1 {
    color: #ffffff !important;
    font-size: clamp(34px, 4.8vw, 58px);
    line-height: 1.04;
    margin: 0 0 12px;
    letter-spacing: 0;
    font-weight: 850;
    -webkit-text-stroke: .6px rgba(255, 255, 255, .34);
    text-shadow:
        0 2px 0 rgba(0, 0, 0, .34),
        0 8px 24px rgba(0, 0, 0, .72),
        0 0 38px rgba(255, 255, 255, .22);
}
.hero p {
    color: #f8fbff !important;
    max-width: 780px;
    margin: 0;
    color: rgba(255, 255, 255, .92);
    font-size: 17px;
    line-height: 1.7;
    text-shadow: 0 1px 10px rgba(0, 0, 0, .4);
}
.mode-note {
    margin: 0 0 14px;
    padding: 12px 14px;
    border-left: 4px solid #a86240;
    background: #fff8ef;
    color: #4e4035;
    border-radius: 6px;
    line-height: 1.6;
}
.section-title {
    font-size: 13px;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #6f6254;
    font-weight: 700;
    margin: 4px 0 10px;
}
.status-box textarea {
    font-weight: 600 !important;
}
.gradio-container textarea {
    overflow-y: auto !important;
    scrollbar-gutter: stable;
    resize: vertical !important;
}
.gradio-container textarea::-webkit-scrollbar {
    width: 10px;
}
.prompt-history-box textarea {
    min-height: 360px !important;
    max-height: 520px !important;
    overflow-y: auto !important;
    resize: vertical !important;
}
.control-row > div {
    min-width: min(220px, 100%) !important;
    flex: 1 1 220px !important;
}
.control-row .wrap,
.control-row .form {
    min-width: 0 !important;
}
[data-testid="dropdown"] input,
[data-testid="dropdown"] .single-select,
[data-testid="dropdown"] .token {
    padding-right: 38px !important;
    text-overflow: ellipsis !important;
}
.gallery-panel {
    min-height: 0 !important;
}
.gallery-panel .grid-wrap,
.gallery-panel .grid-container,
.gallery-panel .thumbnail-lg {
    min-height: 0 !important;
}
.gallery-panel button[aria-label*="Close"],
.gallery-panel button[title*="Close"],
.gallery-panel button[aria-label*="关闭"],
.gallery-panel button[title*="关闭"] {
    z-index: 10000 !important;
    pointer-events: auto !important;
}
.gallery-panel [role="dialog"],
.gallery-panel .modal,
.gallery-panel .preview {
    z-index: 9999 !important;
}
body:has(:fullscreen) button,
button[aria-label*="Close"],
button[title*="Close"],
button[aria-label*="关闭"],
button[title*="关闭"] {
    pointer-events: auto !important;
}
[role="dialog"],
.modal,
.preview,
.fullscreen {
    z-index: 9999 !important;
}
footer {
    display: none !important;
}
@media (max-width: 720px) {
    .hero {
        padding: 24px 20px;
        min-height: 150px;
    }
}
"""

js = """
() => {
    const isCloseControl = (target) => {
        const control = target.closest("button, [role='button']");
        if (!control) return false;
        const text = (control.innerText || control.textContent || "").trim().toLowerCase();
        const label = (
            control.getAttribute("aria-label") ||
            control.getAttribute("title") ||
            control.getAttribute("data-testid") ||
            ""
        ).toLowerCase();
        return text === "close" || text === "关闭" || label.includes("close") || label.includes("关闭");
    };

    const pressEscape = () => {
        document.dispatchEvent(new KeyboardEvent("keydown", {
            key: "Escape",
            code: "Escape",
            keyCode: 27,
            which: 27,
            bubbles: true,
            cancelable: true,
        }));
    };

    document.addEventListener("click", async (event) => {
        if (!isCloseControl(event.target)) return;

        if (document.fullscreenElement) {
            event.preventDefault();
            event.stopPropagation();
            try {
                await document.exitFullscreen();
            } catch (error) {
                console.debug("Fullscreen exit skipped", error);
            }
            setTimeout(pressEscape, 120);
        }
    }, true);
}
"""

with gr.Blocks(title="GPT Image WebStudio", analytics_enabled=False) as app:
    with gr.Column(elem_classes=["app-shell"]):
        gr.HTML(
            """
            <section class="hero">
                <h1>GPT Image WebStudio</h1>
                <p>一个为 GPT Image 系列接口打造的本地创作工作台：支持文生图、图生图、随机提示词、创意批量、自我迭代、提示词反推与统一接口管理。</p>
            </section>
            """
        )

        with gr.Tabs():
            with gr.Tab("手动模式"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">创作设置</div>')
                        gr.HTML('<div class="mode-note">手动模式：输入一段固定提示词，按设定数量生成图片。适合验证一个明确想法；接口、保存目录和重试参数请在“设置”页统一维护。</div>')
                        prompt_input = gr.Textbox(
                            label="提示词",
                            value=CONFIG["prompt"],
                            placeholder="例如：清晨的玻璃花房里，一位穿白裙的女孩正在照顾蓝色鸢尾花，电影感，细腻光影",
                            lines=7,
                            max_lines=10,
                        )

                        with gr.Row():
                            image_model_provider_input = gr.Dropdown(
                                label="模型选择",
                                choices=IMAGE_MODEL_PRESETS,
                                value=CONFIG["image_model_provider"],
                            )
                            image_count_input = gr.Slider(
                                label="生成数量",
                                minimum=1,
                                maximum=12,
                                value=CONFIG["image_count"],
                                step=1,
                            )
                            concurrency_input = gr.Slider(
                                label="并发张数",
                                minimum=1,
                                maximum=6,
                                value=CONFIG["concurrency"],
                                step=1,
                            )
                            aspect_ratio_input = gr.Dropdown(
                                label="图片比例",
                                choices=list(ASPECT_RATIOS.keys()),
                                value=CONFIG["aspect_ratio"],
                            )
                            resolution_input = gr.Dropdown(
                                label="分辨率",
                                choices=list(RESOLUTION_PRESETS.keys()),
                                value=CONFIG["resolution"],
                            )

                        with gr.Row():
                            generate_btn = gr.Button("开始生成", variant="primary", size="lg")
                            stop_btn = gr.Button("停止", variant="stop", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">生成结果</div>')
                        gallery_output = gr.Gallery(
                            label="图片画廊",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("图生图"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">图片编辑</div>')
                        gr.HTML('<div class="mode-note">图生图：上传 1-4 张参考图，输入编辑提示词，再按设定数量生成新图片。大于 2.5MB 的输入图会先自动压缩；接口、保存目录、品质和重试参数请在“设置”页统一维护。多图时请用“第一张参考图 / 第二张参考图”，并补充图片特征，识别更稳定。</div>')
                        edit_images_input = gr.File(
                            label="参考图片",
                            file_count="multiple",
                            file_types=[".png", ".jpg", ".jpeg", ".webp"],
                            type="filepath",
                        )
                        edit_prompt_input = gr.Textbox(
                            label="编辑提示词",
                            value=CONFIG["prompt"],
                            placeholder="例如：保持人物与构图，将背景改成黄昏海边咖啡馆，柔和电影光，色彩更温暖",
                            lines=7,
                            max_lines=10,
                        )

                        with gr.Row():
                            edit_image_model_provider_input = gr.Dropdown(
                                label="模型选择",
                                choices=IMAGE_MODEL_PRESETS,
                                value=CONFIG["image_model_provider"],
                            )
                            edit_image_count_input = gr.Slider(
                                label="生成数量",
                                minimum=1,
                                maximum=12,
                                value=CONFIG["image_count"],
                                step=1,
                            )
                            edit_concurrency_input = gr.Slider(
                                label="并发张数",
                                minimum=1,
                                maximum=6,
                                value=CONFIG["concurrency"],
                                step=1,
                            )
                            edit_aspect_ratio_input = gr.Dropdown(
                                label="图片比例",
                                choices=list(ASPECT_RATIOS.keys()),
                                value=CONFIG["aspect_ratio"],
                            )
                            edit_resolution_input = gr.Dropdown(
                                label="分辨率",
                                choices=list(RESOLUTION_PRESETS.keys()),
                                value=CONFIG["resolution"],
                            )

                        edit_input_fidelity_input = gr.Dropdown(
                            label="输入保真度",
                            choices=INPUT_FIDELITY_PRESETS,
                            value=CONFIG["edit_input_fidelity"],
                            info="high 更倾向保留参考图细节，low 更适合大幅重绘。",
                        )

                        with gr.Row():
                            edit_generate_btn = gr.Button("开始图生图", variant="primary", size="lg")
                            edit_stop_btn = gr.Button("停止", variant="stop", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">编辑结果</div>')
                        edit_gallery_output = gr.Gallery(
                            label="图片画廊",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        edit_status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("随机模式"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">随机设置</div>')
                        gr.HTML('<div class="mode-note">随机模式：先由文本模型生成一段随机提示词，再用这段提示词生成多张图片。适合快速抽卡同一主题的多个变化。</div>')
                        random_preference_input = gr.Textbox(
                            label="本次创作方向",
                            value=CONFIG["random_preference"],
                            placeholder="例如：白色丝袜",
                            lines=1,
                        )
                        random_prompt_output = gr.Textbox(
                            label="随机提示词",
                            value=CONFIG["prompt"],
                            lines=8,
                            max_lines=12,
                            interactive=False,
                        )

                        with gr.Row():
                            random_image_model_provider_input = gr.Dropdown(
                                label="模型选择",
                                choices=IMAGE_MODEL_PRESETS,
                                value=CONFIG["image_model_provider"],
                            )
                            random_image_count_input = gr.Slider(
                                label="生成数量",
                                minimum=1,
                                maximum=12,
                                value=CONFIG["image_count"],
                                step=1,
                            )
                            random_concurrency_input = gr.Slider(
                                label="并发张数",
                                minimum=1,
                                maximum=6,
                                value=CONFIG["concurrency"],
                                step=1,
                            )
                            random_aspect_ratio_input = gr.Dropdown(
                                label="图片比例",
                                choices=list(ASPECT_RATIOS.keys()),
                                value=CONFIG["aspect_ratio"],
                            )
                            random_resolution_input = gr.Dropdown(
                                label="分辨率",
                                choices=list(RESOLUTION_PRESETS.keys()),
                                value=CONFIG["resolution"],
                            )

                        with gr.Row():
                            random_generate_btn = gr.Button("随机生成并出图", variant="primary", size="lg")
                            random_stop_btn = gr.Button("停止", variant="stop", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">生成结果</div>')
                        random_gallery_output = gr.Gallery(
                            label="图片画廊",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        random_status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("创意模式"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">创意设置</div>')
                        gr.HTML('<div class="mode-note">创意模式：并发生成多段不同随机提示词，并将每段提示词各生成一张图片。适合夜间批量探索大量创意方向。</div>')
                        creative_preference_input = gr.Textbox(
                            label="本次创作方向",
                            value=CONFIG["random_preference"],
                            placeholder="例如：白色丝袜、便利店夜班、雨后窗边",
                            lines=1,
                        )
                        creative_prompts_output = gr.Textbox(
                            label="随机提示词组",
                            value="",
                            lines=12,
                            max_lines=18,
                            interactive=False,
                        )

                        with gr.Row():
                            creative_image_model_provider_input = gr.Dropdown(
                                label="模型选择",
                                choices=IMAGE_MODEL_PRESETS,
                                value=CONFIG["image_model_provider"],
                            )
                            creative_count_input = gr.Slider(
                                label="生成张数",
                                minimum=1,
                                maximum=100,
                                value=CONFIG["creative_count"],
                                step=1,
                            )
                            creative_text_concurrency_input = gr.Slider(
                                label="文本并发",
                                minimum=1,
                                maximum=50,
                                value=CONFIG["text_concurrency"],
                                step=1,
                            )
                            creative_image_concurrency_input = gr.Slider(
                                label="图片并发",
                                minimum=1,
                                maximum=12,
                                value=CONFIG["image_concurrency"],
                                step=1,
                            )
                            creative_aspect_ratio_input = gr.Dropdown(
                                label="图片比例",
                                choices=list(ASPECT_RATIOS.keys()),
                                value=CONFIG["aspect_ratio"],
                            )
                            creative_resolution_input = gr.Dropdown(
                                label="分辨率",
                                choices=list(RESOLUTION_PRESETS.keys()),
                                value=CONFIG["resolution"],
                            )
                        creative_random_enhance_input = gr.Checkbox(
                            label="随机增强（会禁用文本模型并行处理功能！）",
                            value=CONFIG["creative_random_enhance"],
                        )

                        with gr.Row():
                            creative_generate_btn = gr.Button("批量创意生成", variant="primary", size="lg")
                            creative_stop_btn = gr.Button("停止", variant="stop", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">生成结果</div>')
                        creative_gallery_output = gr.Gallery(
                            label="图片画廊",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        creative_status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("自我迭代模式"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">迭代设置</div>')
                        gr.HTML('<div class="mode-note">自我迭代模式：可随机生成初始提示词，也可手动输入初始提示词。每轮视觉评估都会带上创作主题或初始创作方向，以及本轮图片使用的提示词，尽量避免越迭代越跑题。</div>')
                        iterative_prompt_source_input = gr.Radio(
                            label="初始提示词来源",
                            choices=ITERATION_PROMPT_SOURCE_PRESETS,
                            value=CONFIG["iteration_prompt_source"],
                        )
                        iterative_preference_input = gr.Textbox(
                            label="创作主题" if CONFIG["iteration_prompt_source"] == "自定义提示词" else "初始创作方向",
                            value=CONFIG["random_preference"],
                            placeholder="例如：课堂午睡、雨夜车站、便利店夜班" if CONFIG["iteration_prompt_source"] == "自定义提示词" else "例如：白色丝袜、雨夜车站、图书馆",
                            lines=1,
                        )
                        iterative_custom_prompt_input = gr.Textbox(
                            label="初始提示词（点击输入你需要的提示词）" if CONFIG["iteration_prompt_source"] == "自定义提示词" else "初始提示词（由文本模型随机生成）",
                            value=(CONFIG["iteration_custom_prompt"] or CONFIG["prompt"]) if CONFIG["iteration_prompt_source"] == "自定义提示词" else "",
                            placeholder="像手动模式一样输入第 1 轮要使用的完整提示词" if CONFIG["iteration_prompt_source"] == "自定义提示词" else "等待提示词生成",
                            lines=7,
                            max_lines=12,
                            interactive=CONFIG["iteration_prompt_source"] == "自定义提示词",
                        )
                        iterative_prompt_output = gr.Textbox(
                            label="每轮提示词",
                            value=CONFIG["prompt"],
                            lines=12,
                            max_lines=18,
                            interactive=False,
                            elem_classes=["prompt-history-box"],
                        )

                        with gr.Row(elem_classes=["control-row"]):
                            iterative_image_model_provider_input = gr.Dropdown(
                                label="模型选择",
                                choices=IMAGE_MODEL_PRESETS,
                                value=CONFIG["image_model_provider"],
                                min_width=220,
                            )
                            iteration_batch_count_input = gr.Slider(
                                label="生成数量",
                                minimum=1,
                                maximum=10,
                                value=CONFIG["iteration_batch_count"],
                                step=1,
                                min_width=220,
                            )

                        with gr.Row(elem_classes=["control-row"]):
                            iteration_count_input = gr.Slider(
                                label="迭代次数",
                                minimum=1,
                                maximum=6,
                                value=CONFIG["iteration_count"],
                                step=1,
                                min_width=220,
                            )
                            iteration_text_concurrency_input = gr.Slider(
                                label="初始提示词并发",
                                minimum=1,
                                maximum=10,
                                value=CONFIG["iteration_text_concurrency"],
                                step=1,
                                min_width=220,
                            )
                        iteration_random_enhance_input = gr.Checkbox(
                            label="随机增强（会禁用文本模型并行处理功能！）",
                            value=CONFIG["iteration_random_enhance"],
                        )

                        with gr.Row(elem_classes=["control-row"]):
                            iteration_image_concurrency_input = gr.Slider(
                                label="图片并发数量",
                                minimum=1,
                                maximum=10,
                                value=CONFIG["iteration_image_concurrency"],
                                step=1,
                                min_width=220,
                            )
                            iterative_aspect_ratio_input = gr.Dropdown(
                                label="图片比例",
                                choices=list(ASPECT_RATIOS.keys()),
                                value=CONFIG["aspect_ratio"],
                                min_width=220,
                            )

                        with gr.Row(elem_classes=["control-row"]):
                            iterative_resolution_input = gr.Dropdown(
                                label="分辨率",
                                choices=list(RESOLUTION_PRESETS.keys()),
                                value=CONFIG["resolution"],
                                min_width=220,
                            )

                        with gr.Row():
                            iterative_generate_btn = gr.Button("开始自我迭代", variant="primary", size="lg")
                            iterative_stop_btn = gr.Button("停止", variant="stop", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">迭代结果</div>')
                        iterative_gallery_output = gr.Gallery(
                            label="最终图片",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        gr.HTML('<div class="section-title">迭代过程</div>')
                        iterative_process_gallery_output = gr.Gallery(
                            label="迭代过程",
                            columns=2,
                            rows=1,
                            height="auto",
                            object_fit="contain",
                            show_label=False,
                            allow_preview=True,
                            elem_classes=["gallery-panel"],
                        )
                        iterative_status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("提示词反推"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=340):
                        gr.HTML('<div class="section-title">图片输入</div>')
                        gr.HTML('<div class="mode-note">上传图片，或填写本地图片路径。应用会先自动压缩图片，再调用设置页中的多模态模型反推出可复用的中文提示词。</div>')
                        reverse_image_input = gr.Image(
                            label="上传图片",
                            type="filepath",
                            sources=["upload", "clipboard"],
                            height=360,
                        )
                        reverse_local_path_input = gr.Textbox(
                            label="本地图片路径",
                            placeholder=r"例如：D:\Images\AI_Cards\img_xxx.png",
                            lines=1,
                        )
                        reverse_generate_btn = gr.Button("开始反推提示词", variant="primary", size="lg")

                    with gr.Column(scale=6, min_width=360):
                        gr.HTML('<div class="section-title">反推结果</div>')
                        reverse_prompt_output = gr.Textbox(
                            label="反推提示词",
                            lines=16,
                            max_lines=24,
                            buttons=["copy"],
                            elem_classes=["prompt-history-box"],
                        )
                        reverse_status_output = gr.Textbox(
                            label="状态",
                            lines=4,
                            elem_classes=["status-box"],
                        )

            with gr.Tab("设置"):
                gr.HTML('<div class="section-title">全局设置</div>')
                gr.HTML('<div class="mode-note">这里集中管理所有模式共用的接口、保存目录、重试策略和提示词模板。修改后点击“保存设置”即可对后续生成生效；如果刷新了页面，请点击“重新读取设置”同步当前配置。也可以关闭正在运行的脚本窗口后重新启动，界面会直接显示已保存的设置。重试策略对文本模型、图片生成、多模态评估和图片 URL 下载全部生效。</div>')

                with gr.Row(equal_height=False):
                    with gr.Column(scale=1, min_width=360):
                        settings_save_dir_input = gr.Textbox(
                            label="保存目录",
                            value=CONFIG["save_dir"],
                            placeholder="留空则保存到当前项目的 AI_Cards 文件夹",
                        )
                        with gr.Accordion("图片生成接口", open=True):
                            gr.HTML('<div class="mode-note">用途：生成图片。支持 OpenAI Images 兼容接口。示例：https://example.com 或 https://example.com/v1/images/generations</div>')
                            settings_base_url_input = gr.Textbox(label="API 地址", value=CONFIG["base_url"])
                            settings_model_id_input = gr.Textbox(label="模型 ID", value=CONFIG["model_id"])
                            settings_quality_input = gr.Dropdown(
                                label="品质",
                                choices=QUALITY_PRESETS,
                                value=CONFIG["quality"],
                            )
                            settings_api_key_input = gr.Textbox(
                                label="API Key",
                                value=CONFIG["api_key"],
                                type="password",
                            )

                        with gr.Accordion("Seedream 接口", open=False):
                            gr.HTML('<div class="mode-note">官方方舟格式使用 /api/v3/images/generations；OpenAI 兼容中转格式复用 /v1/images/generations 与 /v1/images/edits。中转站地址可填写域名根地址或 /v1。</div>')
                            settings_seedream_base_url_input = gr.Textbox(label="API 地址", value=CONFIG["seedream_base_url"])
                            settings_seedream_model_id_input = gr.Dropdown(
                                label="模型 ID",
                                choices=SEEDREAM_MODEL_ID_PRESETS,
                                value=normalize_seedream_model_id(CONFIG["seedream_model_id"]),
                                allow_custom_value=True,
                                info="根据模型 ID 自动识别 Pro/Lite；Lite 兼容 doubao-seedream-5-0-260128。",
                            )
                            settings_seedream_interface_format_input = gr.Dropdown(
                                label="接口格式",
                                choices=SEEDREAM_INTERFACE_FORMAT_PRESETS,
                                value=normalize_seedream_interface_format(CONFIG["seedream_interface_format"]),
                            )
                            with gr.Row():
                                settings_seedream_response_format_input = gr.Dropdown(
                                    label="返回格式",
                                    choices=SEEDREAM_RESPONSE_FORMAT_PRESETS,
                                    value=CONFIG["seedream_response_format"],
                                )
                                settings_seedream_output_format_input = gr.Dropdown(
                                    label="输出格式",
                                    choices=SEEDREAM_OUTPUT_FORMAT_PRESETS,
                                    value=CONFIG["seedream_output_format"],
                                )
                                settings_seedream_watermark_input = gr.Dropdown(
                                    label="水印",
                                    choices=SEEDREAM_WATERMARK_PRESETS,
                                    value=CONFIG["seedream_watermark"],
                                )
                            settings_seedream_api_key_input = gr.Textbox(
                                label="API Key",
                                value=CONFIG["seedream_api_key"],
                                type="password",
                            )

                        with gr.Accordion("文本模型接口", open=True):
                            gr.HTML('<div class="mode-note">用途：生成随机提示词。支持 OpenAI Chat、OpenAI Responses、Gemini 原生、Claude Messages；选择“自动识别”时会根据 URL 和模型 ID 判断。建议格式：https://example.com/v1</div>')
                            settings_random_base_url_input = gr.Textbox(label="API 地址", value=CONFIG["random_base_url"])
                            settings_random_model_id_input = gr.Textbox(label="模型 ID", value=CONFIG["random_model_id"])
                            settings_random_protocol_input = gr.Dropdown(
                                label="协议",
                                choices=MODEL_PROTOCOL_PRESETS,
                                value=CONFIG["random_protocol"],
                            )
                            settings_random_reasoning_effort_input = gr.Dropdown(
                                label="思考档位",
                                choices=REASONING_EFFORT_PRESETS,
                                value=CONFIG["random_reasoning_effort"],
                            )
                            settings_random_api_key_input = gr.Textbox(
                                label="API Key",
                                value=CONFIG["random_api_key"],
                                type="password",
                            )

                        with gr.Accordion("多模态模型接口", open=True):
                            gr.HTML('<div class="mode-note">用途：读取已生成图片并优化下一轮提示词。建议使用 Gemini 模型，也支持 OpenAI Chat、OpenAI Responses、Gemini 原生、Claude Messages；选择“自动识别”时会根据 URL 和模型 ID 判断。建议格式：https://example.com</div>')
                            settings_iteration_base_url_input = gr.Textbox(label="API 地址", value=CONFIG["iteration_base_url"])
                            settings_iteration_model_id_input = gr.Textbox(label="模型 ID", value=CONFIG["iteration_model_id"])
                            settings_iteration_protocol_input = gr.Dropdown(
                                label="协议",
                                choices=MODEL_PROTOCOL_PRESETS,
                                value=CONFIG["iteration_protocol"],
                            )
                            settings_iteration_reasoning_effort_input = gr.Dropdown(
                                label="思考档位",
                                choices=REASONING_EFFORT_PRESETS,
                                value=CONFIG["iteration_reasoning_effort"],
                            )
                            settings_iteration_api_key_input = gr.Textbox(
                                label="API Key",
                                value=CONFIG["iteration_api_key"],
                                type="password",
                            )

                        with gr.Accordion("重试设置", open=True):
                            gr.HTML('<div class="mode-note">作用范围：文本模型提示词生成、图片生成、多模态视觉评估、图片 URL 下载。每次请求失败后会等待指定间隔再重试；超过次数后，该任务会报错或跳过，其他可继续的任务不会被中断。</div>')
                            with gr.Row():
                                settings_retry_count_input = gr.Slider(
                                    label="重试次数",
                                    minimum=0,
                                    maximum=5,
                                    value=CONFIG["retry_count"],
                                    step=1,
                                )
                                settings_retry_delay_input = gr.Slider(
                                    label="重试间隔秒",
                                    minimum=0,
                                    maximum=30,
                                    value=CONFIG["retry_delay"],
                                    step=1,
                                )
                                settings_image_request_delay_input = gr.Slider(
                                    label="生图并发间隔秒",
                                    minimum=0,
                                    maximum=30,
                                    value=CONFIG["image_request_delay"],
                                    step=1,
                                    info="只影响文生图和图生图的并发启动节奏，用于避开中转站限流；不等同于失败后的重试间隔。",
                                )

                    with gr.Column(scale=1, min_width=420):
                        gr.HTML('<div class="mode-note">提示词模板支持变量：{{date}}、{{time}}、{{datetime}}、{{preference}}、{{used_scenes}}；场景概述模板支持 {{prompt}}；视觉迭代还支持 {{current_prompt}}、{{creation_theme}}、{{user_initial_direction}}、{{image}}。</div>')
                        settings_random_system_prompt_input = gr.Textbox(
                            label="文本模型系统提示词（用于提示词生成）",
                            value=CONFIG["random_system_prompt"],
                            lines=8,
                            max_lines=16,
                        )
                        settings_random_user_prompt_input = gr.Textbox(
                            label="文本模型用户提示词（用于提示词生成）",
                            value=CONFIG["random_user_prompt"],
                            lines=8,
                            max_lines=16,
                        )
                        settings_random_scene_summary_prompt_input = gr.Textbox(
                            label="文本模型场景概述提示词（用于随机增强）",
                            value=CONFIG["random_scene_summary_prompt"],
                            lines=7,
                            max_lines=14,
                        )
                        settings_iteration_optimizer_prompt_input = gr.Textbox(
                            label="视觉模型提示词（用于视觉评估迭代模式）",
                            value=CONFIG["iteration_optimizer_prompt"],
                            lines=10,
                            max_lines=20,
                        )
                        settings_reverse_prompt_input = gr.Textbox(
                            label="视觉模型提示词（用于提示词反推）",
                            value=CONFIG["reverse_prompt"],
                            lines=8,
                            max_lines=16,
                        )

                        with gr.Row():
                            settings_save_btn = gr.Button("保存设置", variant="primary", size="lg")
                            settings_reload_btn = gr.Button("重新读取设置", variant="secondary", size="lg")
                        settings_status_output = gr.Textbox(label="保存状态", lines=2)

    manual_event = generate_btn.click(
        fn=generate_image,
        inputs=[
            prompt_input,
            settings_save_dir_input,
            image_count_input,
            concurrency_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            image_model_provider_input,
            aspect_ratio_input,
            resolution_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
        ],
        outputs=[gallery_output, status_output],
    )
    stop_btn.click(
        fn=lambda: request_stop("manual"),
        outputs=[status_output],
        cancels=[manual_event],
        queue=False,
    )

    edit_event = edit_generate_btn.click(
        fn=generate_image_edit,
        inputs=[
            edit_images_input,
            edit_prompt_input,
            settings_save_dir_input,
            edit_image_count_input,
            edit_concurrency_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            edit_image_model_provider_input,
            edit_aspect_ratio_input,
            edit_resolution_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
            edit_input_fidelity_input,
        ],
        outputs=[edit_gallery_output, edit_status_output],
    )
    edit_stop_btn.click(
        fn=lambda: request_stop("edit"),
        outputs=[edit_status_output],
        cancels=[edit_event],
        queue=False,
    )

    random_event = random_generate_btn.click(
        fn=generate_random_image,
        inputs=[
            settings_save_dir_input,
            random_image_count_input,
            random_concurrency_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            random_image_model_provider_input,
            random_aspect_ratio_input,
            random_resolution_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
            settings_random_base_url_input,
            settings_random_model_id_input,
            settings_random_api_key_input,
            settings_random_protocol_input,
            settings_random_reasoning_effort_input,
            random_preference_input,
        ],
        outputs=[random_prompt_output, random_gallery_output, random_status_output],
    )
    random_stop_btn.click(
        fn=lambda: request_stop("random"),
        outputs=[random_status_output],
        cancels=[random_event],
        queue=False,
    )

    creative_event = creative_generate_btn.click(
        fn=generate_creative_images,
        inputs=[
            settings_save_dir_input,
            creative_count_input,
            creative_random_enhance_input,
            creative_text_concurrency_input,
            creative_image_concurrency_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            creative_image_model_provider_input,
            creative_aspect_ratio_input,
            creative_resolution_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
            settings_random_base_url_input,
            settings_random_model_id_input,
            settings_random_api_key_input,
            settings_random_protocol_input,
            settings_random_reasoning_effort_input,
            creative_preference_input,
        ],
        outputs=[creative_prompts_output, creative_gallery_output, creative_status_output],
    )
    creative_stop_btn.click(
        fn=lambda: request_stop("creative"),
        outputs=[creative_status_output],
        cancels=[creative_event],
        queue=False,
    )

    iterative_event = iterative_generate_btn.click(
        fn=generate_iterative_image,
        inputs=[
            settings_save_dir_input,
            iterative_prompt_source_input,
            iterative_custom_prompt_input,
            iteration_count_input,
            iteration_batch_count_input,
            iteration_random_enhance_input,
            iteration_text_concurrency_input,
            iteration_image_concurrency_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            iterative_image_model_provider_input,
            iterative_aspect_ratio_input,
            iterative_resolution_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
            settings_random_base_url_input,
            settings_random_model_id_input,
            settings_random_api_key_input,
            settings_random_protocol_input,
            settings_random_reasoning_effort_input,
            iterative_preference_input,
            settings_iteration_base_url_input,
            settings_iteration_model_id_input,
            settings_iteration_api_key_input,
            settings_iteration_protocol_input,
            settings_iteration_reasoning_effort_input,
        ],
        outputs=[
            iterative_custom_prompt_input,
            iterative_prompt_output,
            iterative_gallery_output,
            iterative_process_gallery_output,
            iterative_status_output,
        ],
    )
    iterative_stop_btn.click(
        fn=lambda: request_stop("iterative"),
        outputs=[iterative_status_output],
        cancels=[iterative_event],
        queue=False,
    )

    iterative_prompt_source_input.change(
        fn=update_iteration_source_ui,
        inputs=[iterative_prompt_source_input],
        outputs=[iterative_preference_input, iterative_custom_prompt_input],
        queue=False,
    )

    reverse_event = reverse_generate_btn.click(
        fn=reverse_prompt_from_image,
        inputs=[
            reverse_image_input,
            reverse_local_path_input,
            settings_iteration_base_url_input,
            settings_iteration_model_id_input,
            settings_iteration_api_key_input,
            settings_iteration_protocol_input,
            settings_iteration_reasoning_effort_input,
            settings_retry_count_input,
            settings_retry_delay_input,
        ],
        outputs=[reverse_prompt_output, reverse_status_output],
    )

    ui_state_outputs = [
        prompt_input,
        image_count_input,
        concurrency_input,
        image_model_provider_input,
        aspect_ratio_input,
        resolution_input,
        edit_prompt_input,
        edit_image_count_input,
        edit_concurrency_input,
        edit_image_model_provider_input,
        edit_aspect_ratio_input,
        edit_resolution_input,
        edit_input_fidelity_input,
        random_preference_input,
        random_prompt_output,
        random_image_count_input,
        random_concurrency_input,
        random_image_model_provider_input,
        random_aspect_ratio_input,
        random_resolution_input,
        creative_preference_input,
        creative_count_input,
        creative_random_enhance_input,
        creative_text_concurrency_input,
        creative_image_concurrency_input,
        creative_image_model_provider_input,
        creative_aspect_ratio_input,
        creative_resolution_input,
        iterative_preference_input,
        iterative_prompt_source_input,
        iterative_custom_prompt_input,
        iterative_prompt_output,
        iteration_count_input,
        iteration_batch_count_input,
        iteration_random_enhance_input,
        iteration_text_concurrency_input,
        iteration_image_concurrency_input,
        iterative_image_model_provider_input,
        iterative_aspect_ratio_input,
        iterative_resolution_input,
        settings_save_dir_input,
        settings_base_url_input,
        settings_model_id_input,
        settings_quality_input,
        settings_api_key_input,
        settings_seedream_base_url_input,
        settings_seedream_model_id_input,
        settings_seedream_interface_format_input,
        settings_seedream_response_format_input,
        settings_seedream_output_format_input,
        settings_seedream_watermark_input,
        settings_seedream_api_key_input,
        settings_random_base_url_input,
        settings_random_model_id_input,
        settings_random_protocol_input,
        settings_random_reasoning_effort_input,
        settings_random_api_key_input,
        settings_iteration_base_url_input,
        settings_iteration_model_id_input,
        settings_iteration_protocol_input,
        settings_iteration_reasoning_effort_input,
        settings_iteration_api_key_input,
        settings_retry_count_input,
        settings_retry_delay_input,
        settings_image_request_delay_input,
        settings_random_system_prompt_input,
        settings_random_user_prompt_input,
        settings_random_scene_summary_prompt_input,
        settings_iteration_optimizer_prompt_input,
        settings_reverse_prompt_input,
        settings_status_output,
    ]

    settings_save_btn.click(
        fn=save_settings,
        inputs=[
            settings_save_dir_input,
            settings_base_url_input,
            settings_model_id_input,
            settings_quality_input,
            settings_api_key_input,
            settings_seedream_base_url_input,
            settings_seedream_model_id_input,
            settings_seedream_api_key_input,
            settings_seedream_interface_format_input,
            settings_seedream_response_format_input,
            settings_seedream_output_format_input,
            settings_seedream_watermark_input,
            settings_random_base_url_input,
            settings_random_model_id_input,
            settings_random_api_key_input,
            settings_random_protocol_input,
            settings_random_reasoning_effort_input,
            settings_iteration_base_url_input,
            settings_iteration_model_id_input,
            settings_iteration_api_key_input,
            settings_iteration_protocol_input,
            settings_iteration_reasoning_effort_input,
            settings_retry_count_input,
            settings_retry_delay_input,
            settings_image_request_delay_input,
            settings_random_system_prompt_input,
            settings_random_user_prompt_input,
            settings_random_scene_summary_prompt_input,
            settings_iteration_optimizer_prompt_input,
            settings_reverse_prompt_input,
        ],
        outputs=[settings_status_output],
        queue=False,
    )

    settings_reload_btn.click(
        fn=load_ui_state,
        outputs=ui_state_outputs,
        queue=False,
    )
