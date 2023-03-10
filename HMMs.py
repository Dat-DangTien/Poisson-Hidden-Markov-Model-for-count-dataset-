import scipy as sp
import numpy as np
from scipy import stats
from scipy.special import logsumexp
from numpy import seterr

class PHMM:
    """
    This class defines a Hidden Markov Model with Poisson emissions,
    in which all observed sequences are assumed to have the same initial
    state probabilities, transition probabilities, and Poisson emission
    parameters. C.f. the PHMM_d class, which assumes each sequence to have
    different emission parameters.
    Parameters
    ----------
    init_delta : float array
        Array of initial state probabilities, summing to 1.
        NOT LOG PROBABILITIES!
    init_theta : float array array
        Matrix of state transition probabilities, with each subarray
        summing to 1. NOT LOG PROBABILITIES!
    init_lambda : float array
        Array of initial Poisson emission parameter guesses.
    conv : float, optional
        Target convergence value for Baum-Welch training - the value defining
        how small individual parameter steps in unsupervised learning must be
        in order to stop training. Set to 10^-3 by default.
    Attributes
    ----------
    nstates : int
        Number of states in the HMM.
    delta : float array
        Array of initial state log probabilities.
    theta : float array array
        Matrix of state transition log probabilities.
    lambdas : float array
        Array of Poisson parameters.
    conv : float
        Target convergence for Baum-Welch training.
    """
    def __init__(self, init_delta, init_theta, init_lambdas, conv=1e-03):
        seterr(divide='ignore')
        self.nstates = len(init_delta)
        self.delta = np.log(init_delta)
        self.theta = np.log(init_theta)
        self.lambdas = np.array(init_lambdas)
        self.conv = conv
        seterr(divide='warn')

    """
    Returns the transition probability matrix (NOT log probabilities)
    """
    def transition_matrix(self):
        return np.exp(self.theta)

    """
    A Poisson random variable generator.
    Input
    -----
    mean : float
        This is the mean of the Poisson distribution we'll be sampling from.
        It must be greater than zero to sample from a true Poisson
        distribution; if set to -1 (the "stop state" value), the sampler
        will always return -1.
    Output
    ------
    int - a Poisson random variable sampled from distribution with mean 'mean'
    """
    def _sp_rvs(self, mean):
        if mean == -1:
            return -1
        else:
            return stats.poisson(mean).rvs()

    """
    A Poisson log probability mass function.
    Input
    -----
    mean : float
        Mean of the Poisson distribution we're using the lpmf of. Must either
        be greater than 0 or equal to -1, in the case a stop state is being
        used.
    val : int
        Value whose log probability is to be calculated.
    Output
    ------
    float - log probability of observing 'val' from Poisson distribution with
            mean 'mean'. Can be negative infinity for zero probabilities.
    """
    def _sp_lpmf(self, mean, val):
        if mean == -1:
            if val == -1:
                return 0
            else:
                return -np.inf
        elif mean >= 0:
            if val == -1:
                return -np.inf
            else:
                return stats.poisson(mean).logpmf(val)

    """
    Generates a random sequence of integers following the class's current
    PHMM specification.
    Input
    -----
    n : int, optional
        The length of the sequence to generate. If a stop state is defined
        (i.e., if the last element of each subarray of self.lambdas is -1),
        then this value is ignored, and generation will continue until the
        stop state is reached. If a stop state is not defined, this is
        set by default to 100, and it is not ignored.
    Output
    ------
    int array - a PHMM observation sequence constructed from the parameters
                specified by the class.
    int array - a sequence with the corresponding true state indices of the
                observation sequence (to be compared with Viterbi output).
    """
    def gen_seq(self, n=100):
        out_seq = [] # Eventual output sequence
        states = []  # True hidden states
        state = np.random.choice(a=self.nstates, p=np.exp(self.delta))#T???O RA 1  GI?? TR??? L?? NGUY??N T??? 0 ?????N A-1
        out_seq.append(self._sp_rvs(self.lambdas[state]))
        states.append(state)
        # Our stop condition, which differs based on whether we have a
        # stop state
        def condition():
            if self.lambdas[-1] == -1:
                return out_seq[-2] != -1
            else:
                return len(out_seq) < n
        while condition():
            state = np.random.choice(a=self.nstates, p=np.exp(self.theta[state]))
            out_seq.append(self._sp_rvs(self.lambdas[state]))
            states.append(state)
        return out_seq, states

    """
    Calculates the forward state log probabilities of a PHMM observation sequence.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - a nested sequence, where the subsequence at index i, j
                        is the forward log probability of state j for element i
                        in the sequence.
    """
    def forward_lprobs(self, seq):#seq nhu input tr??n b???o l?? ch??? l?? 1 d??y th??i, ch??? k ph???i d??y c???a d??y
        seterr(divide='ignore')
        g_1 = [self._sp_lpmf(self.lambdas[i], seq[0]) for i in range(self.nstates)]# tr??? v??? 1 array v???i m???i ph???n t??? l?? 
        #log c???a x??c su???t th???i ??i???m ?????u ti??n ob t???i seq[0] khi bi???t tham s??? Poisson l?? lambdas[i]
        g_1 = np.add(self.delta, g_1)#log (t??ch pi_0 x xs th???i ??i???m ?????u t???i seq[0])
        glst = [g_1]
        for i in range(1, len(seq)):
            g_i = []
            for j in range(self.nstates):
                prev = np.add(glst[-1], self.theta[::, j])
                prev = logsumexp(prev)
                g_ij = prev + self._sp_lpmf(self.lambdas[j], seq[i])
                g_i.append(g_ij)
            glst.append(g_i)
        g_n = glst[-1]
        seterr(divide='warn')
        return np.array(glst)

    """
    Calculates the forward log probability of observing a given sequence. Should
    be equal to the backward log probability of the same sequence.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float - the log probability of observing the given sequence.
    """
    def forward_lprob(self, seq):
        glst = self.forward_lprobs(seq)#l?? ma tr???n v???i m???i h??ng l?? ???ng v???i 1 gi?? tr??? c???a t
        return logsumexp(glst[-1])#log(xich ma t??? i ?????n N c???a alpha_T^(i))

    """
    Calculates the backward state log probabilities of a PHMM observation sequence.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - a nested sequence, where the subsequence at index i, j
                        is the backward log probability of state j for element i
                        in the sequence.
    """
    def backward_lprobs(self, seq):
        seterr(divide='ignore')
        f_n = [self._sp_lpmf(self.lambdas[i], seq[-1]) for i in range(self.nstates)]
        flst = [f_n]
        for i in range(len(seq) - 2, -1, -1):
            f_i = []
            for j in range(self.nstates):
                prev = np.add(self.theta[j], flst[-1])
                prev = logsumexp(prev)
                f_ij = self._sp_lpmf(self.lambdas[j], seq[i]) + prev
                f_i.append(f_ij)
            flst.append(f_i)
        flst.reverse()
        seterr(divide='warn')
        return np.array(flst)

    """
    Calculates the backward log probability of observing a given sequence. Should
    be equal to the forward log probability of the same sequence.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float - the log probability of observing the given sequence.
    """
    def backward_lprob(self, seq):
        flst = self.backward_lprobs(seq)
        f_1 = np.add(self.delta, flst[0])
        return logsumexp(f_1)

    """
    Calculates the probability of being in each state for every element of
    an observation sequence using the forward-backward algorithm.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - an array of arrays defining the probability, for each
                        observation in a sequence, of being in each given state.
                        Note: this does not give us the most likely path!
    """
    def forward_backward(self, seq):
        fprobs = self.forward_lprobs(seq)#c??i forward_lprobs l?? ma tr???n c?? t???ng ph???n t??? l?? log alpha(t) v???i t t??? 0 ?????n T, i tu 1 den N
        bprobs = self.backward_lprobs(seq)
        probs = np.add(fprobs, bprobs)# la ma tran
        probsums = list(map(logsumexp, probs))
        norm_probs = list(map(lambda lst, sum_: list(map(lambda x: x - sum_, lst)), probs, probsums))#probs-probsums
        return np.exp(norm_probs) # l?? ma tr???n c??c gamma_t^(i) v???i bi???n ch???y l?? t v?? i, v?? h??ng l?? ?????i di???n cho bi???n i, t???c ng?????c v???i h??nh
        # v??? trong video tr??n youtube

    """
    Calculates the log-likelihood of the given HMM generating the
    provided sequences.
    Input
    -----
    seqlst : int array array
        An array of observation sequences. Should contain as many sequences
        as there are sets of parameters in self.lambdas. If a stop state is
        defined, make sure that each sequence has two -1s append to its end.
    Output
    ------
    float - log probability of observing all the sequences - i.e., logsumexp
            of observing each individual sequence. This might be a metric for
            goodness of fit.
    """
    def log_likelihood(self, seqlst):
        probs = list(map(self.forward_lprob, seqlst))#v???n ????ng v?? ????y l?? l???y t???ng ph???n t??? 
        return np.sum(probs)#b??i to??n 1 c???a HMMs nh??ng ????y l?? cho v?? seqlst , coi seqlst nh?? 1 d??y d??i, c??n c???a mk ch??? c???n 1 seq l?? ??c

    """
    Calculates the most likely state path of an observation sequence.
    Input
    -----
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    int array - most likely state path of the observation sequence,
                where the state numbers are zero-indexed.
    """
    def viterbi(self, seq):
        print(seq[0])
        v_n = [0.0 for _ in range(self.nstates)]
        vlst = [v_n]
        wlst = []
        for i in range(len(seq) - 1, 0, -1):#tu t=T tro xuong, tu trang thai cuoi
            v_i = []
            w_i = []
            for j in range(self.nstates):#for i tu 1 den N
                all_v_ij = []
                for k in range(self.nstates):#_sp_lmf l?? h??m t??nh x??c su???t 
                    temp = self.theta[j, k] + self._sp_lpmf(self.lambdas[k], seq[i])# l?? c??i 
                    temp += vlst[-1][k]#vlst[-1][k] la xs lon nhat tu diem ban dau di toi trang thai k tai thoi diem t nay
                    all_v_ij.append(temp)
                v_i.append(max(all_v_ij))
                w_i.append(np.argmax(all_v_ij))
            vlst.append(v_i)
            wlst.append(w_i)
        wlst.reverse()
        first_prob = [self._sp_lpmf(self.lambdas[i], seq[0]) for i in range(self.nstates)]
        first_prob = np.add(first_prob, self.delta)
        first_prob = np.add(first_prob, vlst[-1])
        h_1 = np.argmax(first_prob)
        statelst = [h_1]
        for i in range(len(wlst)):
            statelst.append(wlst[i][statelst[-1]])
        return statelst

    """
    Trains the PHMM on a set of observation sequences using the Baum-Welch
    algorithm, a special case of the EM algorithm.
    Input
    -----
    seqlst : int array array
        An array of observation sequences. If a stop state is
        defined, make sure that each sequence has two -1s append to its end.
    max_iter : int, optional
        An integer defining after how many steps the algorithm should terminate
        if the convergence criterion is not met. Set to 200 by default.
    Action
    ------
    Trains the PHMM to best fit the provided list of sequences.
    """
    def baum_welch(self, seqlst, max_iter=200):#seqlst t???c l?? list c??c seq
    #v???n ????? trong file example.py: theo l?? thuy???t th?????ng l?? ch??? c???n truy???n v??o 1 chu???i observation data ????? thu???t to??n baum-welch
    #luy???n, t?????ng ch???ng 1 chu???i ra 1 b??? tham s???, v m?? ??? ????y seqlst g???m t???n 20 chu???i => m?? k???t qu??? ch??? ra 1 b??? tham sso n??n c?? th??? trong 
    #code n??y th?? s??? d???ng nhi???u chu???i, ==> n???u d??ng chu???i t??? data th?? s??? kh??ng ph???i code n??y ???????c, v???y n??n hi???u code n??y c??i 
    #CH???T 1 PH???N: viterbi th?? ch??? c???n 1 seq c??n baum trong ????y c???n lst c??

        itr = 0
        trans = self.theta
        lambdalst = self.lambdas
        prev_trans = None
        prev_lambdalst = None

        # Convergence-checking function
        def assess_convergence(ll=False):
            if prev_trans is None or prev_lambdalst is None:
                return False
            diff = []
            bools = []
            for i in range(len(trans)):
                for j in range(len(trans[i])):
                    if np.isneginf(trans[i, j]) or np.isneginf(prev_trans[i, j]):
                        pass
                    else:
                        d = abs(trans[i, j] - prev_trans[i, j])# l?? log(th????ng 2 ph???n t??? a_ij c???a ma tr???n ??? v??ng l???p tr?????c v?? sau)
                        diff.append(d)
                        bools.append(d <= self.conv)
            for i in range(len(lambdalst)):
                d = abs(lambdalst[i] - prev_lambdalst[i])#l?? log(th????ng 2 tham s??? lambda c???a pp Poisson ??? v??ng l???p tr?????c v?? sau)
                diff.append(d)
                bools.append(d <= self.conv)
            print("Difference: ", sum(diff))# ph???n n??y ch???c l?? ?????I DI???N log_likelihood function c???a 2 v??ng l???p tr??? ??i nhau CH??? CT KH??NG 
            #GI???NG H???N NH?? V???Y
            if ll:
                print("Log-Likelihood:", self.log_likelihood(seqlst))
            return all(bools)# ch??? khi m???i ph???n t??? tr??? ??i nhau ?????u nh??? h??n c??i chu???n so s??nh th?? m???i True h???t, th?? khi ?? 
            #K???T QU??? bools m???i l?? True h???t v???i m???i ph???n t??? th?? m???i l?? h???i t???

        while not assess_convergence() and itr < max_iter:
            prev_trans = trans#G??n 2 gi?? tr??? v???a l???n tr?????c l?? gi?? tr??? tr?????c 
            prev_lambdalst = lambdalst#  ????? c???p nh???t cho gi?? tr??? v??ng hi???n t???i
            trans_lst = []
            #seqs=seqlst
            seqs = [d for sub in seqlst for d in sub]#in ra seqs l?? chu???i g???m 2000 ph???n t??? v???i file example.py
            #print(len(seqs))
            rs = []#ph???n t???o n??n s??? kh??c bi???t khi m???i s??? d???ng t???ng chu???i seq trong seqlst
            for seq, k in zip(seqlst, range(len(seqlst))):#zip(bien1,bien2) l?? ????a v??? d???ng g???m c??c tuple(bien1[i],bien2[i]), ????? 
            #chuy???n th??nh list of tuple th?? c???n ?????t zip trong h??m ???? l?? ???????c 
                flst = self.backward_lprobs(seq)#t??nh ma tr???n beta_t^(i) v???i m???i h??ng l?? theo i
                rlst = []
                r_1_hat = np.add(self.delta, flst[0])#l?? log(tich c???a ph??n ph???i ban ?????u v???i beta_0^(i) v???i bi???n ch???y i)
                r_1_sum = logsumexp(r_1_hat)#log(xichma c???a i ch???y t??? 1 ?????n N c???a pi_i x beta_0^(i))
                r1 = list(map(lambda r: r - r_1_sum, r_1_hat))#ghi ra gi???y cthuc r
                rlst.append(r1)
                tlst = []
                for i in range(1, len(seq)):
                    t_i_hat = []
                    # Indexed the same as transition matrix
                    for j in range(self.nstates):
                        t_i_hat.append(rlst[-1][j] + np.add(trans[j], flst[i]))
                    t_i_sum = logsumexp(t_i_hat)
                    t_i = list(map(lambda lst: list(map(lambda t: t - t_i_sum, lst)), t_i_hat))
                    r_i = np.array(list(map(logsumexp, zip(*t_i))))
                    tlst.append(t_i)
                    rlst.append(r_i)
                expd_trans = []
                for j in range(len(trans)):
                    expd_trans.append([])
                    for l in range(len(trans[j])):
                        t_ij = [tlst[t][j][l] for t in range(len(tlst))]
                        expd_trans[j].append(logsumexp(t_ij))
                trans_lst.append(expd_trans)
                # Now we calculate expected values of the Poisson parameters (wow!)
                rs.append(rlst)
            # Update initial probs
            r1s = [d[0] for d in rs]#1 d??y g???m c??c rs[i][0], d?????ng nh?? rs l?? array array array= array matrix, m???i seq th?? rs l?? 1 matrix
            new_delta = []
            for j in range(len(self.delta)):
                d_i = logsumexp([r1s[t][j] for t in range(len(r1s))])
                new_delta.append(d_i)
            del_sum = logsumexp(new_delta)
            new_delta = np.array(list(map(lambda x: x - del_sum, new_delta)))
            # Update Poisson parameters
            rs = [d for sub in rs for d in sub]
            seq_probs = np.exp(list(zip(*rs)))
            sums = np.array(list(map(sum, seq_probs)))
            scaled_vals = seqs * seq_probs
            expd_vals = np.array(list(map(sum, scaled_vals)))
            pmeans = expd_vals / sums
            lambdalst = pmeans
            # Update transition matrix
            expd_trans = []
            for j in range(len(trans)):
                    expd_trans.append([])
                    for l in range(len(trans[j])):
                        t_ij = [trans_lst[t][j][l] for t in range(len(trans_lst))]
                        expd_trans[j].append(logsumexp(t_ij))
            totals = list(map(logsumexp, expd_trans))
            new_trans = list(map(lambda tlst, t: list(map(lambda et: et - t, tlst)), expd_trans, totals))
            trans = np.array(new_trans)
            # Apply updates
            self.delta = new_delta
            self.theta = trans
            self.lambdas = lambdalst

class PHMM_d:
    """
    This class defines a Hidden Markov Model with Poisson emissions,
    in which all observed sequences are assumed to have the same initial
    state probabilities and transition probabilities, but each sequence
    is assumed to have different Poisson emission parameters. C.f. the
    PHMM class, which assumes all sequences also have the same Poisson
    emission parameters.
    Parameters
    ----------
    init_delta : float array
        Array of initial state probabilities, summing to 1.
        NOT LOG PROBABILITIES!
    init_theta : float array array
        Matrix of state transition probabilities, with each subarray
        summing to 1. NOT LOG PROBABILITIES!
    init_lambda : float array array
        Matrix of initial Poisson parameter guesses, where each subarray
        is an observation sequence's parameters. Each must be greater
        than 0. NOTE: if you wish to have a defined "stop state," you
        must set the final lambda parameter for each site equal to -1, and
        append -1 twice to the end of all sequences.
    conv : float, optional
        Target convergence value for Baum-Welch training - the value defining
        how small individual parameter steps in unsupervised learning must be
        in order to stop training. Set to 10^-3 by default.
    Attributes
    ----------
    nstates : int
        Number of states in the HMM.
    delta : float array
        Array of initial state log probabilities.
    theta : float array array
        Matrix of state transition log probabilities.
    lambdas : float array array
        Matrix of Poisson parameters for each sequence.
    conv : float
        Target convergence for Baum-Welch training.
    """
    def __init__(self, init_delta, init_theta, init_lambdas, conv=1e-03):
        seterr(divide='ignore')
        self.nstates = len(init_delta)
        self.delta = np.log(init_delta)
        self.theta = np.log(init_theta)
        self.lambdas = np.array(init_lambdas)
        self.conv = conv
        seterr(divide='warn')

    """
    Returns the transition probability matrix (NOT log probabilities)
    """
    def transition_matrix(self):
        return np.exp(self.theta)

    """
    A Poisson random variable generator.
    Input
    -----
    mean : float
        This is the mean of the Poisson distribution we'll be sampling from.
        It must be greater than zero to sample from a true Poisson
        distribution; if set to -1 (the "stop state" value), the sampler
        will always return -1.
    Output
    ------
    int - a Poisson random variable sampled from distribution with mean 'mean'
    """
    def _sp_rvs(self, mean):
        if mean == -1:
            return -1
        else:
            return stats.poisson(mean).rvs()

    """
    A Poisson log probability mass function.
    Input
    -----
    mean : float
        Mean of the Poisson distribution we're using the lpmf of. Must either
        be greater than 0 or equal to -1, in the case a stop state is being
        used.
    val : int
        Value whose log probability is to be calculated.
    Output
    ------
    float - log probability of observing 'val' from Poisson distribution with
            mean 'mean'. Can be negative infinity for zero probabilities.
    """
    def _sp_lpmf(self, mean, val):
        if mean == -1:
            if val == -1:
                return 0
            else:
                return -np.inf
        elif mean >= 0:
            if val == -1:
                return -np.inf
            else:
                return stats.poisson(mean).logpmf(val)

    """
    Generates a random sequence of integers following the class's current
    PHMM specification.
    Input
    -----
    k : int, optional
        The index of which subarray of self.lambdas to use. If not given, a
        set of emission parameters is randomly chosen.
    n : int, optional
        The length of the sequence to generate. If a stop state is defined
        (i.e., if the last element of each subarray of self.lambdas is -1),
        then this value is ignored, and generation will continue until the
        stop state is reached. If a stop state is not defined, this is
        set by default to 100, and it is not ignored.
    Output
    ------
    int array - a PHMM observation sequence constructed from the parameters
                specified by the class.
    int array - a sequence with the corresponding true state indices of the
                observation sequence (to be compared with Viterbi output).
    """
    def gen_seq(self, k=None, n=100):
        out_seq = [] # Eventual output sequence
        states = []  # True hidden states
        lambda_ind = np.random.choice(a=len(self.lambdas)) if k is None else k
        state = np.random.choice(a=self.nstates, p=np.exp(self.delta))
        out_seq.append(self._sp_rvs(self.lambdas[lambda_ind, state]))
        states.append(state)
        # Our stop condition, which differs based on whether we have a
        # stop state
        def condition():
            if self.lambdas[lambda_ind][-1] == -1:
                return out_seq[-2] != -1
            else:
                return len(out_seq) < n
        while condition():
            state = np.random.choice(a=self.nstates, p=np.exp(self.theta[state]))
            out_seq.append(self._sp_rvs(self.lambdas[lambda_ind, state]))
            states.append(state)
        return out_seq, states

    """
    Calculates the forward state log probabilities of a PHMM observation sequence.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - a nested sequence, where the subsequence at index i, j
                        is the forward log probability of state j for element i
                        in the sequence.
    """
    def forward_lprobs(self, s, seq):
        seterr(divide='ignore')
        g_1 = [self._sp_lpmf(self.lambdas[s, i], seq[0]) for i in range(self.nstates)]
        g_1 = np.add(self.delta, g_1)
        glst = [g_1]
        for i in range(1, len(seq)):
            g_i = []
            for j in range(self.nstates):
                prev = np.add(glst[-1], self.theta[::, j])
                prev = logsumexp(prev)
                g_ij = prev + self._sp_lpmf(self.lambdas[s, j], seq[i])
                g_i.append(g_ij)
            glst.append(g_i)
        g_n = glst[-1]
        seterr(divide='warn')
        return np.array(glst)

    """
    Calculates the forward log probability of observing a given sequence. Should
    be equal to the backward log probability of the same sequence.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float - the log probability of observing the given sequence.
    """
    def forward_lprob(self, s, seq):
        glst = self.forward_lprobs(s, seq)
        return logsumexp(glst[-1])

    """
    Calculates the backward state log probabilities of a PHMM observation sequence.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - a nested sequence, where the subsequence at index i, j
                        is the backward log probability of state j for element i
                        in the sequence.
    """
    def backward_lprobs(self, s, seq):
        seterr(divide='ignore')
        f_n = [self._sp_lpmf(self.lambdas[s, i], seq[-1]) for i in range(self.nstates)]
        flst = [f_n]
        for i in range(len(seq) - 2, -1, -1):
            f_i = []
            for j in range(self.nstates):
                prev = np.add(self.theta[j], flst[-1])
                prev = logsumexp(prev)
                f_ij = self._sp_lpmf(self.lambdas[s, j], seq[i]) + prev
                f_i.append(f_ij)
            flst.append(f_i)
        flst.reverse()
        seterr(divide='warn')
        return np.array(flst)

    """
    Calculates the backward log probability of observing a given sequence. Should
    be equal to the forward log probability of the same sequence.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float - the log probability of observing the given sequence.
    """
    def backward_lprob(self, s, seq):
        flst = self.backward_lprobs(s, seq)
        f_1 = np.add(self.delta, flst[0])
        return logsumexp(f_1)

    """
    Calculates the probability of being in each state for every element of
    an observation sequence using the forward-backward algorithm.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    float array array - an array of arrays defining the probability, for each
                        observation in a sequence, of being in each given state.
                        Note: this does not give us the most likely path!
    """
    def forward_backward(self, s, seq):
        fprobs = self.forward_lprobs(s, seq)
        bprobs = self.backward_lprobs(s, seq)
        probs = np.add(fprobs, bprobs)
        probsums = list(map(logsumexp, probs))
        norm_probs = list(map(lambda lst, sum: list(map(lambda x: x - sum, lst)), probs, probsums))
        return np.exp(norm_probs)

    """
    Calculates the log-likelihood of the given HMM generating the
    provided sequences.
    Input
    -----
    seqlst : int array array
        An array of observation sequences. Should contain as many sequences
        as there are sets of parameters in self.lambdas. If a stop state is
        defined, make sure that each sequence has two -1s append to its end.
    Output
    ------
    float - log probability of observing all the sequences - i.e., logsumexp
            of observing each individual sequence. This might be a metric for
            goodness of fit.
    """
    def log_likelihood(self, seqlst):
        probs = list(map(self.forward_lprob, range(len(seqlst)), seqlst))
        return np.sum(probs)

    """
    Calculates the most likely state path of an observation sequence.
    Input
    -----
    s : int
        The index of which subarray of self.lambdas to use to calculate log
        probability of observations.
    seq : int array
        A PHMM observation sequence.
    Output
    ------
    int array - most likely state path of the observation sequence (0-indexed)
    """
    def viterbi(self, s, seq):
        v_n = [0.0 for _ in range(self.nstates)]
        vlst = [v_n]
        wlst = []
        for i in range(len(seq) - 1, 0, -1):
            v_i = []
            w_i = []
            for j in range(self.nstates):
                all_v_ij = []
                for k in range(self.nstates):
                    temp = self.theta[j, k] + self._sp_lpmf(self.lambdas[s, k], seq[i])
                    temp += vlst[-1][k]
                    all_v_ij.append(temp)
                v_i.append(max(all_v_ij))
                w_i.append(np.argmax(all_v_ij))
            vlst.append(v_i)
            wlst.append(w_i)
        wlst.reverse()
        first_prob = [self._sp_lpmf(self.lambdas[s, i], seq[0]) for i in range(self.nstates)]
        first_prob = np.add(first_prob, self.delta)
        first_prob = np.add(first_prob, vlst[-1])
        h_1 = np.argmax(first_prob)
        statelst = [h_1]
        for i in range(len(wlst)):
            statelst.append(wlst[i][statelst[-1]])
        return statelst

    """
    Trains the PHMM on a set of observation sequences using the Baum-Welch
    algorithm, a special case of the EM algorithm.
    Input
    -----
    seqlst : int array array
        An array of observation sequences. Should contain as many sequences
        as there are sets of parameters in self.lambdas. If a stop state is
        defined, make sure that each sequence has two -1s append to its end.
    max_iter : int, optional
        An integer defining after how many steps the algorithm should terminate
        if the convergence criterion is not met. Set to 500 by default.
    Action
    ------
    Trains the PHMM to best fit the provided list of sequences.
    """
    def baum_welch(self, seqlst, max_iter=200):
        itr = 0
        trans = self.theta
        lambdalst = self.lambdas
        prev_trans = None
        prev_lambdalst = None

        # Need to make convergence more legit
        def assess_convergence(ll=False):
            if prev_trans is None or prev_lambdalst is None:
                return False
            diff = []
            bools = []
            for i in range(len(trans)):
                for j in range(len(trans[i])):
                    if np.isneginf(trans[i, j]) and np.isneginf(prev_trans[i, j]):
                        diff.append(0)
                        bools.append(True)
                    else:
                        d = abs(trans[i, j] - prev_trans[i, j])
                        diff.append(d)
                        bools.append(d <= self.conv)
            for i in range(len(lambdalst)):
                for j in range(len(lambdalst[i])):
                    d = abs(lambdalst[i][j] - prev_lambdalst[i][j])
                    diff.append(d)
                    bools.append(d <= self.conv)
            print("Difference: ", sum(diff))
            if ll:
                print("Log-Likelihood:", self.log_likelihood(seqlst))
            return all(bools)

        while not assess_convergence() and itr < max_iter:
            prev_trans = trans
            prev_lambdalst = lambdalst
            trans_lst = []
            r1s = []
            for seq, k in zip(seqlst, range(len(seqlst))):
                flst = self.backward_lprobs(k, seq)
                rlst = []
                r_1_hat = np.add(self.delta, flst[0])
                r_1_sum = logsumexp(r_1_hat)
                r1 = list(map(lambda r: r - r_1_sum, r_1_hat))
                rlst.append(r1)
                tlst = []
                for i in range(1, len(seq)):
                    t_i_hat = []
                    # Indexed the same as transition matrix
                    for j in range(self.nstates):
                        t_i_hat.append(rlst[-1][j] + np.add(trans[j], flst[i]))
                    t_i_sum = logsumexp(t_i_hat)
                    t_i = list(map(lambda lst: list(map(lambda t: t - t_i_sum, lst)), t_i_hat))
                    r_i = np.array(list(map(logsumexp, zip(*t_i))))
                    tlst.append(t_i)
                    rlst.append(r_i)
                expd_trans = []
                for j in range(len(trans)):
                    expd_trans.append([])
                    for l in range(len(trans[j])):
                        t_ij = [tlst[t][j][l] for t in range(len(tlst))]
                        expd_trans[j].append(logsumexp(t_ij))
                trans_lst.append(expd_trans)
                r1s.append(rlst[0])
                # Update Poisson parameters
                seq_probs = np.exp(list(zip(*rlst)))
                sums = np.array(list(map(sum, seq_probs)))
                scaled_vals = seq * seq_probs
                expd_vals = np.array(list(map(sum, scaled_vals)))
                pmeans = expd_vals / sums
                pmeans = [p if p >= 0 else 999 for p in pmeans]
                pmeans = [p if p != 0 else 0.001 for p in pmeans]
                if lambdalst[k][-1] == -1:
                    pmeans[-1] = -1
                lambdalst[k] = pmeans
            # Update initial probabilities
            new_delta = []
            for j in range(len(self.delta)):
                d_i = logsumexp([r1s[t][j] for t in range(len(r1s))])
                new_delta.append(d_i)
            del_sum = logsumexp(new_delta)
            new_delta = np.array(list(map(lambda x: x - del_sum, new_delta)))
            # Update transition probabilities
            expd_trans = []
            for j in range(len(trans)):
                expd_trans.append([])
                for l in range(len(trans[j])):
                    t_ij = [trans_lst[t][j][l] for t in range(len(trans_lst))]
                    expd_trans[j].append(logsumexp(t_ij))
            totals = list(map(logsumexp, expd_trans))
            new_trans = list(map(lambda tlst, t: list(map(lambda et: et - t, tlst)), expd_trans, totals))
            trans = np.array(new_trans)
            self.delta = new_delta
            self.theta = trans
            self.lambdas = lambdalst