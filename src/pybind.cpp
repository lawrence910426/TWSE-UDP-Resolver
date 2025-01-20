#include <pybind11/pybind11.h>
#include "parser.h"

namespace py = pybind11;

int add(int i, int j) {
    return i + j;
}

PYBIND11_MODULE(twse_udp_resolver, m) {
    m.doc() = "TWSE UDP Resolver (Python interface)"; // optional module docstring

    py::class_<Parser>(m, "Parser")
        .def(py::init<>())
        .def("set_multicast", &Parser::set_multicast, "Sets the parameter of multicast");
}