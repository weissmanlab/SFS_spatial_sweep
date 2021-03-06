'''
List of functions being used to create the backward time simulation for 2-D sweeps
Tracks migration and parent lineage as they coalesce back in time 
'''

import numpy as np
from multiprocessing import Pool
import sys
from numpy import random

'''
L = 200 # number of demes in 1 Direction. Total demes = L*L
N = 200 # deme capacity
s = 0.05 # selection coef
m = 0.25 # migration rate
r = 0 # recombination rate
tfinal = 1721 # sweep time
nbase = 100# sample size
N_SFS = 4 # number of coalescent simulation we run.
T_after_fix = 0 # number of generations between fixation and sampling
n_forward = 1 # forward time simulation number
l0 = 100
'''
def safe_divide(a, b, val=0):
    return np.divide(a, b, out=np.full_like(a, val), where=b != 0)
    
def get_parent_presweep_arr_new(inds, N, m, L):
    '''
    Function picks up a particular individiual, allows it to randomly migrate and tracks it to the parent till before the sweep happened
    
    Input Arguement: inds (created in main function runner from the results of the forward simulation)
    inds = [type of mutation (0 for wt), which deme number, individual within the deme] per row and # of rows is how many individuals left tp sample
    deme_arr = 1-D array of size L*L
    mut_type = 1 for neutral mutation, 0 for wt
    N = number of indovoduals in a deme
    m = migration rate
    L = number of demes in one direction


    The addition and subtraction of indexes is to do migration in 2-D space in a 1-D array. 
    For index i:
    Top = (i-L)%(L*L)
    Bottom = (i+L)%(L*)
    Right = i + [-(L-1) if (i+1)%L ==0 else 1][0]
    Left = i + [(L-1) if (i)%L ==0 else -1][0]
    This takes care of edge cases also
    '''
    
    mut_types, deme_arr, ind_in_deme_arr = inds.T
    
    ##Create new arrays to track changes after the individual is tracked per generational step
    mut_types_new = (np.zeros_like(mut_types)).astype(np.int64)
    deme_arr_new = np.zeros_like(deme_arr)  ##Where the mutation goes after migration
    ind_in_deme_arr_new = np.zeros_like(ind_in_deme_arr)

    len_inds = len(inds)
    which_deme_rand = random.random(len_inds)
    #array of random numbers used to determine which deme the parent is in. Its an array as big as the number of demes so we can track all individuals .
    choice_rand = random.random(len_inds)  
    #random numbers used to determine which individual to pick in each deme.Its an array as big as the number of demes so we can track all individuals .
    
    '''Creating Cummulative Probablities of each direction'''
    left_range_prob = m / 4. # prob of going to the left deme
    right_range_prob = 2*m / 4. # prob of going to the right deme
    top_range_prob = 3*m / 4. # prob of going to the upper deme
    bottom_range_prob = 4*m / 4. # prob of going to the bottom deme
    mid_range_prob = 1. - m # Prob of remaining in the same deme
    # Sum of these 5 probablities is 1

    '''
    Monte Carlo like method of choosing which deme the migration happens to.
    Example: Left idx is an array of all indexes of deme_arr that meet the condition for migrating left. 
    For all these indexes, we update the values into a new array using migration probablities (explained at the end)
    Repeat for right, top, bottom, mid
    '''

    '''The location of individuals where probablty to move left is found is in left_idx. For those indivduals, move the location. Repeat for others'''
    left_idxs = np.where(which_deme_rand < left_range_prob)[0]
    deme_arr_new[left_idxs] = ([(deme_arr[i] + L-1) if deme_arr[i]%L == 0 else (deme_arr[i]-1) for i in left_idxs])
      
    right_idxs = np.where(np.logical_and(
        which_deme_rand > left_range_prob,
        which_deme_rand < right_range_prob))[0]
    deme_arr_new[right_idxs] = ([(deme_arr[i] - (L-1)) if (deme_arr[i]+1)%L == 0 else (deme_arr[i]+1) for i in right_idxs])

    top_idxs = np.where(np.logical_and(
        which_deme_rand > right_range_prob,
        which_deme_rand < top_range_prob))[0]
    deme_arr_new[top_idxs] = ((deme_arr[top_idxs]-L)%(L*L)).astype(np.int64)

    bottom_idxs = np.where(np.logical_and(
        which_deme_rand > top_range_prob,
        which_deme_rand < bottom_range_prob))[0]
    deme_arr_new[bottom_idxs] = ((deme_arr[bottom_idxs]+L)%(L*L)).astype(np.int64)

    mid_idxs = np.where(which_deme_rand > bottom_range_prob)[0]
    deme_arr_new[mid_idxs] = (deme_arr[mid_idxs]).astype(np.int64)

    ind_in_deme_arr_new = (np.floor(choice_rand * N)).astype(np.int64)
    inds2 = np.vstack((mut_types_new,
                              deme_arr_new,
                              ind_in_deme_arr_new)).T
    return inds2
    
        
def get_individuals2_new(Ne, Ne_parent, individuals, N, m, L):
    '''
    for each bucket, choose between neighboring/own buckets with relative
    probabilities [m/4 for each neighbor and 1-m for being in the same bucket.
    
    Input Arguements: Ne, Ne_Parents (Arrays of populations), individuals which is same as inds previously and has three values (mutation, which deme, number within deme)
    Ne = Array of mutants so we create the array of wildtypes within the function. As we draw arrows backwars in time, mutations only interact with mutations.             
    deme_arr = 1-D array of size L*L
    Mutation = 1, 0 for WT
    left, right, top, bottom are the neighbors. Mid is the same deme with no migration/probablity 
    N = number of individuals in a deme 
    m = migration rate
    L = number of demes in one direction
    
    
    Migration patterns from a given index i:
    Top = (i-L)%(L*L)
    Bottom = (i+L)%(L*)
    Right = i + [-(L-1) if (i+1)%L ==0 else 1][0]
    Left = i + [(L-1) if (i)%L ==0 else -1][0]
    
    This takes care of edge cases also
    '''
    
    '''Creating the array of wildtypes since we had mutants'''
    Nwt = (N - Ne).astype(np.int64)   ##Since forward simulation only tracked mutants
    Nwt_parent = (N - Ne_parent).astype(np.int64)    
    mut_types, deme_arr, ind_in_deme_arr = individuals.T
    #print(Ne_parent)
    #print(Nwt_parent)

    #Create new arrays to track changes after the individual is tracked per generational step
    ind_in_deme_arr_next = np.zeros_like(ind_in_deme_arr)
    len_inds = len(deme_arr)
    which_parent_rand = random.random(len_inds) # to choose btw left/mid/right/top/bottom
    choice_rand = random.random(len_inds) # used for index within the deme
    
    '''
    For mutant first, find the parent's deme and then its index inside the deme
    Perform for the entire deme list in one step.
    '''
    mut_idxs, deme_arr_next, mut_types_next = track_individual(Ne_parent, choice_rand, which_parent_rand, 1, individuals, N, m, L)
    ind_in_deme_arr_next[mut_idxs] = (np.floor(choice_rand[mut_idxs] * np.take(Ne_parent, deme_arr_next[mut_idxs]))).astype(np.int64)

    '''
    Next for Wildtype find the parent's deme and then its index inside the deme
    Do for the entire array at the same time 
    '''
    #wt_idxs, deme_arr_next, mut_types_next = track_individual(Nwt_parent, choice_rand, which_parent_rand, 0, individuals, N, m, L)
    #ind_in_deme_arr_next[wt_idxs] = (np.floor(choice_rand[wt_idxs] * np.take(Nwt_parent, deme_arr_next[wt_idxs]))).astype(np.int64)

    ###Recreate the data structure we had for passing into function
    individuals2 = np.vstack((mut_types_next, deme_arr_next, ind_in_deme_arr_next)).T
    
    del deme_arr_next
    del deme_arr    
    del mut_types_next
    del which_parent_rand
    del choice_rand
    return individuals2
    
    
def track_individual(parent_array, choice_rand, which_parent_rand, mutation_val, individuals, N, m, L):
    '''
    parent_array = the array of parent values (coud be wildtype or mutant)
    choice_rand, which_parent_rand = random probablities created for makinf choices
    mutation_val = value to compare nearest neighbors. Can only coalesce with the same type.
    1 if mutant, 0 if wildtype
    individuals: the structure of data that is created.
    N = number of individuals in a deme
    m = migration rate
    L = number of demes in one direction
    '''
    mut_types, deme_arr, ind_in_deme_arr = individuals.T
    deme_arr = (deme_arr).astype(np.int64)
    mut_types_next = np.ones_like(mut_types)
    deme_arr_next = np.zeros_like(deme_arr)
    ind_in_deme_arr_next = np.zeros_like(ind_in_deme_arr)
    len_inds = len(deme_arr)
    
    '''Creating the probablities of moving to the nearest neigbor if it is of same type. The probablity is weighted by the number of mutants/wiltypes in the neighborinf deme'''
    left_parent_prob = m/4 *np.take(parent_array,[(deme_arr[i]+(L-1)) if (deme_arr[i])%L == 0 else (deme_arr[i]-1) for i in range(len(deme_arr))])
    right_parent_prob = m/4 *np.take(parent_array,[(deme_arr[i]-(L-1)) if (deme_arr[i]+1)%L == 0 else (deme_arr[i]+1) for i in range(len(deme_arr))])    
    top_parent_prob = m / 4 * np.take(parent_array, ((deme_arr-L)%(L*L)))
    bottom_parent_prob = m/4 * np.take(parent_array, ((deme_arr+L)%(L*L)))
    mid_parent_prob = (1 - m) * np.take(parent_array, deme_arr)
    total_prob = (left_parent_prob + right_parent_prob + top_parent_prob + bottom_parent_prob + mid_parent_prob)
    #print(total_prob,'\n')
    
    '''Set the cumulative probability and normalise'''
    left_parent_prob_cumulative = safe_divide(left_parent_prob, total_prob)
    #print(left_parent_prob_cumulative,'\n')
    right_parent_prob_cumulative = safe_divide(left_parent_prob  + right_parent_prob, total_prob)
    #print(right_parent_prob_cumulative,'\n')
    top_parent_prob_cumulative = safe_divide(left_parent_prob  + right_parent_prob+ top_parent_prob, total_prob)
    #print(top_parent_prob_cumulative,'\n')
    bottom_parent_prob_cumulative = safe_divide(left_parent_prob  + right_parent_prob + top_parent_prob + bottom_parent_prob, total_prob)
    #print(bottom_parent_prob_cumulative,'\n')
    #mid_parent_prob_cumulative = 1 - bottom_parent_prob_cumulative

    '''The location of individuals where probablty to move left is found is in left_idx. For those indivduals, move the location. Repeat for others'''
    left_parent_idxs = np.where(np.logical_and(
        which_parent_rand < left_parent_prob_cumulative,
        mut_types_next == mutation_val))[0]
    deme_arr_next[left_parent_idxs] = ([(deme_arr[i] + L-1) if deme_arr[i]%L == 0 else (deme_arr[i]-1) for i in left_parent_idxs])
    #print(left_parent_idxs)

    right_parent_idxs = np.where(np.logical_and.reduce((
        which_parent_rand > left_parent_prob_cumulative,
        which_parent_rand < right_parent_prob_cumulative,
        mut_types_next == mutation_val)))[0]
    deme_arr_next[right_parent_idxs] = ([(deme_arr[i] - (L-1)) if (deme_arr[i]+1)%L == 0 else (deme_arr[i]+1) for i in right_parent_idxs])
    #print(right_parent_idxs)    
    
    top_parent_idxs = np.where(np.logical_and.reduce((
        which_parent_rand > right_parent_prob_cumulative,
        which_parent_rand < top_parent_prob_cumulative,
        mut_types_next == mutation_val)))[0]
    deme_arr_next[top_parent_idxs] = (((deme_arr[top_parent_idxs]+L)%(L*L))).astype(np.int64)
    #print(top_parent_idxs)        
        
    bottom_parent_idxs = np.where(np.logical_and.reduce((
        which_parent_rand > top_parent_prob_cumulative,
        which_parent_rand < bottom_parent_prob_cumulative,
        mut_types_next == mutation_val)))[0]
    deme_arr_next[bottom_parent_idxs] = (((deme_arr[bottom_parent_idxs]+L)%(L*L))).astype(np.int64)
    #print(bottom_parent_idxs)    
    
    mid_parent_idxs = np.where(np.logical_and(
        which_parent_rand > bottom_parent_prob_cumulative,
        mut_types_next == mutation_val))[0]
    deme_arr_next[mid_parent_idxs] = (deme_arr[mid_parent_idxs]).astype(np.int64)
    #print(mid_parent_idxs)    
    
    given_idxs = np.concatenate((left_parent_idxs, right_parent_idxs, top_parent_idxs, bottom_parent_idxs, mid_parent_idxs))
    #print(len(given_idxs))    
    
    
    return given_idxs, deme_arr_next, mut_types_next


def sample_data(Ne, n, N):
    '''
    Pick random deme locations for as many individuals as we want to sample and what the index within a deme is 
    Currently, uniform probablity distributions
    '''
    individuals = [] # format will be [mut_type, deme index, individual index (inside the deme)]
    if n < round(sum(Ne)):   ##If sample size is less than the total number of mutants 
        individuals_location = random.choice(np.arange(0, round(sum(Ne))), size = n, replace = False)

    else:   ##If sample size is equal or more than mutants
        individuals_location = np.arange(0, round(sum(Ne)))
        n = sum(Ne)
    
    ind_inside_deme = np.mod(individuals_location, N)
    deme_ind = (individuals_location - ind_inside_deme) // N

    ###Adding mutants to the data structure
    for k in range(n):  
        # 1 is for having beneficial mutation
        individuals.append([1., deme_ind[k], ind_inside_deme[k]])
        
    individuals = np.array(individuals)
    return individuals
