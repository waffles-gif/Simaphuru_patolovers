from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_optimization import QuadraticProgram


def test_aer_runs_a_measured_circuit_locally():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.measure_all()
    result = AerSimulator().run(circuit, shots=32, seed_simulator=7).result()
    counts = result.get_counts()
    assert sum(counts.values()) == 32
    assert set(counts).issubset({"0", "1"})


def test_optimization_package_represents_the_team_fixture():
    problem = QuadraticProgram()
    problem.binary_var("x0")
    problem.binary_var("x1")
    problem.minimize(constant=3, linear={"x0": -2, "x1": 1}, quadratic={("x0", "x1"): -2})
    assert problem.objective.evaluate([0, 0]) == 3
    assert problem.objective.evaluate([1, 1]) == 0
