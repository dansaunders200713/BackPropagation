from __future__ import print_function
import theano, theano.tensor as T, numpy, os, gzip, cPickle as pickle, timeit, sys
from matplotlib import pyplot as plt

__docformat__ = 'restructedtext en'


class LogisticRegression(object):
	"""
    Multi-class Logistic Regression Class
    """

	def __init__(self, input, num_inputs, num_outputs):
		""" Initialize the parameters of the logistic regression

        :param input: symbolic variable that describes the input of the network

        :param num_inputs: number of input units / the dimension of the input vector space

        :param num_outputs: number of output units / the dimension of the output vector space

        """

		# initialize with 0 the weights "weights" as a matrix of shape (num_inputs, num_outputs)
		self.weights = theano.shared(value=numpy.zeros((num_inputs, num_outputs), dtype=theano.config.floatX),
		                             name='weights', borrow=True)
		# initialize the biases "biases" as a vector of num_outputs 0s
		self.biases = theano.shared(value=numpy.zeros((num_outputs,), dtype=theano.config.floatX), name='biases',
		                            borrow=True)

		# symbolic expression for computing the matrix of class-membership
		# probabilities:
		# "weights" is a matrix where column-k represent the separation hyperplane for
		# class-k
		# "x" is a matrix where row-j represents input training sample-j
		# "biases" is a vector where element-k represent the free parameter of
		# hyperplane-k
		self.prob_y_given_x = T.nnet.softmax(T.dot(input, self.weights) + self.biases)

		# symbolic description of how to compute prediction as class whose
		# probability is maximal
		self.y_prediction = T.argmax(self.prob_y_given_x, axis=1)
		# end-snippet-1

		# parameters of the model
		self.params = [self.weights, self.biases]

		# keep track of model input
		self.input = input

	def negative_log_likelihood(self, y):
		"""Return the mean of the negative log-likelihood of the prediction
        of this model under a given target distribution.

        :param y: corresponds to a vector that gives for each example the
                  correct label

        Note: we use the mean instead of the sum so that
              the learning rate is less dependent on the batch size
        """

		# y.shape[0] is (symbolically) the number of rows in y, i.e.,
		# number of examples (call it n) in the minibatch
		# T.arange(y.shape[0]) is a symbolic vector which will contain
		# [0,1,2,...,n-1] T.log(self.p_y_given_x) is a matrix of
		# Log-Probabilities (call it LP) with one row per example and
		# one column per class LP[T.arange(y.shape[0]),y] is a vector
		# v containing [LP[0,y[0]], LP[1,y[1]], LP[2,y[2]], ...,
		# LP[n-1,y[n-1]]] and T.mean(LP[T.arange(y.shape[0]),y]) is
		# the mean (across minibatch examples) of the elements in v,
		# i.e., the mean log-likelihood across the minibatch.
		return -T.mean(T.log(self.prob_y_given_x)[T.arange(y.shape[0]), y])

	def errors(self, y):
		"""Return a float representing the number of errors in the minibatch
        over the total number of examples of the minibatch ; zero one
        loss over the size of the minibatch

        :param y: corresponds to a vector that gives for each example the
                  correct label
        """

		# check if y has same dimension of y_prediction
		if y.ndim != self.y_prediction.ndim:
			raise TypeError('y should have the same shape as self.y_pred',
			                ('y', y.type, 'y_pred', self.y_prediction.type))
		# check if y is of the correct datatype
		if y.dtype.startswith('int'):
			# the T.neq operator returns a vector of 0s and 1s, where 1
			# represents a mistake in prediction
			return T.mean(T.neq(self.y_prediction, y))
		else:
			raise NotImplementedError()


class HiddenLayer(object):
	def __init__(self, random_number_generator, input, num_inputs, num_outputs, weights=None, bias=None,
	             activation=T.tanh):
		""" initializing parameters for the hidden layer of the perceptron

        :param random_number_generator: a random number generator used to initialize weights
        :param input: a symbolic tensor, of the form (num_examples, num_inputs)
        :param num_inputs: the dimensionality of the input vector
        :param num_outputs: the number of hidden units in this layer
        :param weights: a matrix representing the weights of the hidden layer
        :param bias: a vector representing the bias input to the hidden layer
        :param activation: the nonlinear activation function of the hidden layer neurons
        """

		self.input = input

		# the "weights" vector is initialized with random weights sampled from the interval
		# [ sqrt(-6./(n_in+n_hidden)) , sqrt(6./(n_in+n_hidden)) ], chosen for the tanh function.

		if weights is None:
			weight_values = numpy.asarray(
					random_number_generator.uniform(low=-numpy.sqrt(6. / (num_inputs + num_outputs)),
					                                high=numpy.sqrt(6. / (num_inputs + num_outputs)),
					                                size=(num_inputs, num_outputs)), dtype=theano.config.floatX)

			weights = theano.shared(value=weight_values, name='weights', borrow=True)

		if bias is None:
			bias_values = numpy.zeros((num_outputs,), dtype=theano.config.floatX)
			bias = theano.shared(value=bias_values, name='bias', borrow=True)

		self.weights = weights
		self.bias = bias

		linear_output = T.dot(input, self.weights) + self.bias
		self.output = (linear_output if activation is None
		               else activation(linear_output))

		self.params = [self.weights, self.bias]


class MLP(object):
	"""
    Multi-Layer Perceptron Class
    """

	def __init__(self, random_number_generator, input, num_inputs, num_hidden, num_outputs):
		""" initializing parameters for the multilayer perceptron

        :param random_number_generator: a random number generator used to initialize network weights
        :param input: symbolic variable that describes the input of the architecture (one minibatch)
        :param num_inputs: the number of input units in the network / the dimension of the input vector space
        :param num_hidden: the number of hidden units in the network
        :param num_outputs: the number of output units in the network / the dimension of the output vector space

        """

		# We are implementing a perceptron with one hidden layer, and so the entire netowrk will consist
		# of a HiddenLayer with the tanh activation function, connected to a LogisticRegression layer, where the
		# activation function can be replaced with any other nonlinear function.

		self.hiddenLayer = HiddenLayer(random_number_generator=random_number_generator, input=input,
		                               num_inputs=num_inputs, num_outputs=num_hidden, activation=T.tanh)

		# The LogisticRegression layer, or the output layer, takes the units of the hidden layer as input.
		self.logRegressionLayer = LogisticRegression(input=self.hiddenLayer.output, num_inputs=num_hidden,
		                                             num_outputs=num_outputs)

		# L1 norm: one regularization option is to enforce a small L1 norm.
		self.L1 = (abs(self.hiddenLayer.weights).sum() + abs(self.logRegressionLayer.weights).sum())

		# square of L2 norm: another regularization option is to enforce a small square of the L2 norm
		self.L2_sqr = ((self.hiddenLayer.weights ** 2).sum() + (self.logRegressionLayer.weights ** 2).sum())

		# the negative log likelihood of the multi-layer perceptron is given by the negative log likelihood
		# of the output of the perceptron, which we compute in the logistic regression layer
		self.negative_log_likelihood = (self.logRegressionLayer.negative_log_likelihood)
		# the same holds for the function computing the nubmer of errors
		self.errors = self.logRegressionLayer.errors

		# the parameters of the perceptron are the parameters of the layers it is composed of
		self.params = self.hiddenLayer.params + self.logRegressionLayer.params

		# keep track of model input
		self.input = input


def load_data(dataset, num_examples):
	"""

    This function loads the dataset we use for stochastic gradient descent.

    :param dataset: the path to the MNIST dataset

    :return: the 3-tuple (training, validation, testing) which represents the MNIST dataset
    """

	# Download the MNIST dataset if it is not present
	data_dir, data_file = os.path.split(dataset)
	if data_dir == "" and not os.path.isfile(dataset):
		# Check if dataset is in the data directory.
		new_path = os.path.join(os.path.split(__file__)[0], "..", "data", dataset)
		if os.path.isfile(new_path) or data_file == 'mnist.pkl.gz':
			dataset = new_path

	if (not os.path.isfile(dataset)) and data_file == 'mnist.pkl.gz':
		from six.moves import urllib
		origin = ('http://www.iro.umontreal.ca/~lisa/deep/data/mnist/mnist.pkl.gz')
		print('Downloading data from %s' % origin)
		urllib.request.urlretrieve(origin, dataset)

	print('... loading data')

	# Load the dataset
	with gzip.open(dataset, 'rb') as f:
		try:
			train_set, valid_set, test_set = pickle.load(f, encoding='latin1')
		except:
			train_set, valid_set, test_set = pickle.load(f)

	def shared_dataset(data_xy, borrow=True, num_ex=10000):
		data_x, data_y = data_xy
		data_x = data_x[0:num_ex]
		data_y = data_y[0:num_ex]

		shared_x = theano.shared(numpy.asarray(data_x, dtype=theano.config.floatX), borrow=borrow)
		shared_y = theano.shared(numpy.asarray(data_y, dtype=theano.config.floatX), borrow=borrow)

		return shared_x, T.cast(shared_y, 'int32')

	test_set_x, test_set_y = shared_dataset(test_set)
	valid_set_x, valid_set_y = shared_dataset(valid_set)
	train_set_x, train_set_y = shared_dataset(train_set, num_ex=num_examples)

	sets = [(train_set_x, train_set_y), (valid_set_x, valid_set_y), (test_set_x, test_set_y)]
	return sets


def test_mlp(learning_rate=0.01, L1_reg=0.00, L2_reg=0.0001, num_epochs=1000, dataset='mnist.pkl.gz', batch_size=20, num_hidden=500, num_examples = 50000):
	"""
	We demonstrate stochastic gradient descent on the MNIST data set.

	:param learning_rate: the parameter which controls the weight-tuning during the run of the gradient descent algorithm
	:param L1_reg: L1-norm's weight when added to the cost function
	:param L2_reg: L2-norm's weight when added to the cost function
	:param num_epochs: the number of epochs which we use to train the multilayer perceptron
	:param dataset: the path to the MNIST dataset
	:param batch_size: the number of examples which we pass to the GPU for training
	:param num_hidden: the number of hidden neurons in the perceptron

	"""

	datasets = load_data(dataset, num_examples)

	train_set_x, train_set_y = datasets[0]
	valid_set_x, valid_set_y = datasets[1]
	test_set_x, test_set_y = datasets[2]

	# compute number of minibatches for training, validation and testing
	num_train_batches = train_set_x.get_value(borrow=True).shape[0] // batch_size
	num_valid_batches = valid_set_x.get_value(borrow=True).shape[0] // batch_size
	num_test_batches = test_set_x.get_value(borrow=True).shape[0] // batch_size

	# Building the multilayer perceptron
	print('... building the model')

	# allocate symbolic variables for the data
	index = T.lscalar()  # index to a [mini]batch
	x = T.matrix('x')  # the data is presented as rasterized images
	y = T.ivector('y')  # the labels are presented as 1D vector of [int] labels

	random_number_generator = numpy.random.RandomState(1234)

	# construct the MLP class
	classifier = MLP(random_number_generator=random_number_generator, input=x, num_inputs=28 * 28,
	                 num_hidden=num_hidden, num_outputs=10)

	# the cost we minimize during training is the negative log likelihood of
	# the model plus the regularization terms (L1 and L2); cost is expressed
	# here symbolically
	cost = (classifier.negative_log_likelihood(y) + L1_reg * classifier.L1 + L2_reg * classifier.L2_sqr)

	# a Theano function that computes the mistakes made by the model on a minibatch
	test_model = theano.function(inputs=[index], outputs=classifier.errors(y),
	                             givens={x: test_set_x[index * batch_size:(index + 1) * batch_size],
	                                     y: test_set_y[index * batch_size:(index + 1) * batch_size]})

	validate_model = theano.function(inputs=[index], outputs=classifier.errors(y),
	                                 givens={x: valid_set_x[index * batch_size:(index + 1) * batch_size],
	                                         y: valid_set_y[index * batch_size:(index + 1) * batch_size]})

	# we compute the gradient of the cost function with respect to theta. The resulting gradients with be
	# stored in the list "gradient_params"

	gradient_params = [T.grad(cost, param) for param in classifier.params]

	# this specifies how to update the parameter of the multilayer perceptron as a list of
	# (variable, update expression) pairs

	# given two lists of the same length, A = [a1, a2, a3, a4] and
	# B = [b1, b2, b3, b4], zip generates a list C of same size, where each
	# element is a pair formed from the two lists :
	#    C = [(a1, b1), (a2, b2), (a3, b3), (a4, b4)]

	updates = [(param, param - learning_rate * gradient_param) for param, gradient_param in
	           zip(classifier.params, gradient_params)]

	#
	# compiling a Theano function `train_model` that returns the cost, but
	# in the same time updates the parameter of the model based on the rules
	# defined in `updates`
	train_model = theano.function(inputs=[index], outputs=cost, updates=updates,
	                              givens={x: train_set_x[index * batch_size: (index + 1) * batch_size],
	                                      y: train_set_y[index * batch_size: (index + 1) * batch_size]})

	# Training the model

	print('... training')

	# early-stopping parameters
	patience = 100  # look at this many examples regardless of performance
	patience_increase = 2  # wait this much longer when a new best is found
	improvement_threshold = 0.995  # a relative improvement of this magnitude is considered significant
	validation_frequency = min(num_train_batches, patience // 2)  # go through this many minibatches before checking the
	# network on the validation set. In this case, we check every epoch.
	best_validation_loss = numpy.inf
	best_iteration = 0
	test_score = 0.
	start_time = timeit.default_timer()

	epoch = 0
	done_looping = False

	while (epoch < num_epochs) and (not done_looping):
		epoch = epoch + 1
		for minibatch_index in range(num_train_batches):

			minibatch_average_cost = train_model(minibatch_index)
			# iteration number
			iteration = (epoch - 1) * num_train_batches + minibatch_index

			if (iteration + 1) % validation_frequency == 0:
				# here computae the zero-one loss function on validation set
				validation_losses = [validate_model(i) for i in range(num_valid_batches)]
				this_validation_loss = numpy.mean(validation_losses)

				print('epoch %i, minibatch %i/%i, validation error %f %%' % (
					epoch, minibatch_index + 1, num_train_batches, this_validation_loss * 100.))

				# if this validation score is the best yet
				if this_validation_loss < best_validation_loss:
					# improve the patience parameter if loss improvement is good enough
					if (this_validation_loss < best_validation_loss * improvement_threshold):
						patience = max(patience, iteration * patience_increase)
					best_validation_loss = this_validation_loss
					best_iteration = iteration

					# test this model on the test set
					test_losses = [test_model(i) for i in range(num_test_batches)]
					test_score = numpy.mean(test_losses)

					print(('    epoch %i, minibatch %i/%i, test error of '
					       ' best model %f %%') % (epoch, minibatch_index + 1, num_train_batches, test_score * 100.))
			if patience <= iteration:
				done_looping = True
				break
	end_time = timeit.default_timer()
	print(('Optimization complete. Best validation score of %f %% '
			'obtained at iteration %i, with test performance %f %%') % (
			best_validation_loss * 100., best_iteration + 1, test_score * 100.))

	return best_validation_loss, test_score

if __name__ == '__main__':
	trial = input('Enter (1) for hidden neuron plot, (2) for batch size plot: ')

	if trial == 1:
		neurons = [2, 5, 10, 50, 100, 200, 400]
		valid_losses = []
		test_losses = []

		for neuron in neurons:
			valid_loss, test_loss = test_mlp(num_hidden = neuron, num_epochs = 10)
			valid_losses.append(valid_loss)
			test_losses.append(test_loss)

		plt.semilogx(neurons, valid_losses, 'rs', label = 'Neurons vs. Validation Loss', linestyle='solid')
		plt.semilogx(neurons, test_losses, 'bs', label = 'Nuerons vs. Test Loss', linestyle='solid')
		plt.title('Hidden Neurons vs. Validation / Test Loss for 10 Epochs')
		plt.xlabel('Neurons')
		plt.ylabel('Loss')
		plt.legend(loc='upper right', shadow=True, fontsize='small')
		plt.show()

	if trial == 2:
		examples = [100, 500, 1000, 10000, 25000, 50000]
		valid_losses = []
		test_losses = []

		for example in examples:
			valid_loss, test_loss = test_mlp(num_epochs = 10, num_hidden = 100, num_examples = example)
			valid_losses.append(valid_loss)
			test_losses.append(test_loss)

		plt.semilogx(examples, valid_losses, 'rs', label = 'Batches vs. Validation Loss', linestyle='solid')
		plt.semilogx(examples, test_losses, 'bs', label = 'Batches vs. Test Loss', linestyle='solid')
		plt.title('Number of Examples vs. Validation / Test Loss for 10 Epochs')
		plt.xlabel('Example Set Size')
		plt.ylabel('Loss')
		plt.legend(loc='upper right', shadow=True, fontsize='small')
		plt.show()
