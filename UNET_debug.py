import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
import tensorflow as tf
import numpy as np
import datetime
import src.LinkNet as network, src.utilities as util

tf.logging.set_verbosity(tf.logging.ERROR)
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="0"

# Paths
base_path = "/scratch/cai/deepQSMGAN/"
data_path = "data/shapes_shape64_ex100_2019_08_30"

#base_path = "/home/francesco/UQ/deepQSMGAN/"
#data_path = "data/shapes_shape64_ex100_2019_08_20"

now = datetime.datetime.now()
checkpointName = "ckp_" + str(now.year) + str(now.month) + str(now.day) + "_" + str(now.hour) + str(now.minute) + "_" + data_path.split("/")[-1]

input_shape = (64, 64, 64, 1)
train_data_filename = util.generate_file_list(file_path=base_path + data_path + "/train/", p_shape=input_shape)
train_input_fn = util.data_input_fn(train_data_filename, p_shape=input_shape, batch=1, nepochs=3000, shuffle=True)
X_tensor, Y_tensor, _ = train_input_fn()


Y_generated = network.getGenerator(X_tensor)    
loss = tf.reduce_mean(tf.abs(Y_tensor - Y_generated)) 
optimizer = tf.train.AdamOptimizer(0.0001, 0.5).minimize(loss, var_list=tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='generator'))

train_summaries = [tf.summary.scalar('loss', loss)]
train_merged_summaries = tf.summary.merge(train_summaries)

for i in tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='generator'):
    print(i)
# VISUALIZE => tensorboard --logdir=.
summaries_dir = base_path + checkpointName

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
with tf.Session(config=config) as sess:
    sess.run(tf.global_variables_initializer())
    train_summary_writer = tf.summary.FileWriter(summaries_dir + '/train', graph=tf.get_default_graph())
    global_step = 0
    while True:
        try:
            _, summary = sess.run([optimizer, train_merged_summaries])
            train_summary_writer.add_summary(summary, global_step)
            global_step += 1 
        except tf.errors.OutOfRangeError:
            break
