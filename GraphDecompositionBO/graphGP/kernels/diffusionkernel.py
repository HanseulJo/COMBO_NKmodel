import math

import torch
from GraphDecompositionBO.graphGP.kernels.graphkernel import GraphKernel


class DiffusionKernel(GraphKernel):
	"""
	Usually Graph Kernel means a kernel between graphs, here this kernel is a kernel between vertices on a graph
	Edge scales are not included in the module, instead edge weights of each subgraphs is used to calculate frequencies (fourier_freq)
	"""
	def __init__(self, fourier_freq_list, fourier_basis_list):
		super(DiffusionKernel, self).__init__(fourier_freq_list, fourier_basis_list)

	def forward(self, x1, x2=None, diagonal=False):
		"""
		:param x1, x2: each row is a vector with vertex numbers starting from 0 for each 
		:return: 
		"""
		if diagonal:
			assert x2 is None

		stabilizer = 0
		if x2 is None:
			x2 = x1
			if diagonal:
				stabilizer = 1e-6 * x1.new_ones(x1.size(0), 1, dtype=torch.float32)
			else:
				stabilizer = torch.diag(1e-6 * x1.new_ones(x1.size(0), dtype=torch.float32))

		full_gram = 1
		for i in range(len(self.fourier_freq_list)):
			fourier_freq = self.fourier_freq_list[i]
			fourier_basis = self.fourier_basis_list[i]

			if torch.isnan(fourier_freq).any():
				print(fourier_freq)
				raise RuntimeError('Nan in Frequency')
			if torch.isinf(fourier_freq).any():
				print(fourier_freq)
				raise RuntimeError('Inf in Frequency')
			if torch.isnan(fourier_basis).any():
				print(fourier_basis)
				raise RuntimeError('Nan in Basis')
			if torch.isinf(fourier_basis).any():
				print(fourier_basis)
				raise RuntimeError('Inf in Basis')

			subvec1 = fourier_basis[x1[:, i]]
			subvec2 = fourier_basis[x2[:, i]]
			freq_transform = torch.exp(-fourier_freq)


			if torch.isnan(subvec1).any():
				print(subvec1)
				raise RuntimeError('Nan in subvec1')
			if torch.isinf(subvec1).any():
				print(subvec1)
				raise RuntimeError('Inf in subvec1')
			if torch.isnan(subvec2).any():
				print(subvec2)
				raise RuntimeError('Nan in subvec2')
			if torch.isinf(subvec2).any():
				print(subvec2)
				raise RuntimeError('Inf in subvec2')
			if torch.isnan(freq_transform).any():
				print(freq_transform)
				raise RuntimeError('Nan in freq_transform')
			if torch.isinf(freq_transform).any():
				print(freq_transform)
				raise RuntimeError('Inf in freq_transform')
			if torch.isnan(torch.exp(self.log_amp)).any():
				raise RuntimeError('Nan in exp(log_amp)')
			if torch.isinf(torch.exp(self.log_amp)).any():
				raise RuntimeError('Inf in exp(log_amp)')

			if diagonal:
				factor_gram = torch.sum(subvec1 * freq_transform.unsqueeze(0) * subvec2, dim=1, keepdim=True)
			else:
				factor_gram = torch.matmul(subvec1 * freq_transform.unsqueeze(0), subvec2.t())
			# HACK for numerical stability for scalability
			full_gram *= factor_gram / torch.mean(freq_transform)

			if torch.isnan(factor_gram).any():
				print(factor_gram)
				raise RuntimeError('Nan in factor_gram')
			if torch.isinf(factor_gram).any():
				print(factor_gram)
				raise RuntimeError('Inf in factor_gram')
			if torch.isnan(1.0/torch.mean(freq_transform)).any():
				raise RuntimeError('Nan in 1.0/torch.mean(freq_transform)')
			if torch.isinf(1.0/torch.mean(freq_transform)).any():
				raise RuntimeError('Inf in 1.0/torch.mean(freq_transform)')
			if torch.isnan(full_gram).any():
				print(full_gram)
				raise RuntimeError('Nan in full_gram')
			if torch.isinf(full_gram).any():
				print(full_gram)
				raise RuntimeError('Inf in full_gram')

		return torch.exp(self.log_amp) * (full_gram + stabilizer)


if __name__ == '__main__':
	weight_mat_list = []
	graph_size = []
	n_variables = 24
	n_data = 10

	fourier_freq_list = []
	fourier_basis_list = []
	for i in range(n_variables):
		n_v = int(torch.randint(50, 51, (1,))[0])
		graph_size.append(n_v)
		# type_num = int(torch.randint(0, 3, (1,))[0])
		type_num = 1
		if type_num < 0:
			adjmat = (torch.rand(n_v, n_v) * 0.5 - 0.25).clamp(min=0).tril(-1)
			adjmat = adjmat + adjmat.t()
		elif type_num == 0:
			adjmat = torch.diag(torch.ones(n_v - 1), -1) + torch.diag(torch.ones(n_v - 1), 1)
			adjmat *= n_v * (n_v - 1) / 2.0
		elif type_num == 1:
			adjmat = torch.ones(n_v, n_v) - torch.eye(n_v)
		wgtsum = torch.sum(adjmat, dim=0)
		laplacian = (torch.diag(wgtsum) - adjmat)# / wgtsum ** 0.5 / wgtsum.unsqueeze(1) ** 0.5
		eigval, eigvec = torch.symeig(laplacian, eigenvectors=True)
		fourier_freq_list.append(eigval)
		fourier_basis_list.append(eigvec)
	k = DiffusionKernel(fourier_freq_list=fourier_freq_list, fourier_basis_list=fourier_basis_list)
	k.log_amp.fill_(0)
	k.log_beta.fill_(math.log(0.05))
	input_data = torch.empty([0, n_variables])
	for i in range(n_data):
		datum = torch.zeros([1, n_variables])
		for e, c in enumerate(graph_size):
			datum[0, e] = torch.randint(0, c, (1,))[0]
		input_data = torch.cat([input_data, datum], dim=0)
	input_data = input_data.long()
	data = k(input_data)

	# data = factor_gram / torch.mean(freq_transform)
	for r in range(data.size(0)):
		print(' '.join([' %+.2E' % data[r, i] for i in range(data.size(1))]))
