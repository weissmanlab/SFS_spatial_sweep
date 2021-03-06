#!/usr/bin/env python3
"""
Coalescent simulation with recombination.
open the frequency file read backward in time until n individuals all coalesce.
As we go, we will record the number of leaves for each node. 
If the neutral mutation arises as a Poisson process with rate Un = 1, 
the expected AFS is the histogram of the leaf counts 

Update : pre-sweep coalescent process changed to account for more than one 
mergers in a single generation when there are many individuals are left. 
(compared to sqrt(2 * N))


"""



import numpy as np
import random as rand
from multiprocessing import Pool
from multiprocessing import Process
import sys
from numpy import random
import os.path
from os import path


# L = 500
# N = 5000
# s = 0.05
# m = 0.25
# r = 0
# tfinal = 10000
# nbase = 1000
# N_SFS = 10


L = int(sys.argv[1]) # number of demes
N = int(sys.argv[2]) # deme capacity
s = float(sys.argv[3]) # selection coef
m = float(sys.argv[4]) # migration rate
r = float(sys.argv[5]) # recombination rate
tfinal = int(sys.argv[6]) # sweep time
nbase = int(sys.argv[7]) # sample size
N_SFS = int(sys.argv[8]) # number of coalescent simulation we run.
T_after_fix = int(sys.argv[9]) # number of generations between fixation and sampling
n_forward = int(sys.argv[10]) # forward time simulation number
startIndx = int(sys.argv[11])
endIndx = int(sys.argv[12])
mutationSite = int(sys.argv[13])

step = 1
r_per_base = 1e-8
mutationRate = r_per_base * 10

fname = 'L={}_N={}_s={:.6f}_m={:.6f}_tfinal={}_{}.txt'.format(L, 
           N, s, m, tfinal, n_forward)
freq_file = open(fname)
lines = np.loadtxt(fname, dtype=np.int64)

# a/b, except = 0 when b = 0
# https://stackoverflow.com/questions/26248654/how-to-return-0-with-divide-by-zero
def safe_divide(a, b, val=0):
    return np.divide(a, b, out=np.full_like(a, val), where=b != 0)

# Coalescence before the sweep (neutral L * N pop)

def get_parent_presweep_arr_new(inds):


    mut_types, deme_arr, ind_in_deme_arr = inds.T
    mut_types_new = (np.zeros_like(mut_types)).astype(np.int64)
    deme_arr_new = np.zeros_like(deme_arr)
    ind_in_deme_arr_new = np.zeros_like(ind_in_deme_arr)

    len_inds = len(inds)
    # array of random numbers used to determine which deme the parent is in.
    which_deme_rand = random.random(len_inds)
    # random numbers used to determine which individual to pick in each deme.
    choice_rand = random.random(len_inds)
    left_range_prob = m / 2 # prob of going to the left
    mid_range_prob = 1 - m / 2 # P(left) + P(middle)
    # P(left) + P(middle) + P(right) = 1

    left_idxs = np.where(which_deme_rand < left_range_prob)[0]
    deme_arr_new[left_idxs] = (deme_arr[left_idxs] - 1).astype(np.int64)

    mid_idxs = np.where(np.logical_and(
        which_deme_rand > left_range_prob,
        which_deme_rand < mid_range_prob))[0]
    deme_arr_new[mid_idxs] = (deme_arr[mid_idxs]).astype(np.int64)

    right_idxs = np.where(which_deme_rand > mid_range_prob)[0]
    deme_arr_new[right_idxs] = (deme_arr[right_idxs] + 1).astype(np.int64)


    # Taking care of the edge cases
    
    left_edge_idxs = np.where(deme_arr_new < 0)[0]
    deme_arr_new[left_edge_idxs] = 0

    right_edge_idxs = np.where(deme_arr_new > L - 1)[0]
    deme_arr_new[right_edge_idxs] = L - 1

    ind_in_deme_arr_new = (np.floor(choice_rand * N)).astype(np.int64)

    inds2 = np.vstack((mut_types_new,
                              deme_arr_new,
                              ind_in_deme_arr_new)).T
    return inds2

def get_individuals2_new(Ne, Ne_parent, individuals):
    '''
    for each bucket, choose between neighboring/own buckets w/ relative
    probabilities [m/2, 1-m] respectively.
    '''
    # mut_types, i_arr = individuals.T
    mut_types, deme_arr, ind_in_deme_arr = individuals.T
    deme_arr = (deme_arr).astype(np.int64)

    Nwt = (N - Ne).astype(np.int64)
    Nwt_parent = (N - Ne_parent).astype(np.int64)
    mut_types_next = np.ones_like(mut_types)
    p_vals = random.random(len(mut_types))

    # There are two ways in which an individual be a wt:
    # First, it could be already a mutant and recombine with a WT
    zero_idx = np.where(np.logical_and(
        mut_types == 1,
        p_vals < r * np.take(Nwt, deme_arr) / (N - 1)))[0]
    mut_types_next[zero_idx] = 0

    # Second, it can be a WT originally and NOT recombine with a mutant in the same deme
    zero_idx2 = np.where(np.logical_and(
        mut_types == 0,
        p_vals > r * np.take(Ne, deme_arr) / (N - 1)))[0]
    mut_types_next[zero_idx2] = 0


    deme_arr_next = np.zeros_like(deme_arr)
    ind_in_deme_arr_next = np.zeros_like(ind_in_deme_arr)
    Ne_parent_extended = np.concatenate(([Ne_parent[0]], Ne_parent, [Ne_parent[-1]]))
    Nwt_parent_extended = np.concatenate(([Nwt_parent[0]], Nwt_parent, [Nwt_parent[-1]]))

    len_inds = len(deme_arr_next)

    # For mutant first, find the parent's deme and then its index inside the deme
    left_parent_prob = m / 2 * np.take(Ne_parent_extended, deme_arr)
    mid_parent_prob = (1 - m) * np.take(Ne_parent_extended, deme_arr + 1)
    right_parent_prob = m / 2 * np.take(Ne_parent_extended, deme_arr + 2)
    total_prob = (left_parent_prob + mid_parent_prob + right_parent_prob)

    # Set the cumulative probability
    mid_parent_prob = safe_divide(
        left_parent_prob + mid_parent_prob,
        total_prob,
        val=1,
    )
    left_parent_prob = safe_divide(left_parent_prob, total_prob)


    which_parent_rand = random.random(len_inds) # choose btw left/mid/right
    choice_rand = random.random(len_inds) # used for index within the deme


    left_parent_idxs = np.where(np.logical_and(
        which_parent_rand < left_parent_prob,
        mut_types_next == 1))[0]
    deme_arr_next[left_parent_idxs] = (deme_arr[left_parent_idxs] - 1).astype(np.int64)



    mid_parent_idxs = np.where(np.logical_and.reduce((
        which_parent_rand > left_parent_prob,
        which_parent_rand < mid_parent_prob,
        mut_types_next == 1)))[0]
    deme_arr_next[mid_parent_idxs] = (deme_arr[mid_parent_idxs]).astype(np.int64)


    right_parent_idxs = np.where(np.logical_and(
        which_parent_rand > mid_parent_prob,
        mut_types_next ==1))[0]
    deme_arr_next[right_parent_idxs] = (deme_arr[right_parent_idxs] + 1).astype(np.int64)

    left_edge_idxs = np.where(deme_arr_next < 0)[0]
    deme_arr_next[left_edge_idxs] = (np.zeros_like(left_edge_idxs)).astype(np.int64)

    right_edge_idxs = np.where(deme_arr_next > L - 1)[0]
    deme_arr_next[right_edge_idxs] = (np.ones_like(right_edge_idxs) *
                                      (L - 1)).astype(np.int64)

    mut_idxs = np.concatenate((left_parent_idxs, mid_parent_idxs, right_parent_idxs))
    ind_in_deme_arr_next[mut_idxs] = (np.floor(
        choice_rand[mut_idxs] * np.take(Ne_parent,
                              deme_arr_next[mut_idxs]))).astype(np.int64)

    # then same for wt
    left_parent_prob = m / 2 * np.take(Nwt_parent_extended, deme_arr)
    mid_parent_prob = (1 - m) * np.take(Nwt_parent_extended, deme_arr + 1)
    right_parent_prob = m / 2 * np.take(Nwt_parent_extended, deme_arr + 2)
    total_prob = (left_parent_prob + mid_parent_prob + right_parent_prob)
    mid_parent_prob = safe_divide(
        left_parent_prob + mid_parent_prob,
        total_prob,
        val=1,
    )
    left_parent_prob = safe_divide(left_parent_prob, total_prob)

    which_parent_rand = random.random(len_inds) # choose btw left/mid/right
    choice_rand = random.random(len_inds) # used for index within the deme


    left_parent_idxs = np.where(np.logical_and(
        which_parent_rand < left_parent_prob,
        mut_types_next == 0))[0]
    deme_arr_next[left_parent_idxs] = (deme_arr[left_parent_idxs] - 1).astype(np.int64)

    mid_parent_idxs = np.where(np.logical_and.reduce((
        which_parent_rand > left_parent_prob,
        which_parent_rand < mid_parent_prob,
        mut_types_next == 0)))[0]
    deme_arr_next[mid_parent_idxs] = (deme_arr[mid_parent_idxs]).astype(np.int64)


    right_parent_idxs = np.where(np.logical_and(
        which_parent_rand > mid_parent_prob,
        mut_types_next == 0))[0]
    deme_arr_next[right_parent_idxs] = (deme_arr[right_parent_idxs] + 1).astype(np.int64)

    left_edge_idxs = np.where(deme_arr_next < 0)[0]
    deme_arr_next[left_edge_idxs] = (np.zeros_like(left_edge_idxs)).astype(np.int64)

    right_edge_idxs = np.where(deme_arr_next > L - 1)[0]
    deme_arr_next[right_edge_idxs] = (np.ones_like(right_edge_idxs) * (L - 1)).astype(np.int64)

    wt_idxs = np.concatenate((left_parent_idxs, mid_parent_idxs, right_parent_idxs))
    ind_in_deme_arr_next[wt_idxs] = (np.floor(
        choice_rand[wt_idxs] * np.take(Nwt_parent,
                              deme_arr_next[wt_idxs]))).astype(np.int64)
    individuals2 = np.vstack((mut_types_next,
                              deme_arr_next,
                              ind_in_deme_arr_next)).T
    return individuals2

def runner(idx):
    Ne_0 = lines[-1]
    n = nbase
    SFS = np.zeros(n)

    Ne = Ne_0
    Ne = (Ne).astype(np.int64)
    # Ne = [range(Ne_0[i]) for i in range(len(Ne_0))]
    individuals = [] # format will be [mut_type, deme index, individual index (inside the deme)]
    if n < round(sum(Ne)):
        individuals_location = random.choice(np.arange(0
        , round(sum(Ne))), size = n, replace = False)

    else:
        individuals_location = np.arange(0
        , round(sum(Ne)))
        n = sum(Ne)
    ind_inside_deme = np.mod(individuals_location, N)
    deme_ind = (individuals_location - ind_inside_deme) // N

    for k in range(n):
        # 1 is for having beneficial mutation
        individuals.append([1, deme_ind[k], ind_inside_deme[k]])
        
    individuals = np.array(individuals)
    unique, leaf_counts = np.unique(individuals, axis = 0, return_counts = True)
    hist, bin_edges = np.histogram(leaf_counts, bins = np.arange(1, n + 2))


    t_after_fix = 0
    while t_after_fix < T_after_fix:
        t_after_fix += 1
        individuals2 = get_individuals2_new(Ne, Ne, individuals)
        individuals2 = np.repeat(individuals2, leaf_counts, axis = 0)
        unique, leaf_counts = np.unique(individuals2, axis = 0,
                                         return_counts = True)
        
        hist, bin_edges = np.histogram(leaf_counts,
                                       bins = np.arange(1, n + 2))
        
        SFS += hist
        individuals = unique



    line_num = -1
    while (len(individuals) > 1) and (line_num > -len(lines)):
        line_num -= 1
        Ne_parent = (lines[line_num]).astype(np.int64)
        individuals2 = get_individuals2_new(Ne, Ne_parent, individuals)
        individuals2 = np.repeat(individuals2, leaf_counts, axis = 0)
        unique, leaf_counts = np.unique(individuals2, axis = 0,
                                                        return_counts = True)
        hist, bin_edges = np.histogram(leaf_counts,
                                       bins = np.arange(1, n + 2))

        SFS += hist
        individuals = unique
        Ne = Ne_parent

    # The first round of coalescence simulation ends when we get to the time
    # when the beneficial mmutation arose, and all the left over individuals
    # are WT. From this point on, the coalescence will be extremely slow.
    # Therefore, we will run the same kind of simulation until the individuals
    # disperse for L^2 / m / N. We speed up the simulation by recording the number
    # of generations between the coalescence events.
    left_individuals = len(individuals)
    branch_len = 0 # number of generations until first merging event
    extra_gen = 0 # extra run time before stopping the coalescent simulation.

    while left_individuals > 1 and extra_gen < int(L ** 2 / m / N):

        branch_len += 1
        extra_gen += 1

        individuals2 = get_parent_presweep_arr_new(individuals)
        individuals2 = np.repeat(individuals2, leaf_counts, axis = 0)

        unique, leaf_counts = np.unique(individuals2,
                                        axis = 0, return_counts = True)
        current_individuals_counts = len(unique)
        individuals2 = unique

        if left_individuals == current_individuals_counts:
            individuals = individuals2
        else:
            hist, bin_edges = np.histogram(leaf_counts * branch_len,
                                       bins = np.arange(1, n + 2))

            SFS += hist
            individuals = unique
            branch_len = 0
        left_individuals = len(individuals)
        
        
        
    # After the individuals disperse, we may ignore the spatial structure.
    # If there are more than sqrt(2 * N * L) individuals left, it is likely
    # to have more than 1 merging event in a single generation. Thus, we manually
    # draw parent for every individual and find if some of them are the same.
    # Once there are much smaller number of individuals left, it will take a long
    # time to coalesce. Thus, we draw T2 (time until the first coalescent) from
    # geometric prob. distribution. (This is found from prob. of choosing different
    # parent for every individual left.)
    
    while left_individuals > 1:
        T2 = random.exponential(
                N * L / ((left_individuals - 1) * left_individuals / 2))
        
        hist, bin_edges = np.histogram(leaf_counts,
                                       bins = np.arange(1, n + 2))
        SFS += hist * T2
        
        coal_inds = random.choice(range(left_individuals), 
                                  size = 2, replace = False)

        individuals[coal_inds[0]] = individuals[coal_inds[1]] 

        individuals2 = np.repeat(individuals, leaf_counts, axis = 0)

        unique, leaf_counts = np.unique(individuals2, 
                                        axis = 0, return_counts = True)
        individuals = unique
        left_individuals = len(individuals)
        # print(left_individuals)

    return SFS

def writeOutput(position, mutationCount, outputFileName):
    if path.exists(outputFileName) == False:
        output = open(outputFileName, "w")
        output.write("position\t" + "x\t" + "n\t" + "folded\n")
        output.close()
    output = open(outputFileName, "a")
    output.write(str(position) + "\t" + str(mutationCount) + "\t" + str(nbase) + "\t" + "0\n")
    output.close()

#recalculates the recombination rate at the new position
def recalcRecombination(position):
    relDistance = abs(mutationSite - position)
    genDistance = float(relDistance * r_per_base)
    newRecomb = 1 - (np.exp(-2 * genDistance)) 
    newRecomb *= 0.5
    return newRecomb

#updates the increment between loci
def updateStep(position):
    relDistance = abs(mutationSite - position)

    if relDistance < 10000:
        return 1000
    elif relDistance <= 100000:
        return 10000
    elif relDistance <= 1000000:
        return 100000
    else:
        return 1000000

def implicit_sim(lowerBound, upperBound, outputFileName):
    perBaseMutation = r_per_base * 10
    mutations = {}

    validLoci = []

    for x in range(lowerBound, upperBound + 1):
        validLoci.append(x)
                    
    theta = perBaseMutation * 2 * N
            
    for i in range(1, nbase):
        expectedValue = theta/i

        mutations[i] = np.random.binomial(len(validLoci), expectedValue) #[Key, value] where key is expected number of loci and value is number of mutations

    for mutationCount in mutations:
        for _ in range(mutations[mutationCount]):
            target = np.random.randint(0, len(validLoci) - 1)
            writeOutput(validLoci[target], mutationCount, outputFileName)

            #remove in O(1) time
            validLoci[target] = validLoci[len(validLoci) - 1]
            validLoci.pop()

def explicit_sim(left, right, outputFile):
    p = Pool(25)
        
    SFS = np.sum(p.map(runner, range(N_SFS)), axis = 0) / N_SFS
    SFS *= mutationRate
        
    SFS_List = SFS.tolist()

    zeroProbability = 1 - sum(SFS_List)
    SFS_List.append(zeroProbability)

    mutations = []
    for x in range(1, nbase + 1):
        mutations.append(x)
    mutations.append(0)
    
    resultListLeft = rand.choices(mutations, SFS_List, k = step)
    resultListRight = rand.choices(mutations, SFS_List, k = step)

    targetLociLeft = rand.sample(range(left, left + step), step)
    targetLociRight = rand.sample(range(right - step, right), step)

    for i in range(step):
        if resultListLeft[i] > 0:
            writeOutput(targetLociLeft[i], resultListLeft[i], outputFile)
        if resultListRight[i] > 0:
            writeOutput(targetLociRight[i], resultListRight[i], outputFile)

#abs(mutationSite - startIndx) * r_per_base >= 10 * s
if __name__ == '__main__':
    lo = int(mutationSite - ((10 * s) / r_per_base))
    hi = int(mutationSite + ((10 * s) / r_per_base))
    left = mutationSite
    right = mutationSite


    implicit_sim(1, lo, "output_implicit_lower.txt")
    implicit_sim(hi, endIndx, "output_implicit_upper.txt")
    while right < hi:
        step = updateStep(right)
        right += step
        left -= step
        processCount = 1
        r = recalcRecombination(right)

        processes = []
        for x in range(processCount):
            p = Process(target=explicit_sim, args=(left, right, "output_explicit_" + str(x) + ".txt",))
            processes.append(p)
        for process in processes:
            process.start()
        for process in processes:
            process.join()
        
