import tensorflow as tf
import numpy as np
import datetime
import os

import Pix2Pix, utilities as util
from tensorflow.python.client import device_lib 

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="0"  # specify which GPU(s) to be used
print(device_lib.list_local_devices())

# Paths
base_path = "/scratch/cai/QSM-GAN/"
base_path = "/home/francesco/UQ/Job/QSM-GAN/"

last_path = "shapes_shape64_ex512_2019_05_01"
#last_path = "shapes_shape64_ex15_2019_04_17"
#last_path = "shapes_shape16_ex5_2019_03_26"
#last_path = "shapes_shape16_ex128_2019_04_17"

path = base_path + "data/" + last_path

currenttime = datetime.datetime.now()
checkpointName = "checkpoints_" + str(currenttime.year) + "-" + str(currenttime.month) + "-" + \
                    str(currenttime.day) + "_" + str(currenttime.hour) + str(currenttime.minute) + \
                    "_" + last_path

tf.reset_default_graph()
input_shape = (64, 64, 64, 1)
#input_shape = (16, 16, 16, 1)

train_data_filename = util.generate_file_list(file_path=path + "/train/", p_shape=input_shape)
eval_data_filename = util.generate_file_list(file_path=path + "/eval/", p_shape=input_shape)

train_input_fn = util.data_input_fn(train_data_filename, p_shape=input_shape, batch=1, nepochs=1, shuffle=True)
eval_input_fn = util.data_input_fn(eval_data_filename, p_shape=input_shape, batch=64, nepochs=1, shuffle=False)

# Unpack tensors
train_data = train_input_fn()
val_data = eval_input_fn()

# Construct a suitable iterator (and ops) for switching between the datasets
iterator = tf.data.Iterator.from_structure(train_data[2].output_types, train_data[2].output_shapes)
X_tensor, Y_tensor = iterator.get_next()

training_init_op = iterator.make_initializer(train_data[2])
validation_init_op = iterator.make_initializer(val_data[2])


# Create networks
with tf.variable_scope("generator"):
    Y_generated = Pix2Pix.getGenerator(X_tensor["x"])

with tf.name_scope("real_discriminator"):
    with tf.variable_scope("discriminator"):
        D_logits_real = Pix2Pix.getDiscriminator(X_tensor["x"], Y_tensor)
        
with tf.name_scope("fake_discriminator"):
    with tf.variable_scope("discriminator", reuse=True):
        D_logits_fake = Pix2Pix.getDiscriminator(X_tensor["x"], Y_generated)

accuracy = tf.reduce_mean(tf.abs(Y_generated - Y_tensor))

# Parameters
lr = 0.0002
batch_size = 1
EPS = 1e-12

# Losses
def discriminatorLoss(D_real, D_fake):
   
    discrim_loss = tf.reduce_mean(-(tf.log(D_real + EPS) + tf.log(1 - D_fake + EPS)))
    
    return discrim_loss

def generatorLoss(D_fake, G_output, target, weight=100.0):
    gen_loss_GAN = tf.reduce_mean(-tf.log(D_fake + EPS))
    gen_loss_L1 = tf.reduce_mean(tf.abs(target -  G_output))
    gen_loss = gen_loss_GAN * 1.0 + gen_loss_L1 * weight

    return gen_loss, gen_loss_GAN, gen_loss_L1

D_loss = discriminatorLoss(D_logits_real, D_logits_fake)
G_loss, G_gan, G_L1 = generatorLoss(D_logits_fake, Y_generated, Y_tensor, 90.0)

# Optimizers
with tf.name_scope('optimize'):
    discrim_tvars = [var for var in tf.trainable_variables() if var.name.startswith("discriminator")]
    discrim_optim = tf.train.AdamOptimizer(lr, 0.5)
    discrim_grads_and_vars = discrim_optim.compute_gradients(D_loss, var_list=discrim_tvars)
    discrim_train = discrim_optim.apply_gradients(discrim_grads_and_vars)

    with tf.control_dependencies([discrim_train]):
        gen_tvars = [var for var in tf.trainable_variables() if var.name.startswith("generator")]
        gen_optim = tf.train.AdamOptimizer(lr, 0.5)
        gen_grads_and_vars = gen_optim.compute_gradients(G_loss, var_list=gen_tvars)
        gen_train = gen_optim.apply_gradients(gen_grads_and_vars)

train_op = gen_train

# SUMMARIES - Create a list of summaries
D_loss_summary = tf.summary.scalar('D_loss', D_loss)
G_loss_summary = tf.summary.scalar('G_loss', G_gan)
L1_loss_summary = tf.summary.scalar('L1_loss', G_L1)

tf.summary.image('input', X_tensor["x"][:, :, :, int(input_shape[2]/2)], max_outputs=1)
tf.summary.image('output', Y_generated[:, :, :, int(input_shape[2]/2)], max_outputs=1)
tf.summary.image('ground_truth', Y_tensor[:, :, :, int(input_shape[2]/2)], max_outputs=1)

# MERGE SUMMARIES - Merge all summaries into a single op
merged_summary_op = tf.summary.merge_all()

# VISUALIZE => tensorboard --logdir=.
summaries_dir = base_path + checkpointName

with tf.Session() as sess:
    # Initialize variables
    saver = tf.train.Saver(max_to_keep=1)
    sess.run(tf.global_variables_initializer())
    
    # op to write logs to Tensorboard
    train_summary_writer = tf.summary.FileWriter(summaries_dir + '/train', graph=tf.get_default_graph())
    # val_summary_writer = tf.summary.FileWriter(summaries_dir + '/val')

    best_val_L1 = 100000
    global_step = 0
    for n_epoch in range(1000):
        '''
            Training data : Feedforward and backpropagate first D and then G
        '''
        sess.run(training_init_op)
        train_L1, train_G, train_D = [], [], []
        while True:
            try:
                if global_step % 250 == 0:
                    _, summary = sess.run([train_op, merged_summary_op])
                    train_summary_writer.add_summary(summary, global_step)
                else:
                    _ = sess.run(train_op)

                global_step += 1
            except tf.errors.OutOfRangeError:
                break


        '''
            Validation data : Check accuracy (L1) on validation
        
        sess.run(validation_init_op)
        total_val_L1 = []
        while True:
            try:
                if len(total_val_L1) == 0:
                    summary, val_L1 = sess.run([merged_summary_op, accuracy])
                    val_summary_writer.add_summary(summary, n_epoch) 
                else:
                    val_L1 = sess.run(accuracy)
                total_val_L1.append(val_L1)
            except tf.errors.OutOfRangeError:
                break

        # Calculate mean of accuracy over validation and save it
        val_L1 = np.mean(np.array(total_val_L1))
        acc_summary = sess.run(L1_loss_summary, feed_dict={avg_L1_loss: val_L1})
        val_summary_writer.add_summary(acc_summary, n_epoch)

        # If better model, save it
        if val_L1 < best_val_L1:
            best_val_L1 = val_L1
            save_path = saver.save(sess, summaries_dir + "/model.ckpt")'''