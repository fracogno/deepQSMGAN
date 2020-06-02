#!/bin/bash
#SBATCH -N 1
#SBATCH --job-name=QSMResGAN
#SBATCH -n 1
#SBATCH -c 6
#SBATCH --mem=50000
#SBATCH -o out_wiener.txt
#SBATCH -e error_wiener.txt
#SBATCH --partition=gpu
#SBATCH --gres=gpu:tesla-smx2:1

module load anaconda/3.6
source activate /opt/ohpc/pub/apps/tensorflow_2.0.0

srun -n 1 python3 sample/train.py
# srun -n 1 python3 sample/predict.py