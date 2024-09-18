from pathlib import Path
from hair_swap import HairFast, get_parser

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import torchvision.transforms as T
import torch
from torchvision.utils import save_image

model_args = get_parser()
hair_fast = HairFast(model_args.parse_args([]))

input_dir = Path("input")
face_path = input_dir / 'tuan.jpg'
shape_path = input_dir / 'drake.jpg'
color_path = input_dir / '5.jpg'

final_image, face_align, shape_align, color_align = hair_fast.swap(face_path,shape_path,color_path, align=True)

# save final_image to output directory
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)
output_image_path = output_dir / 'final_image_result.png'
save_image(final_image, output_image_path)
