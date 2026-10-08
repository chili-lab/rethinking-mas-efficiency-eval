from typing import List

from core.log import get_logger


class Topology:
    def __init__(
        self,
        spatial_masks: List[List[List[int]]],   # [round][node][node]
        temporal_masks: List[List[List[int]]],  # [round][node][node]
        node_masks: List[List[int]],            # [round][node]
    ):

        self.spatial_masks = spatial_masks
        self.temporal_masks = temporal_masks
        self.node_masks = node_masks

    def validate(self) -> None:
        self._validate_binary()
        self._validate_spatial_dag()
        self._validate_temporal_dag()
        self._validate_node_masks()

    def num_rounds(self) -> int:
        return len(self.spatial_masks)

    def to_string(self) -> str:
        return (
            f"Spatial masks: {self.spatial_masks}\n"
            f"Temporal masks: {self.temporal_masks}\n"
            f"Node masks: {self.node_masks}"
        )

    def _validate_binary(self) -> None:
        # spatial & temporal: 3D
        for masks in (self.spatial_masks, self.temporal_masks):
            for round_idx, mat in enumerate(masks):
                for i, row in enumerate(mat):
                    for j, cell in enumerate(row):
                        if cell not in (0, 1):
                            raise ValueError(
                                f"Mask must be binary at "
                                f"round={round_idx}, i={i}, j={j}: {cell}"
                            )
        # node_masks: 2D
        for round_idx, mask in enumerate(self.node_masks):
            for i, val in enumerate(mask):
                if val not in (0, 1):
                    raise ValueError(
                        f"Node mask must be binary at round={round_idx}, i={i}: {val}"
                    )

    def _validate_spatial_dag(self) -> None:
        # forbid self-loop and backward edge
        for round_idx, mat in enumerate(self.spatial_masks):
            n = len(mat)
            for i in range(n):
                if mat[i][i] != 0:
                    raise ValueError(
                        f"Spatial mask must be DAG (no self-loop) at "
                        f"round={round_idx}, node={i}"
                    )
                for j in range(i):
                    if mat[i][j] != 0:
                        raise ValueError(
                            f"Spatial mask must be DAG (no backward edge) at "
                            f"round={round_idx}, {i}->{j}"
                        )

    def _validate_temporal_dag(self) -> None:
        # forbid t->t+1 and t+1->t simultaneously
        for t in range(len(self.temporal_masks) - 1):
            mat_fwd = self.temporal_masks[t]
            mat_bwd = self.temporal_masks[t + 1]
            n = len(mat_fwd)
            for i in range(n):
                for j in range(n):
                    if mat_fwd[i][j] == 1 and mat_bwd[j][i] == 1:
                        raise ValueError(
                            f"Temporal mask must be DAG (no bidirectional link) "
                            f"between rounds {t} and {t+1}, nodes {i}<->{j}"
                        )

    def _validate_node_masks(self) -> None:
        expected_rounds = len(self.spatial_masks)
        if len(self.node_masks) != expected_rounds:
            raise ValueError(
                f"Node mask rounds {len(self.node_masks)} "
                f"!= spatial mask rounds {expected_rounds}"
            )




""" write a test case for the topology every time we update the code """
def test_topology():
    # test case 1
    spatial_masks = [[[0, 1], [0, 0]], [[0, 0], [0, 0]]]
    temporal_masks = [[[0, 1], [0, 0]], [[0, 0], [0, 0]]]
    node_masks = [[1, 0], [0, 1]]
    topology = Topology(spatial_masks, temporal_masks, node_masks)
    topology.validate()
    get_logger().info(topology.to_string())

if __name__ == "__main__":
    test_topology()