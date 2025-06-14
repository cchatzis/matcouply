# MIT License: Copyright (c) 2022, Marie Roald.
# See the LICENSE file in the root directory for full license text.

import math
from copy import copy
from unittest.mock import patch

import numpy as np
import pytest
import scipy.stats as stats
import tensorly as tl
from tensorly.testing import assert_array_equal

from matcouply import penalties
from matcouply._utils import get_svd
from matcouply.testing import (
    BaseTestFactorMatricesPenalty,
    BaseTestFactorMatrixPenalty,
    BaseTestRowVectorPenalty,
    MixinTestHardConstraint,
    assert_allclose,
)

from .utils import RTOL_SCALE  # TODO: Consider if this should be changed


def test_row_vector_penalty_forwards_updates_correctly(rng, random_matrix, random_matrices):
    class BetweenZeroAndOneConstraint(penalties.RowVectorPenalty):
        def factor_matrix_row_update(self, factor_matrix_row, feasibility_penalty, aux_row):
            return tl.clip(factor_matrix_row, 0, 1)

        def penalty(self, x):
            return 0

    penalty = BetweenZeroAndOneConstraint()
    updated_factor_matrix = penalty.factor_matrix_update(random_matrix, 1, random_matrix)  # last input is ignored

    assert tl.all(updated_factor_matrix >= 0)
    assert tl.all(updated_factor_matrix <= 1)

    updated_factor_matrices = penalty.factor_matrices_update(
        random_matrices, np.ones(len(random_matrices)), random_matrices
    )  # last input is ignored
    for factor_matrix in updated_factor_matrices:
        assert tl.all(factor_matrix >= 0)
        assert tl.all(factor_matrix <= 1)


def test_matrix_penalty_forwards_updates_correctly(rng, random_matrices):
    class BetweenZeroAndOneConstraint(penalties.MatrixPenalty):
        def factor_matrix_update(self, factor_matrix, feasibility_penalty, aux_row):
            return tl.clip(factor_matrix, 0, 1)

        def penalty(self, x):
            return 0

    penalty = BetweenZeroAndOneConstraint()
    updated_factor_matrices = penalty.factor_matrices_update(
        random_matrices, np.ones(len(random_matrices)), random_matrices
    )  # last input is ignored
    for factor_matrix in updated_factor_matrices:
        assert tl.all(factor_matrix >= 0)
        assert tl.all(factor_matrix <= 1)


class TestL1Penalty(BaseTestRowVectorPenalty):
    PenaltyType = penalties.L1Penalty
    penalty_default_kwargs = {"reg_strength": 1}

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_row_update_invariant_point(self, non_negativity):
        invariant_matrix_row = tl.zeros((1, 4))
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrix_row_update(invariant_matrix_row, 10, None)
        assert_allclose(invariant_matrix_row, out)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrix_update_invariant_point(self, non_negativity):
        invariant_matrix = tl.zeros((10, 3))
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrix_update(invariant_matrix, 10, None)
        assert_allclose(invariant_matrix, out)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrices_update_invariant_point(self, non_negativity):
        invariant_matrices = [tl.zeros((10, 3)) for i in range(5)]
        feasibility_penalties = [10] * len(invariant_matrices)
        auxes = [None] * len(invariant_matrices)
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrices_update(invariant_matrices, feasibility_penalties, auxes)
        for invariant_matrix, out_matrix in zip(invariant_matrices, out):
            assert_allclose(invariant_matrix, out_matrix)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_row_update_reduces_penalty(self, random_row, non_negativity):
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        initial_penalty = l1_penalty.penalty(random_row)
        out = l1_penalty.factor_matrix_row_update(random_row, 10, None)
        assert l1_penalty.penalty(out) <= initial_penalty

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrix_update_reduces_penalty(self, random_matrix, non_negativity):
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        initial_penalty = l1_penalty.penalty(random_matrix)
        out = l1_penalty.factor_matrix_update(random_matrix, 10, None)
        assert l1_penalty.penalty(out) <= initial_penalty

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrices_update_reduces_penalty(self, random_matrices, non_negativity):
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)
        feasibility_penalties = [10] * len(random_matrices)
        auxes = [None] * len(random_matrices)
        initial_penalty = l1_penalty.penalty(random_matrices)
        out = l1_penalty.factor_matrices_update(random_matrices, feasibility_penalties, auxes)
        assert l1_penalty.penalty(out) <= initial_penalty

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_row_update_changes_input(self, random_row, non_negativity):
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrix_row_update(random_row, 10, None)
        assert not np.allclose(out, random_row)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrix_update_changes_input(self, random_matrix, non_negativity):
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrix_update(random_matrix, 10, None)
        assert not np.allclose(out, random_matrix)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrices_update_changes_input(self, random_matrices, non_negativity):
        feasibility_penalties = [10] * len(random_matrices)
        auxes = [None] * len(random_matrices)
        l1_penalty = penalties.L1Penalty(0.1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrices_update(random_matrices, feasibility_penalties, auxes)
        for random_matrix, out_matrix in zip(random_matrices, out):
            assert not np.allclose(random_matrix, out_matrix)

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_factor_matrix_update_sets_small_weights_to_zero(self, random_matrix, non_negativity):
        random_matrix /= tl.abs(random_matrix).max()
        feasibility_penalty = 1
        aux = None
        l1_penalty = penalties.L1Penalty(1, non_negativity=non_negativity)

        out = l1_penalty.factor_matrix_update(random_matrix, feasibility_penalty, aux)
        assert_allclose(out, 0)

    def test_non_negativity_sets_negative_values_to_zero(self):
        negative_matrix = tl.ones((30, 5)) * (-100)
        feasibility_penalty = 1
        aux = None
        l1_penalty = penalties.L1Penalty(1, non_negativity=True)

        out = l1_penalty.factor_matrix_update(negative_matrix, feasibility_penalty, aux)
        assert_array_equal(out, 0)

    def test_penalty(self, random_ragged_cmf):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        l1_penalty = self.PenaltyType(reg_strength=1)
        assert l1_penalty.penalty(A) == pytest.approx(tl.sum(tl.abs(A)))
        assert l1_penalty.penalty(B_is) == pytest.approx(sum(tl.sum(tl.abs(B_i)) for B_i in B_is))
        assert l1_penalty.penalty(C) == pytest.approx(tl.sum(tl.abs(C)))

        l1_penalty = self.PenaltyType(reg_strength=2)
        assert l1_penalty.penalty(A) == pytest.approx(2 * tl.sum(tl.abs(A)))
        assert l1_penalty.penalty(B_is) == pytest.approx(2 * sum(tl.sum(tl.abs(B_i)) for B_i in B_is))
        assert l1_penalty.penalty(C) == pytest.approx(2 * tl.sum(tl.abs(C)))

        l1_penalty = self.PenaltyType(reg_strength=0)
        assert l1_penalty.penalty(A) == 0
        assert l1_penalty.penalty(B_is) == 0
        assert l1_penalty.penalty(C) == 0

        with pytest.raises(ValueError):
            l1_penalty = self.PenaltyType(reg_strength=-1)


class TestBox(MixinTestHardConstraint, BaseTestRowVectorPenalty):
    PenaltyType = penalties.Box
    penalty_default_kwargs = {"min_val": 0, "max_val": 1}

    def get_invariant_row(self, rng, n_columns):
        invariant_row = tl.tensor(rng.uniform(size=(1, n_columns), low=0, high=1))
        return invariant_row

    def get_non_invariant_row(self, rng, n_columns):
        random_row = tl.tensor(rng.uniform(size=(1, n_columns)))
        random_row[0] += 100
        return random_row


class TestL2BallConstraint(MixinTestHardConstraint, BaseTestFactorMatrixPenalty):
    PenaltyType = penalties.L2Ball
    penalty_default_kwargs = {"norm_bound": 1}

    def get_invariant_matrix(self, rng, shape):
        random_matrix = tl.tensor(rng.random_sample(shape))
        return random_matrix / math.sqrt(shape[0])

    def get_non_invariant_matrix(self, rng, shape):
        random_matrix = tl.tensor(rng.random_sample(shape) + 10)
        return 10 + random_matrix / math.sqrt(shape[0])

    def test_input_is_checked(self):
        with pytest.raises(ValueError):
            self.PenaltyType(norm_bound=0)
        with pytest.raises(ValueError):
            self.PenaltyType(norm_bound=-1)

        self.PenaltyType(norm_bound=0.1)

    def test_non_negativity_sets_negative_values_to_zero(self):
        negative_matrix = tl.ones((30, 5)) * (-100)
        feasibility_penalty = 1
        aux = None
        penalty = self.PenaltyType(1, non_negativity=True)

        out = penalty.factor_matrix_update(negative_matrix, feasibility_penalty, aux)
        assert_array_equal(out, 0)


class TestUnitSimplex(MixinTestHardConstraint, BaseTestFactorMatrixPenalty):
    PenaltyType = penalties.UnitSimplex
    rtol = 1e-5 * RTOL_SCALE
    atol = 1e-8

    def get_invariant_matrix(self, rng, shape):
        random_matrix = tl.tensor(rng.uniform(size=shape))
        col_sum = tl.sum(random_matrix, axis=0)
        return random_matrix / col_sum

    def get_non_invariant_matrix(self, rng, shape):
        random_matrix = tl.tensor(rng.uniform(size=shape))
        col_sum = tl.sum(random_matrix, axis=0)
        return 10 + random_matrix / col_sum


class TestGeneralizedL2Penalty(BaseTestFactorMatrixPenalty):
    PenaltyType = penalties.GeneralizedL2Penalty
    n_rows = 50
    min_rows = n_rows
    max_rows = n_rows

    norm_matrix1 = 2 * np.eye(n_rows // 2) - np.eye(n_rows // 2, k=-1) - np.eye(n_rows // 2, k=1)
    norm_matrix1[0, 0] = 1
    norm_matrix1[-1, -1] = 1

    norm_matrix2 = 2 * np.eye(n_rows // 2) - np.eye(n_rows // 2, k=-1) - np.eye(n_rows // 2, k=1)
    norm_matrix2[0, 0] = 1
    norm_matrix2[-1, -1] = 1

    zeros_matrix = np.zeros((n_rows // 2, n_rows // 2))

    # fmt: off
    norm_matrix = tl.tensor(np.block([
        [norm_matrix1, zeros_matrix],
        [zeros_matrix, norm_matrix2]
    ]))
    # fmt: on
    penalty_default_kwargs = {"norm_matrix": norm_matrix}

    def get_invariant_matrix(self, rng, shape):
        if shape[0] != self.n_rows:
            raise ValueError("Shape must align with the norm matrix")
        return tl.ones(shape)

    def get_non_invariant_matrix(self, rng, shape):
        return tl.tensor(rng.random_sample(size=shape))

    def test_penalty(self, random_matrices):
        B01 = random_matrices[0][: self.n_rows // 2]
        B02 = random_matrices[0][self.n_rows // 2 :]
        penalty_manual = tl.sum((B01[1:] - B01[:-1]) ** 2) + tl.sum((B02[1:] - B02[:-1]) ** 2)

        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        assert penalty.penalty(random_matrices[0]) == pytest.approx(penalty_manual)

    def test_update_is_correct_on_example(self, rng):
        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        X = tl.tensor(rng.random_sample(size=(self.n_rows, 10)))
        feasibility_penalty = 5
        Y = penalty.factor_matrix_update(X, feasibility_penalty, None)

        aug_norm_matrix = self.norm_matrix + 0.5 * feasibility_penalty * tl.eye(self.n_rows)
        assert_allclose(Y, tl.solve(aug_norm_matrix, 2.5 * X), rtol=RTOL_SCALE * 1e-7)


@pytest.mark.skipif(
    tl.get_backend() != "numpy",
    reason="The TV penalty is only supported with the Numpy backend due to C dependencies",
)
class TestTotalVariationPenalty(BaseTestFactorMatrixPenalty):
    PenaltyType = penalties.TotalVariationPenalty
    penalty_default_kwargs = {"reg_strength": 1, "l1_strength": 0}
    min_rows = 3

    def get_invariant_matrix(self, rng, shape):
        return tl.zeros(shape)

    def get_non_invariant_matrix(self, rng, shape):
        return tl.tensor(rng.uniform(size=shape))

    def test_penalty(self, rng):
        shape = rng.randint(3, 20), rng.randint(3, 20)
        # shape = 10, 10
        tv_penalty = self.PenaltyType(reg_strength=1, l1_strength=1)

        # Penalty is 0 if input is 0
        assert tv_penalty.penalty(tl.zeros(shape)) == pytest.approx(0)

        # Penalty is sum(abs(X)) if X is only ones
        X1 = tl.ones(shape)
        assert tv_penalty.penalty(X1) == pytest.approx(tl.sum(tl.abs(X1)))

        # Penalty is sum(abs(X))+2 if X is only ones except for one non-boundary entry (not index 0 or -1) in one
        # column which is zero
        X2 = tl.ones(shape)
        X2[shape[0] // 2, shape[1] // 2] = 0
        print("X2", X2)
        assert tv_penalty.penalty(X2) == pytest.approx(tl.sum(tl.abs(X2)) + 2)

        # Penalty is sum(abs(X))+1 if X is only ones except for one boundary entry (index 0 or -1) in one column
        X3 = tl.ones(shape)
        X3[0, shape[1] // 2] = 0
        assert tv_penalty.penalty(X3) == pytest.approx(tl.sum(tl.abs(X3)) + 1)

        # Penalty is sum(abs(X))+n_cols if all columns of x is on form [0, 0, 0, 0, 1, 1, 1, 1]
        X4 = tl.ones(shape)
        X4[: shape[0] // 2] = 0
        assert tv_penalty.penalty(X4) == pytest.approx(tl.sum(tl.abs(X4)) + shape[1])

        # Penalty is zero for constant columns if l1_strength is 0
        tv_penalty_no_l1 = self.PenaltyType(reg_strength=1, l1_strength=0)
        X_constant_columns = rng.uniform(shape[0]) * tl.ones(shape)
        assert tv_penalty_no_l1.penalty(X_constant_columns) == pytest.approx(0)

    def test_input_is_checked(self):
        with pytest.raises(ValueError):
            tv_penalty = self.PenaltyType(reg_strength=0, l1_strength=1)
        with pytest.raises(ValueError):
            tv_penalty = self.PenaltyType(reg_strength=-1, l1_strength=1)
        with pytest.raises(ValueError):
            tv_penalty = self.PenaltyType(reg_strength=1, l1_strength=-1)

        tv_penalty = self.PenaltyType(reg_strength=1, l1_strength=0)

        HAS_TV = penalties.HAS_TV
        penalties.HAS_TV = False
        with pytest.raises(ModuleNotFoundError):
            tv_penalty = self.PenaltyType(reg_strength=1, l1_strength=0)  # pragma: noqa
        penalties.HAS_TV = HAS_TV

    def test_l1_is_applied(self):
        shape = (10, 3)
        normally_invariant_matrix = tl.ones(shape)
        penalty_without_l1 = self.PenaltyType(reg_strength=1, l1_strength=0)
        assert_allclose(
            normally_invariant_matrix, penalty_without_l1.factor_matrix_update(normally_invariant_matrix, 1, None)
        )

        penalty_with_l1 = self.PenaltyType(reg_strength=1, l1_strength=1000)
        assert_allclose(tl.zeros(shape), penalty_with_l1.factor_matrix_update(normally_invariant_matrix, 1, None))


class TestNonNegativity(MixinTestHardConstraint, BaseTestRowVectorPenalty):
    PenaltyType = penalties.NonNegativity

    def get_invariant_row(self, rng, n_columns):
        random_row = tl.tensor(rng.uniform(size=(1, n_columns)))
        return random_row

    def get_non_invariant_row(self, rng, n_columns):
        random_row = tl.tensor(rng.uniform(size=(1, n_columns)))
        random_row[0] = -1
        return random_row


@pytest.mark.skipif(
    tl.get_backend() != "numpy",
    reason=(
        "The unimodality constraint is only supported with the Numpy backend due"
        " to the serial nature of the unimodal regression algorithm and the implementation's use of Numba"
    ),
)
class TestUnimodality(MixinTestHardConstraint, BaseTestFactorMatrixPenalty):
    PenaltyType = penalties.Unimodality
    penalty_default_kwargs = {}
    min_rows = 3

    def get_invariant_matrix(self, rng, shape):
        matrix = tl.zeros(shape)
        I, J = shape
        t = np.linspace(-10, 10, I)
        for j in range(J):
            sigma = rng.uniform(0.5, 1)
            mu = rng.uniform(-5, 5)
            matrix[:, j] = stats.norm.pdf(t, loc=mu, scale=sigma)
        return matrix

    def get_non_invariant_matrix(self, rng, shape):
        # There are at least 3 rows
        M = rng.uniform(size=shape)
        M[1, :] = -1  # M is positive, so setting the second element to -1 makes it impossible for it to be unimodal
        return M

    @pytest.mark.parametrize("non_negativity", [True, False])
    def test_non_negativity_used(self, non_invariant_matrix, non_negativity):
        # Check that non_negativity is used
        with patch("matcouply.penalties.unimodal_regression") as mock:
            unimodality_constaint = self.PenaltyType(non_negativity=non_negativity)
            unimodality_constaint.factor_matrix_update(non_invariant_matrix, 1, None)
            mock.assert_called_once_with(non_invariant_matrix, non_negativity=non_negativity)


def test_unimodality_skipped():
    with patch("matcouply.decomposition.tensorly.get_backend", return_value="pytorch"):
        with pytest.raises(RuntimeError):
            penalties.Unimodality()

        with pytest.raises(RuntimeError):
            penalties.Unimodality(non_negativity=True)


class TestParafac2(BaseTestFactorMatricesPenalty):
    PenaltyType = penalties.Parafac2
    min_matrices = 2  # PARAFAC2 constraint does not make sense for only one matrix
    # The factor matrix needs at least as many rows as columns for PARAFAC2
    max_columns = 5
    min_rows = 5

    def test_projection_improves_with_num_iterations(self, random_rank5_ragged_cmf, rng):
        cmf, shapes, rank = random_rank5_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()
        feasibility_penalties = tl.tensor(rng.uniform(2, 3, size=len(B_is)))

        pf2_1it = self.PenaltyType(n_iter=1)
        pf2_5it = self.PenaltyType(n_iter=5)

        auxes_1it = pf2_1it.init_aux(matrices, rank, 1, rng)
        auxes_5it = ([tl.copy(Pi) for Pi in auxes_1it[0]], tl.copy(auxes_1it[1]))

        proj_1it = pf2_1it.factor_matrices_update(B_is, feasibility_penalties, auxes_1it)
        proj_5it = pf2_5it.factor_matrices_update(B_is, feasibility_penalties, auxes_5it)

        error_1it = sum(tl.sum(err**2) for err in pf2_1it.subtract_from_auxes(proj_1it, B_is))
        error_5it = sum(tl.sum(err**2) for err in pf2_5it.subtract_from_auxes(proj_5it, B_is))

        assert error_5it < error_1it

    def test_factor_matrices_update_invariant_point(self, rng):
        svd = get_svd("truncated_svd")

        # Construct invariant matrices in NumPy for double precision
        def random_orthogonal(size):
            X = rng.standard_normal(size)
            return np.linalg.qr(X)[0]

        deltaB = rng.standard_normal((3, 3))
        P_is = [random_orthogonal((10, 3)) for _ in range(5)]
        invariant_matrices = [P_i @ deltaB for P_i in P_is]

        deltaB = tl.tensor(deltaB)
        P_is = [tl.tensor(P_i) for P_i in P_is]
        invariant_matrices = [tl.tensor(B_i) for B_i in invariant_matrices]
        auxes = P_is, deltaB

        feasibility_penalties = [10] * len(invariant_matrices)
        pf2_penalty = penalties.Parafac2()

        out = pf2_penalty.factor_matrices_update(invariant_matrices, feasibility_penalties, auxes)
        assert_allclose(deltaB, out[1], rtol=1e-6 * RTOL_SCALE)
        for P_i, out_matrix in zip(P_is, out[0]):
            if tl.get_backend() == "numpy":
                rtol = 1e-6
            else:
                # This seems to be very unstable with single precision, one of the entries in one of the P_is is often too large
                rtol = 1e-2

            assert_allclose(P_i, out_matrix, rtol=rtol, err_msg="This can be somewhat unstable with single precision")

    def test_not_updating_basis_matrices_works(self, rng):
        svd = get_svd("truncated_svd")
        deltaB = tl.tensor(rng.standard_normal((3, 3)))
        P_is = [svd(tl.tensor(rng.standard_normal(size=(10, 3))), n_eigenvecs=3)[0] for _ in range(5)]
        wrong_P_is = [svd(tl.tensor(rng.standard_normal(size=(10, 3))), n_eigenvecs=3)[0] for _ in range(5)]
        B_is = [tl.matmul(P_i, deltaB) for P_i in P_is]
        auxes = wrong_P_is, deltaB

        feasibility_penalties = [10] * len(B_is)
        pf2_penalty = penalties.Parafac2(update_basis_matrices=False)

        out = pf2_penalty.factor_matrices_update(B_is, feasibility_penalties, auxes)
        assert not tl.all(deltaB == out[1])
        for P_i, out_matrix in zip(wrong_P_is, out[0]):
            assert_allclose(P_i, out_matrix)

    def test_not_updating_coordinate_matrix_works(self, rng):
        svd = get_svd("truncated_svd")
        deltaB = tl.tensor(rng.standard_normal((3, 3)))
        wrong_deltaB = tl.tensor(rng.standard_normal((3, 3)))
        P_is = [svd(tl.tensor(rng.standard_normal(size=(10, 3))), n_eigenvecs=3)[0] for _ in range(5)]
        B_is = [tl.matmul(P_i, deltaB) for P_i in P_is]
        auxes = P_is, wrong_deltaB

        feasibility_penalties = [10] * len(B_is)
        pf2_penalty = penalties.Parafac2(update_coordinate_matrix=False)
        out = pf2_penalty.factor_matrices_update(B_is, feasibility_penalties, auxes)
        assert_allclose(wrong_deltaB, out[1])
        for P_i, out_matrix in zip(P_is, out[0]):
            assert not tl.all(P_i == out_matrix)

    def test_factor_matrices_update_reduces_penalty(self, rng, random_matrices):
        svd = get_svd("truncated_svd")

        shapes = [tl.shape(matrix) for matrix in random_matrices]
        rank = shapes[0][1]
        deltaB = tl.tensor(rng.standard_normal((rank, rank)))
        P_is = [svd(tl.tensor(rng.standard_normal(size=shape)), n_eigenvecs=rank)[0] for shape in shapes]
        auxes = P_is, deltaB

        feasibility_penalties = [10] * len(random_matrices)
        pf2_penalty = penalties.Parafac2()

        initial_penalty = pf2_penalty.penalty(pf2_penalty.auxes_as_matrices(auxes))
        out = pf2_penalty.factor_matrices_update(random_matrices, feasibility_penalties, auxes)
        assert pf2_penalty.penalty(pf2_penalty.auxes_as_matrices(out)) <= initial_penalty

    def test_factor_matrices_update_changes_input(self, random_matrices, rng):
        svd = get_svd("truncated_svd")

        shapes = [tl.shape(matrix) for matrix in random_matrices]
        rank = shapes[0][1]
        deltaB = tl.tensor(rng.standard_normal((rank, rank)))
        P_is = [svd(tl.tensor(rng.standard_normal(size=shape)), n_eigenvecs=rank)[0] for shape in shapes]
        auxes = P_is, deltaB

        feasibility_penalties = [10] * len(random_matrices)
        pf2_penalty = penalties.Parafac2()

        out = pf2_penalty.factor_matrices_update(random_matrices, feasibility_penalties, auxes)
        constructed_out = [P_i @ out[1] for P_i in out[0]]
        for random_matrix, out_matrix in zip(random_matrices, constructed_out):
            assert not np.allclose(random_matrix, out_matrix)

    @pytest.mark.parametrize(
        "dual_init",
        ["random_uniform", "random_standard_normal", "zeros"],
    )
    @pytest.mark.parametrize("aux_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_rank_and_mode_validation_for_init_aux(self, rng, random_ragged_cmf, dual_init, aux_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        penalty = self.PenaltyType(aux_init=aux_init, dual_init=dual_init, **self.penalty_default_kwargs)
        # Test that mode and rank needs int input
        with pytest.raises(TypeError):
            penalty.init_aux(matrices, rank, mode=None)
        with pytest.raises(TypeError):
            penalty.init_aux(matrices, rank=None, mode=1)

        # Check that initialize fails with mode != 1
        with pytest.raises(ValueError):
            penalty.init_aux(matrices, rank, 0, random_state=rng)
        with pytest.raises(ValueError):
            penalty.init_aux(matrices, rank, 2, random_state=rng)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_uniform_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        # Test that init works with random uniform init
        penalty = self.PenaltyType(aux_init="random_uniform", dual_init=dual_init, **self.penalty_default_kwargs)
        init_bases, init_coordinates = penalty.init_aux(matrices, rank, mode=1, random_state=rng)
        assert tl.shape(init_coordinates) == (rank, rank)
        assert tl.all(init_coordinates >= 0)
        assert tl.all(init_coordinates <= 1)

        for init_basis, B_i in zip(init_bases, B_is):
            assert_allclose(init_basis.T @ init_basis, tl.eye(rank))
            assert tl.shape(init_basis) == tl.shape(B_i)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_standard_normal_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        # Test that init works with random standard normal init
        penalty = self.PenaltyType(
            aux_init="random_standard_normal", dual_init=dual_init, **self.penalty_default_kwargs
        )
        init_bases, init_coordinates = penalty.init_aux(matrices, rank, mode=1, random_state=rng)
        assert tl.shape(init_coordinates) == (rank, rank)
        for init_basis, B_i in zip(init_bases, B_is):
            assert_allclose(init_basis.T @ init_basis, tl.eye(rank))
            assert tl.shape(init_basis) == tl.shape(B_i)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_zeros_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        # Test that init works with zeros init
        penalty = self.PenaltyType(aux_init="zeros", dual_init=dual_init, **self.penalty_default_kwargs)
        init_bases, init_coordinates = penalty.init_aux(matrices, rank, mode=1, random_state=rng)
        assert tl.shape(init_coordinates) == (rank, rank)
        assert_array_equal(init_coordinates, 0)
        for init_basis, B_i in zip(init_bases, B_is):
            assert_allclose(init_basis.T @ init_basis, tl.eye(rank), rtol=1e-6)
            assert tl.shape(init_basis) == tl.shape(B_i)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_given_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        # Test that init works with specified init
        init_bases = [tl.eye(*tl.shape(B_i)) for B_i in B_is]
        init_coordinates = tl.tensor(rng.random_sample((rank, rank)))
        penalty = self.PenaltyType(
            aux_init=(init_bases, init_coordinates), dual_init=dual_init, **self.penalty_default_kwargs
        )
        init_bases_2, init_coordinates_2 = penalty.init_aux(matrices, rank, mode=1, random_state=rng)
        assert_array_equal(init_coordinates, init_coordinates_2)
        for init_basis, init_basis_2 in zip(init_bases, init_bases_2):
            assert_array_equal(init_basis, init_basis_2)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_validating_given_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        # Test that init works with specified init
        init_bases = [tl.eye(*tl.shape(B_i)) for B_i in B_is]
        init_coordinates = tl.tensor(rng.random_sample((rank, rank)))
        # Test with various invalid basis matrix lists
        all_invalid_bases = []

        invalid_init_bases = copy(init_bases)
        invalid_init_bases[0] = tl.zeros(tl.shape(invalid_init_bases[0]))  # Not orthogonal is invalid
        all_invalid_bases.append(invalid_init_bases)

        invalid_init_bases = copy(init_bases)
        invalid_init_bases[0] = tl.zeros((tl.shape(invalid_init_bases[0])[0] + 1, rank))  # Wrong shape
        all_invalid_bases.append(invalid_init_bases)

        invalid_init_bases = copy(init_bases)
        invalid_init_bases[0] = tl.zeros((*tl.shape(invalid_init_bases[0]), 2))  # Wrong order
        all_invalid_bases.append(invalid_init_bases)

        all_invalid_bases.append(init_bases + init_bases)  # Wrong number of matrices

        for invalid_init_bases in all_invalid_bases:
            aux_init = (invalid_init_bases, init_coordinates)
            penalty = self.PenaltyType(aux_init=aux_init, dual_init=dual_init, **self.penalty_default_kwargs)

            with pytest.raises(ValueError):
                penalty.init_aux(matrices, rank, mode=1, random_state=rng)

        invalid_coordinates = [
            tl.zeros((rank, rank, rank)),
            tl.zeros((rank + 1, rank)),
            tl.zeros((rank, rank + 1)),
            tl.zeros((rank + 1, rank + 1)),
        ]
        for invalid_init_coordinates in invalid_coordinates:
            aux_init = (init_bases, invalid_init_coordinates)
            penalty = self.PenaltyType(aux_init=aux_init, dual_init=dual_init, **self.penalty_default_kwargs)

            with pytest.raises(ValueError):
                penalty.init_aux(matrices, rank, mode=1, random_state=rng)

    @pytest.mark.parametrize("dual_init", ["random_uniform", "random_standard_normal", "zeros"])
    def test_input_validation_for_init_aux(self, rng, random_ragged_cmf, dual_init):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()
        # Test that the init method must be a valid type
        invalid_inits = [
            None,
            1,
            1.1,
            (None, None),
            ([None] * len(matrices), tl.zeros((rank, rank))),
            ([tl.eye(J_i, rank) for J_i, k in shapes], None),
        ]
        for invalid_init in invalid_inits:
            penalty = self.PenaltyType(aux_init=invalid_init, dual_init=dual_init, **self.penalty_default_kwargs)
            with pytest.raises(TypeError):
                penalty.init_aux(matrices, rank, mode=1, random_state=rng)

        # Check that we get value error if aux init is str but not "random_uniform" or "random_standard_normal"
        penalty = self.PenaltyType(aux_init="invalid init name", dual_init=dual_init, **self.penalty_default_kwargs)
        for mode in range(2):
            with pytest.raises(ValueError):
                penalty.init_aux(matrices, rank, mode=mode, random_state=None)

    def test_subtract_from_aux(
        self,
    ):
        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        with pytest.raises(TypeError):
            penalty.subtract_from_aux(None, None)

    def test_subtract_from_auxes(self, rng, random_ragged_cmf):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        auxes = penalty.init_aux(matrices, rank, 1, random_state=rng)
        aux_matrices = penalty.auxes_as_matrices(auxes)

        aux_diffs = penalty.subtract_from_auxes(auxes, B_is)
        for i, B_i in enumerate(B_is):
            aux = aux_matrices[i]
            aux_diff = aux_diffs[i]

            assert_allclose(aux_diff, aux - B_i)

    def test_aux_as_matrix(self, random_matrix):
        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        # Check that this raises TypeError
        with pytest.raises(TypeError):
            penalty.aux_as_matrix(random_matrix)

    def test_auxes_as_matrices(self, rng, random_ragged_cmf):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        matrices = cmf.to_matrices()

        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        auxes = penalty.init_aux(matrices, rank, 1, random_state=rng)
        aux_matrices = penalty.auxes_as_matrices(auxes)

        for i, aux in enumerate(aux_matrices):
            aux = aux_matrices[i]
            basis_i = auxes[0][i]

            assert_allclose(aux, basis_i @ auxes[1])

    def test_penalty(self, random_ragged_cmf):
        cmf, shapes, rank = random_ragged_cmf
        weights, (A, B_is, C) = cmf
        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        assert penalty.penalty(B_is) == 0

        with pytest.raises(TypeError):
            penalty.penalty(A)


class TestTemporalSmoothness(BaseTestFactorMatricesPenalty):
    PenaltyType = penalties.TemporalSmoothnessPenalty
    penalty_default_kwargs = {"smoothness_l": 1}

    n_rows = 10
    min_rows = n_rows
    max_rows = n_rows

    def test_penalty(self, random_regular_cmf):
        # Check that the penalty term is computed correctly.

        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        cmf, random_ragged_shapes, rank = random_regular_cmf
        weights, (A, B_is, C) = cmf

        K = len(B_is)

        penalty_term = 0
        for k in range(1, K):
            penalty_term += tl.sum((B_is[k] - B_is[k - 1]) ** 2)

        assert_allclose(penalty.penalty(B_is), penalty_term)

    def get_invariant_matrices(self, rng, shapes):
        # Generate a list of invariant matrices that will not be changed by the proximal operator.

        K = len(shapes)

        invariant_matrix = np.array(rng.random_sample(shapes[0]))
        invariant_matrices = [tl.tensor(invariant_matrix.copy()) for _ in range(K)]
        return invariant_matrices

    def get_non_invariant_matrices(self, rng, shapes):
        # Generate a list of invariant matrices that will be changed by the proximal operator.

        K = len(shapes)

        non_invariant_matrices = [tl.tensor(rng.random_sample(shapes[k])) for k in range(K)]
        return non_invariant_matrices

    def test_A_assembly(self, random_regular_cmf,rng):
        # Ensure A is assembled correctly by comparing the efficent method (A1) with the manual assembly (A2).

        penalty = self.PenaltyType(**self.penalty_default_kwargs)
        cmf, random_ragged_shapes, rank = random_regular_cmf
        weights, (A, B_is, C) = cmf

        I = len(B_is)

        rhos = rng.random_sample(I)

        A1 = (
            tl.diag(
                tl.tensor([penalty._get_laplace_coef( i, I) + rho for i, rho in enumerate(rhos)]), k=0
            )
            - tl.diag(tl.ones(I - 1) * 2 * penalty.smoothness_l, k=1)
            - tl.diag(tl.ones(I - 1) * 2 * penalty.smoothness_l, k=-1)
        )

        A2 = tl.zeros((len(B_is), len(B_is)))

        for i in range(len(B_is)):
            for j in range(len(B_is)):
                if i == j:
                    A2[i, j] = 4 * penalty.smoothness_l + rhos[i]
                elif (i == j - 1) or (i == j + 1):
                    A2[i, j] = -2 * penalty.smoothness_l
                else:
                    pass

        A2[0, 0] -= 2 * penalty.smoothness_l
        A2[len(B_is) - 1, len(B_is) - 1] -= 2 * penalty.smoothness_l

        if tl.get_backend() == "numpy":
            assert_allclose(A1, A2)
        else: # pytorch is slightly less accurate here, so we relax the tolerance
            assert_allclose(A1, A2, rtol=1e-5)
