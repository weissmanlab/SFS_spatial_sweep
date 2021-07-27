# -*- coding: utf-8 -*-
"""
Created on Thu Jun 17 14:46:16 2021

@author: jim903
"""

import numpy as np
import random
import matplotlib.pyplot as plt
N = 2 * 10 ** 6
s = 0.05
N_sim = 40
nsample = 10 ** 3
T_after_fix = 0
r = 10 ** (-5)

n_sim = 0
SFS = np.zeros(nsample)



while n_sim < N_sim:
    n_selected = 1
    n_selected_series = [n_selected]
    while n_selected < N and n_selected > 0:
        n_selected = np.random.binomial(N, n_selected / N 
                                    + s * n_selected / N 
                                    * (1 - n_selected / N))
        n_selected_series.append(n_selected)
#    print(n_selected)
    if n_selected > 0:
        n_sim += 1
        print(n_sim)
        
        # coalescent simulation on a successful sweep data
        T_sweep = len(n_selected_series)
        t_after_fix = 0
        t = 0
        leaf_counts = [1 for _ in range(nsample)]
        n_mut_inds = nsample
        n_wt_inds = 0
        while t_after_fix < T_after_fix:
            t_after_fix += 1
            inds_mut_new = np.array([np.ones(n_mut_inds), np.random.randint(
                    N, size = n_mut_inds)]).T
            inds_mut_new_repeat = np.repeat(inds_mut_new, leaf_counts
                                            , axis = 0)
            unique, leaf_counts = np.unique(inds_mut_new_repeat, 
                                            return_counts = True, 
                                            axis = 0)
#            leaf_counts = np.append(leaf_counts_mut, leaf_counts_wt)
            hist, bin_edges = np.histogram(leaf_counts,
                                           bins = np.arange(1, nsample + 2))
            SFS += hist
            n_mut_inds = len(unique)
            n_wt_inds = 0
        # During the sweep, draw a number of recombination events from a Poisson
        # distribution with mean = var = Nr. 
        while t < T_sweep - 1:
            t += 1
            Ne = n_selected_series[-t - 1]
            Ne_old = n_selected_series[-t]

#            print(t)
#            n_recombine_wt = np.random.poisson(n_wt_inds * r)
#            n_recombine_mut = np.random.poisson(n_mut_inds * r)
            n_recombine_wt = sum(np.random.random(n_wt_inds) < r)
            n_recombine_mut = sum(np.random.random(n_mut_inds) < r)
            n_recombine = n_recombine_wt + n_recombine_mut
            
            n_new_mut = int(sum(np.random.choice(
                    np.append(np.zeros(N - Ne_old)
                    , np.ones(Ne_old))
                    , size = n_recombine, replace = False)))
            n_new_wt = n_recombine - n_new_mut
            n_mut_inds_post_rec = n_mut_inds - n_recombine_mut + n_new_mut
            n_wt_inds_post_rec = n_wt_inds - n_recombine_wt + n_new_wt
            
#            n_recombine = np.random.poisson(N * r)
#            
#            # instead of assigning zero or one for WT/mutant, we have a list 
#            # number, which initially is range(N) and elements with < Ne is mutants
#            labels = list(range(N))
#            for i in range(n_recombine):
#                recombining_inds = np.random.randint(N, size = 2)
#                labels[recombining_inds[0]] = recombining_inds[1]
#                labels[recombining_inds[1]] = recombining_inds[0]
#            n_mut_inds_post_rec = 0
#            n_wt_inds_post_rec = 0
#
#            for i in range(n_mut_inds):
#                if labels[i] < Ne_old:
#                    n_mut_inds_post_rec += 1
#                else:
#                    n_wt_inds_post_rec += 1
#            for j in range(n_wt_inds):
#                if labels[-j - 1] < Ne_old:
#                    n_mut_inds_post_rec += 1
#                else:
#                    n_wt_inds_post_rec += 1


            inds_mut_new = np.array([np.ones(n_mut_inds_post_rec), 
                                     np.random.randint(Ne, 
                                            size = n_mut_inds_post_rec)]).T

            inds_wt_new = np.array([np.zeros(n_wt_inds_post_rec), 
                                    np.random.randint(N - Ne, 
                                        size = n_wt_inds_post_rec)]).T
            inds_new = np.append(inds_mut_new, inds_wt_new, axis = 0)
#            random.shuffle(leaf_counts)
            inds_new_repeat = np.repeat(inds_new, 
                                        leaf_counts, axis = 0)
            unique, leaf_counts = np.unique(inds_new_repeat, 
                                    return_counts = True, axis = 0)

            hist, bin_edges = np.histogram(leaf_counts, 
                                           bins = np.arange(1, nsample + 2))
            SFS += hist
            n_inds = len(unique)
            n_mut_inds = int(np.sum(unique, axis = 0)[0])
            n_wt_inds = n_inds - n_mut_inds

#            inds_mut_new_repeat = np.repeat(inds_mut_new
#                                            , leaf_counts[:n_mut_inds_post_rec]
#                                            , axis = 0)
#            unique_mut, leaf_counts_mut = np.unique(inds_mut_new_repeat, 
#                                            return_counts = True)
#            n_mut_inds = len(unique_mut)
#            inds_wt_new_repeat = np.repeat(inds_wt_new
#                                           , leaf_counts[n_mut_inds_post_rec:]
#                                           , axis = 0)
#            unique_wt, leaf_counts_wt = np.unique(inds_wt_new_repeat, 
#                                                  return_counts = True)
#            n_wt_inds = len(unique_wt)
#            leaf_counts = np.append(leaf_counts_mut, leaf_counts_wt)
#            hist, bin_edges = np.histogram(leaf_counts, 
#                                           bins = np.arange(1, nsample + 2))
#            SFS += hist
            
        while n_inds > 1:
            individuals = np.random.randint(N, size = n_inds)
            T2 = np.random.exponential(
                N / ((n_inds - 1) * n_inds / 2))
        
            hist, bin_edges = np.histogram(leaf_counts,
                                       bins = np.arange(1, nsample + 2))
            SFS += hist * T2
        
            coal_inds = np.random.choice(range(n_inds), 
                                  size = 2, replace = False)

            individuals[coal_inds[0]] = individuals[coal_inds[1]] 

            individuals2 = np.repeat(individuals, leaf_counts, axis = 0)

            unique, leaf_counts = np.unique(individuals2, 
                                        axis = 0, return_counts = True)
            individuals = unique
            n_inds = len(individuals)

#            inds_wt_new = np.array([np.zeros(n_inds), 
#                                    np.random.randint(N, 
#                                        size = n_inds)]).T
#            inds_wt_new_repeat = np.repeat(inds_wt_new, leaf_counts, axis = 0)
#            unique, leaf_counts = np.unique(inds_wt_new_repeat, 
#                                            return_counts = True, axis = 0)
#            hist, bin_edges = np.histogram(leaf_counts,
#                                           bins = np.arange(1, nsample + 2))
#            SFS += hist
#            n_inds = len(unique)
            
            
SFS /= N_sim
SFS *= nsample

def moving_average(a, n = 3, start_smooth = 100):
    a_start = a[:start_smooth]
    a_end = a[start_smooth:]
    ret = np.cumsum(a_end, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return np.concatenate((a_start, ret[n - 1:] / n))

f = np.arange(1, nsample + 1) / nsample
plt.rc('text', usetex=True)
plt.rc('font', family='serif', size = 60, weight = 'bold')
plt.figure(figsize = (24, 18))
plt.xlabel(r'$f$', fontsize = 75)
plt.ylabel(r'$P(f)$', fontsize = 75)

plt.loglog(moving_average(f, 20, 100), moving_average(SFS, 20, 100), linewidth = 2)
plt.loglog(f, (1 + 2 * N * r) / f ** 2 / s, label = r'$P(f) = U_n(1 + 2Nr) / sf^2$')
plt.loglog(f, 2 * N / f, label = r'$P(f) = 2 N U_n /f$')
plt.legend(fontsize = 'medium', loc = 'upper right')
#plt.savefig('expected_SFS_well_mixed_N={}_Tfix={}_s={:.2f}_r={:.1e}.png'.format(N, T_after_fix, s, r))
#
#np.savetxt('expected_SFS_well_mixed_N={}_Tfix={}_s={:.2f}_r={:.1e}.txt'.format(N, T_after_fix, s, r), SFS)

