"""Local AI-only CLI; intentionally independent of any API/frontend."""
import argparse, json
from pathlib import Path
from circl_e_ai.release.loader import load_release
from circl_e_ai.pipeline.infer import infer_image
from circl_e_ai.utils import to_builtin


def main():
    p=argparse.ArgumentParser(description='Run frozen CIRCL-E AI inference on one image.')
    p.add_argument('image')
    p.add_argument('--release',required=True)
    p.add_argument('--device',default=None,help='cuda, cpu, etc.; default auto')
    p.add_argument('--allow-unverified-release',action='store_true')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    release=load_release(args.release,require_verified=not args.allow_unverified_release,load_backbones=True,device=args.device)
    result=to_builtin(infer_image(args.image,release))
    text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)
    if args.output: args.output.write_text(text,encoding='utf-8')
    else: print(text)
