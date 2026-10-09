"""Reproducible training command; does not require a running web server."""
import argparse
import json
from pathlib import Path
from .ai import train


def main():
    parser=argparse.ArgumentParser(description='Train an Escape Plan Q-learning opponent')
    parser.add_argument('--episodes',type=int,default=500)
    parser.add_argument('--size',type=int,choices=[5,7,9],default=5)
    parser.add_argument('--modifiers',default='',help='Comma-separated shift,key,fake,shrink,timer')
    parser.add_argument('--powers',choices=['off','limited','pickups','both'],default='off')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',default='data')
    args=parser.parse_args()
    if not 20 <= args.episodes <= 100000:
        parser.error('episodes must be between 20 and 100000')
    Path(args.output).mkdir(parents=True,exist_ok=True)
    result=train(args.output,args.episodes,{'mode':'stage','size':args.size,'bot':'qlearning','modifiers':[m for m in args.modifiers.split(',') if m],'powers':args.powers},args.seed)
    print(json.dumps({k:v for k,v in result.items() if k!='metrics'},indent=2))


if __name__=='__main__':
    main()
