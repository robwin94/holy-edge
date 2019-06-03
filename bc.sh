#!/bin/bash
#SBATCH --share
#SBATCH -J trainNN                          # job name
#SBATCH -N 1                                  # number of nodes
#SBATCH -n 1                                   # number of MPI processes, here 1 per node
#SBATCH --partition=gpu        # choose nodes from partition
#SBATCH -o %j.out                            # stdout file name (%j: job ID)
#SBATCH -e %j.err                             # stderr file name (%j: job ID)
#SBATCH -t 72:00:00                        # max run time (hh:mm:ss), max 72h!
#SBATCH --mail-type=end
#SBATCH --mail-user=rw123603@uni-greifswald.de

## optional environment variables
echo "On which nodes it executes:"
echo $SLURM_JOB_NODELIST
echo " "
echo "jobname: $SLURM_JOB_NAME"

source /home/rw123603/.bashrc
## pip install -r requirements.txt --user
export CUDA_VISIBLE_DEVICES=1
export OMP_NUM_THREADS=1
module load cuda/9.1 tensorflow/1.8.0

CUDA_VISIBLE_DEVICES=1 python2 run-hed.py --train --config-file hed/configs/hed_auf_brain.yaml

