import math

from comfy_api.latest import io
from comfy_extras.nodes_resolution import ASPECT_RATIOS, AspectRatio


class ClosestAspectRatio(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="CD_ClosestAspectRatio",
            display_name="获取图片比例和像素数",
            category="CDToolSets/图像",
            inputs=[
                io.Image.Input("image", optional=True, tooltip="连接图片时优先使用图片宽高。"),
                io.Int.Input("width", default=1024, min=1, max=0x7fffffff, optional=True),
                io.Int.Input("height", default=1024, min=1, max=0x7fffffff, optional=True),
            ],
            outputs=[
                io.Combo.Output("aspect_ratio", options=[ratio.value for ratio in AspectRatio]),
                io.Float.Output("megapixels", tooltip="按官方分辨率选择器计算：width × height ÷ (1024 × 1024)。"),
            ],
        )

    @classmethod
    def execute(cls, image=None, width=1024, height=1024):
        if image is not None:
            height, width = image.shape[1:3]
        if width <= 0 or height <= 0:
            raise ValueError("width 和 height 必须大于 0。")
        target = math.log(width / height)
        ratio = min(ASPECT_RATIOS, key=lambda ratio: abs(
            target - math.log(ASPECT_RATIOS[ratio][0] / ASPECT_RATIOS[ratio][1])
        ))
        return io.NodeOutput(ratio.value, width * height / (1024 * 1024))
