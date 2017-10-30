# Autoregressive RNN with logistic outputs.
# Author: Yingru Liu
# Institute: Stony Brook University

import tensorflow as tf
from .utility import hidden_net
from dl4stochastic.tools import get_batches_idx
import numpy as np

"""
Class: arRNN - the hyper abstraction of the auto-regressive RNN.
"""
class _arRNN(object):

    """
    __init__:the initialization function.
    input: Config - configuration class in ./utility.
    output: None.
    """
    def __init__(
            self,
            Config,
    ):
        # Check the dimension configuration.
        if Config.dimLayer == []:
            raise(ValueError('The structure is empty!'))
        # Check the autoregressive structure(i.e. dim of output is equal to dim of input).
        if Config.dimLayer[-1] != Config.dimLayer[0]:
            Config.dimLayer[-1] = Config.dimLayer[0]

        # <tensor graph> define a default graph.
        self._graph = tf.Graph()
        # <scalar>
        self._batch_size = Config.batch_size

        with self._graph.as_default():
            # <tensor placeholder> input.
            self.x = tf.placeholder(dtype='float32', shape=[None, None, Config.dimLayer[0]])
            # <tensor placeholder> learning rate.
            self.lr = tf.placeholder(dtype='float32', shape=(), name='learningRate')

            # <scalar> number of hidden layers.
            self._numLayer = len(Config.dimLayer) - 2
            # <scalar list> dimensions of each layer[input, hiddens, output].
            self._dimLayer = Config.dimLayer
            # <string/None> path to save the model.
            self._savePath = Config.savePath
            # <string/None> path to save the events.
            self._eventPath = Config.eventPath
            # <string/None> path to load the events.
            self._loadPath = Config.loadPath
            # <list> collection of trainable parameters.
            self._params = []
            # <pass> will be define in the children classes.
            self._train_step = None
            # <pass> will be define in the children classes.
            self._loss = None
            # <pass> will be define in the children classes.
            self._outputs = None

            # Build the Inference Network
            # self._cell: the mutil - layer hidden cells.
            # self._hiddenOutput - the output with shape [batch_size, max_time, cell.output_size].
            # self._initializer - Initializer.
            self._cell, self._hiddenOutput, self._initializer = hidden_net(
                self.x, self._graph, Config)

            # <Tensorflow Optimizer>.
            if Config.Opt == 'Adadelta':
                self._optimizer = tf.train.AdadeltaOptimizer(learning_rate=self.lr)
            elif Config.Opt == 'Adam':
                self._optimizer = tf.train.AdamOptimizer(learning_rate=self.lr)
            elif Config.Opt == 'Momentum':
                self._optimizer = tf.train.MomentumOptimizer(self.lr, 0.5)
            elif Config.Opt == 'SGD':
                self._optimizer = tf.train.GradientDescentOptimizer(learning_rate=self.lr)
            else:
                raise(ValueError("Config.Opt should be either 'Adadelta', 'Adam', 'Momentum' or 'SGD'!"))
            # <Tensorflow Session>.
            self._sess = tf.Session(graph=self._graph)
        return

    """
    _runSession: initialize the graph or restore from the load path.
    input: None.
    output: None.
    """
    def _runSession(self):
        if self._loadPath is None:
            self._sess.run(tf.global_variables_initializer())
        else:
            saver = tf.train.Saver()
            saver.restore(self._sess, self._loadPath)
        return

    """
    train_function: compute the loss and update the tensor variables.
    input: input - numerical input.
           lrate - <scalar> learning rate.
    output: the loss value.
    """
    def train_function(self, input, lrate):
        with self._graph.as_default():
            zero_padd = np.zeros(shape=(input.shape[0], 1, input.shape[2]), dtype='float32')
            con_input = np.concatenate((zero_padd, input), axis=1)
            _, loss_value = self._sess.run([self._train_step, self._loss],
                                           feed_dict={self.x: con_input, self.lr: lrate})
        return loss_value * input.shape[-1]

    """
    val_function: compute the loss with given input.
    input: input - numerical input.
    output: the loss value.
    """
    def val_function(self, input):
        with self._graph.as_default():
            zero_padd = np.zeros(shape=(input.shape[0], 1, input.shape[2]), dtype='float32')
            con_input = np.concatenate((zero_padd, input), axis=1)
            loss_value = self._sess.run(self._loss, feed_dict={self.x: con_input})
        return loss_value * input.shape[-1]

    """
    output_function: compute the output with given input.
    input: input - numerical input.
    output: the output values of the network.
    """
    def output_function(self, input):
        with self._graph.as_default():
            zero_padd = np.zeros(shape=(input.shape[0], 1, input.shape[2]), dtype='float32')
            con_input = np.concatenate((zero_padd, input), axis=1)
            output = self._sess.run(self._outputs, feed_dict={self.x: con_input})
        return output[:, 0:-1, :]

    """
    gen_function: generate samples.
    input: numSteps - the length of the sample sequence.
    output: should be the sample.
    """
    def gen_function(self, numSteps):
        return

    """
    saveModel:save the trained model into disk.
    input: savePath - another saving path, if not provide, use the default path.
    output: None
    """
    def saveModel(self, savePath=None):
        with self._graph.as_default():
            # Create a saver.
            saver = tf.train.Saver()
            if savePath is None:
                saver.save(self._sess, self._savePath)
            else:
                saver.save(self._sess, savePath)
        return

    """
    loadModel:load the model from disk.
    input: loadPath - another loading path, if not provide, use the default path.
    output: None
    """
    def loadModel(self, loadPath=None):
        with self._graph.as_default():
            # Create a saver.
            saver = tf.train.Saver()
            if loadPath is None:
                if self._loadPath is not None:
                    saver.restore(self._sess, self._loadPath)
                else:
                    raise (ValueError("No loadPath is given!"))
            else:
                saver.restore(self._sess, loadPath)
        return


    """
    saveEvent:save the event to visualize the last model once.
              (To visualize other aspects, other codes should be used.)
    input: None
    output: None
    """
    def saveEvent(self):
        with self._graph.as_default():
            # compute the statistics of the parameters.
            for param in self._params:
                scopeName =param.name.split('/')[-1]
                with tf.variable_scope(scopeName[0:-2]):
                    mean = tf.reduce_mean(param)
                    tf.summary.scalar('mean',  mean)
                    stddev = tf.sqrt(tf.reduce_mean(tf.square(param - mean)))
                    tf.summary.scalar('stddev', stddev)
                    tf.summary.scalar('max', tf.reduce_max(param))
                    tf.summary.scalar('min', tf.reduce_min(param))
                    tf.summary.histogram('histogram', param)
            # visualize the trainable parameters of the model.
            summary = tf.summary.merge_all()
            summary_str = self._sess.run(summary)
            # Define a event writer and write the events into disk.
            Writer = tf.summary.FileWriter(self._eventPath, self._sess.graph)
            Writer.add_summary(summary_str)
            Writer.flush()
            Writer.close()
        return

    """
    full_train: define to fully train a model given the dataset.
    input: 
    output: 
    """
    def full_train(self, dataset, max_epoch, earlyStop, learning_rate, saveto):
        # slit the dataset.
        trainData = dataset['train']
        validData = dataset['valid']
        testData = dataset['test']
        validBatch = get_batches_idx(len(validData), self._batch_size, False)
        testBatch = get_batches_idx(len(testData), self._batch_size, False)

        historyLoss = []                   # <list> record the training process.
        worseCase = 0                       # indicate the worse cases for early stopping
        bestEpoch = -1

        for epoch in range(max_epoch):

            # update the model w.r.t the training set and record the average loss.
            trainLoss = []
            trainBatch = get_batches_idx(len(trainData), self._batch_size, True)
            for Idx in trainBatch:
                x = trainData[Idx]
                trainLoss.append(x.shape[0]*self.train_function(x, learning_rate))
            trainLoss_avg = np.asarray(trainLoss).sum()/len(trainData)

            # evaluate the model w.r.t the valid set and record the average loss.
            validLoss = []
            for Idx in validBatch:
                x = validData[Idx]
                validLoss.append(x.shape[0]*self.train_function(x, learning_rate))
            validLoss_avg = np.asarray(validLoss).sum()/len(validData)
            print("In epoch \x1b[1;32m%4d\x1b[0m: the training loss is "
                  "\x1b[1;32m%10.4f\x1b[0m; the valid loss is \x1b[1;32m%10.4f\x1b[0m." % (epoch, trainLoss_avg, validLoss_avg))

            # check the early stopping conditions.
            if len(historyLoss)==0 or validLoss_avg < np.min(np.asarray(historyLoss)[:, 1]):
                worseCase = 0
                bestEpoch = epoch
                self.saveModel()
            else:
                worseCase += 1
            historyLoss.append([trainLoss_avg, validLoss_avg])

            if worseCase >= earlyStop:
                break

        # evaluate the best model w.r.t the test set and record the average loss.
        self.loadModel(self._savePath)

        trainLoss = []
        trainBatch = get_batches_idx(len(trainData), self._batch_size, True)
        for Idx in trainBatch:
            x = trainData[Idx]
            trainLoss.append(x.shape[0] * self.train_function(x, learning_rate))
        trainLoss_avg = np.asarray(trainLoss).sum() / len(trainData)

        validLoss = []
        for Idx in validBatch:
            x = validData[Idx]
            validLoss.append(x.shape[0] * self.train_function(x, learning_rate))
        validLoss_avg = np.asarray(validLoss).sum() / len(validData)

        testLoss = []
        for Idx in testBatch:
            x = testData[Idx]
            testLoss.append(x.shape[0] * self.train_function(x, learning_rate))
        testLoss_avg = np.asarray(testLoss).sum() / len(testData)

        # evaluate the model w.r.t the valid set and record the average loss.
        print("BEST MODEL from epoch \x1b[1;91m%4d\x1b[0m with training loss"
              " \x1b[1;91m%10.4f\x1b[0m and valid loss \x1b[1;91m%10.4f\x1b[0m."
              % (bestEpoch, trainLoss_avg, validLoss_avg))
        print('The testing loss is \x1b[1;91m%10.4f\x1b[0m.' % testLoss_avg)

        if saveto is not None:
            np.savez(saveto, historyLoss=np.asarray(historyLoss), testLoss=testLoss_avg)
        return



"""
Class: binRNN - the hyper abstraction of the auto-regressive RNN.
"""
class binRNN(_arRNN, object):
    """
        __init__:the initialization function.
        input: Config - configuration class in ./utility.
        output: None.
    """
    def __init__(
            self,
            Config,
    ):
        _arRNN.__init__(self, Config)

        # add the output layer at the top of hidden output.
        with self._graph.as_default():
            with tf.variable_scope('logit', initializer=self._initializer):
                # define the output layer.
                W = tf.get_variable('weight', shape=(Config.dimLayer[-2], Config.dimLayer[-1]))
                b = tf.get_variable('bias', shape=Config.dimLayer[-1], initializer=tf.zeros_initializer)
                logits = tf.tensordot(self._hiddenOutput, W, [[-1], [0]]) + b
                self._outputs = tf.nn.sigmoid(logits)
                # define the loss function.
                self._loss = tf.losses.sigmoid_cross_entropy(self.x[:, 1:, :], logits[:, 0:-1, :])
                self._params = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
                self._train_step = self._optimizer.minimize(tf.cast(tf.shape(self.x), tf.float32)[-1]*self._loss)
                self._runSession()

    """
    gen_function: reconstruction of the gen_function in class: arRNN.
    """
    def gen_function(self, numSteps):
        with self._graph.as_default():
            state = self._cell.zero_state(1, dtype=tf.float32)
            x_ = tf.zeros((1, self._dimLayer[0]), dtype='float32')
            samples = []
            with tf.variable_scope('logit', reuse=True):  # reuse the output layer.
                W = tf.get_variable('weight')
                b = tf.get_variable('bias')
                for i in range(numSteps):
                    hidde_, state = self._cell(x_, state)
                    probs = tf.nn.sigmoid(tf.nn.xw_plus_b(hidde_, W, b))
                    x_ = tf.distributions.Bernoulli(probs=probs, dtype=tf.float32).sample()
                    samples.append(x_)
            samples = tf.concat(samples, 0)
        return self._sess.run(samples)


"""
--------------------------------------------------------------------------------------------
"""
class gaussRNN(_arRNN):
    pass

"""
--------------------------------------------------------------------------------------------
"""
class gmmRNN(_arRNN):
    pass